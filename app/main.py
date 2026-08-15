import os
import json
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import Base, engine, get_db
from app import models, schemas
from app.agent import plan_work
from app.executor import execute_action

# Ensure directories exist
os.makedirs("briefs", exist_ok=True)
os.makedirs("app/static", exist_ok=True)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Agentic Work Intake & Execution System",
    description="AI-powered work intake and execution prototype",
    version="1.0.0"
)

# Request schemas for FastAPI endpoints
class IntakeRequest(BaseModel):
    text: str

class EditActionRequest(BaseModel):
    description: str
    output: str

# API Endpoints

@app.post("/api/intake")
def intake_work(req: IntakeRequest, db: Session = Depends(get_db)):
    """
    Ingests unstructured text, runs LLM parsing, creates database records,
    routes actions, executes automatable tasks, and prepares review tasks.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Request text cannot be empty.")

    try:
        # 1. Run LLM parsing
        interpretation = plan_work(req.text)
        
        # 2. Save WorkItem in DB
        work_item = models.WorkItem(
            original_request=req.text,
            title=interpretation.title,
            summary=interpretation.summary,
            priority=interpretation.priority.value,
            deadline=interpretation.deadline,
            missing_information=json.dumps(interpretation.missing_information),
            status="PROCESSING"
        )
        db.add(work_item)
        db.commit()
        db.refresh(work_item)
        
        # 3. Create Activity Log
        log_ingest = models.ActivityLog(
            work_item_id=work_item.id,
            event="Work Request Ingested",
            details=f"Structured Ingestion:\nTitle: {work_item.title}\nPriority: {work_item.priority}\nSummary: {work_item.summary}",
            status="SUCCESS"
        )
        db.add(log_ingest)
        db.commit()
        
        # 4. Save and Process ActionItems
        has_awaiting_review = False
        db_actions = []
        
        for item in interpretation.action_items:
            db_action = models.ActionItem(
                work_item_id=work_item.id,
                description=item.description,
                action_type=item.route.value,
                reason=item.reason,
                automatable=item.automatable,
                tool_name=item.tool_name,
                tool_params=json.dumps(item.tool_params.model_dump()) if item.tool_params else None,
                status="PENDING"
            )
            db.add(db_action)
            db.commit()
            db.refresh(db_action)
            db_actions.append(db_action)
            
        # 5. Process / Execute Actions
        for db_action in db_actions:
            route = db_action.action_type
            if route == "EXECUTE_AUTOMATICALLY":
                # Execute tool automatically
                execute_action(db_action, db)
            elif route == "PREPARE_FOR_HUMAN_REVIEW":
                # Run the draft tool but set status to AWAITING_CONFIRMATION
                if db_action.tool_name:
                    execute_action(db_action, db)
                    db_action.status = "AWAITING_CONFIRMATION"
                    db.commit()
                else:
                    db_action.status = "AWAITING_CONFIRMATION"
                    db.commit()
                has_awaiting_review = True
            elif route == "REQUIRES_CLARIFICATION":
                db_action.status = "BLOCKED"
                db.commit()
                # Log clarification block
                log = models.ActivityLog(
                    work_item_id=work_item.id,
                    event="Action Blocked",
                    details=f"Requires clarification: {db_action.description}\nReason: {db_action.reason}",
                    status="BLOCKED"
                )
                db.add(log)
                db.commit()
            else:  # CANNOT_EXECUTE
                db_action.status = "FAILED"
                db.commit()
                # Log failure
                log = models.ActivityLog(
                    work_item_id=work_item.id,
                    event="Action Failed (Unsupported)",
                    details=f"Cannot execute: {db_action.description}\nReason: {db_action.reason}",
                    status="FAILED"
                )
                db.add(log)
                db.commit()

        # Update work item status
        if has_awaiting_review:
            work_item.status = "AWAITING_REVIEW"
        else:
            # Check if all action items succeeded
            all_statuses = [a.status for a in work_item.actions]
            if "FAILED" in all_statuses or "BLOCKED" in all_statuses:
                work_item.status = "FAILED" if "FAILED" in all_statuses else "NEEDS_CLARIFICATION"
            else:
                work_item.status = "COMPLETED"
        db.commit()
        db.refresh(work_item)
        
        # Log final intake completion
        log_complete = models.ActivityLog(
            work_item_id=work_item.id,
            event="Intake Processing Finished",
            details=f"Workflow Status set to {work_item.status}.",
            status="SUCCESS"
        )
        db.add(log_complete)
        db.commit()
        
        return get_work_item_detail(work_item.id, db)
        
    except Exception as e:

        db.rollback()

        error_message = str(e)

        if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota exceeded. Please wait for the quota to reset or check your Gemini API plan."
            )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process work request: {error_message}"
        )

@app.get("/api/work-items")
def list_work_items(q: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """
    Lists work items. If q is specified, filters by title, summary, or description.
    """
    query = db.query(models.WorkItem)
    if q:
        query = query.filter(
            models.WorkItem.title.like(f"%{q}%") |
            models.WorkItem.summary.like(f"%{q}%") |
            models.WorkItem.original_request.like(f"%{q}%")
        )
    items = query.order_by(models.WorkItem.created_at.desc()).all()
    
    res = []
    for item in items:
        # Basic list serialisation
        res.append({
            "id": item.id,
            "title": item.title,
            "summary": item.summary,
            "priority": item.priority,
            "deadline": item.deadline,
            "status": item.status,
            "created_at": item.created_at.isoformat()
        })
    return res

@app.get("/api/work-items/{id}")
def get_work_item_detail(id: int, db: Session = Depends(get_db)):
    """
    Returns complete details of a single work item, its actions, and its activity log.
    """
    work_item = db.query(models.WorkItem).filter(models.WorkItem.id == id).first()
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found.")
        
    actions = []
    for a in work_item.actions:
        actions.append({
            "id": a.id,
            "description": a.description,
            "action_type": a.action_type,
            "reason": a.reason,
            "automatable": a.automatable,
            "tool_name": a.tool_name,
            "tool_params": json.loads(a.tool_params) if a.tool_params else None,
            "status": a.status,
            "output": a.output,
            "created_at": a.created_at.isoformat()
        })
        
    activities = []
    for act in work_item.activities:
        activities.append({
            "id": act.id,
            "event": act.event,
            "details": act.details,
            "status": act.status,
            "created_at": act.created_at.isoformat()
        })
        
    # Sort activity logs chronological order
    activities.sort(key=lambda x: x["created_at"])
    
    missing_info = []
    if work_item.missing_information:
        try:
            missing_info = json.loads(work_item.missing_information)
        except Exception:
            missing_info = [work_item.missing_information] if work_item.missing_information else []

    return {
        "id": work_item.id,
        "original_request": work_item.original_request,
        "title": work_item.title,
        "summary": work_item.summary,
        "priority": work_item.priority,
        "deadline": work_item.deadline,
        "missing_information": missing_info,
        "status": work_item.status,
        "created_at": work_item.created_at.isoformat(),
        "updated_at": work_item.updated_at.isoformat(),
        "actions": actions,
        "activities": activities
    }

@app.post("/api/work-items/{id}/actions/{action_id}/execute")
def trigger_action(id: int, action_id: int, db: Session = Depends(get_db)):
    """
    Manually triggers execution of an action item.
    """
    action = db.query(models.ActionItem).filter(
        models.ActionItem.id == action_id,
        models.ActionItem.work_item_id == id
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found.")
        
    # Run tool
    execute_action(action, db)
    
    # Check if we should update work item status
    update_work_item_overall_status(action.work_item_id, db)
    
    return get_work_item_detail(id, db)

@app.post("/api/work-items/{id}/actions/{action_id}/approve")
def approve_action(id: int, action_id: int, db: Session = Depends(get_db)):
    """
    Approves a human-review action, setting its status to COMPLETED.
    """
    action = db.query(models.ActionItem).filter(
        models.ActionItem.id == action_id,
        models.ActionItem.work_item_id == id
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found.")
        
    action.status = "COMPLETED"
    db.commit()
    
    # Log approval activity
    log = models.ActivityLog(
        work_item_id=id,
        event="Action Approved",
        details=f"Human approved action: {action.description}",
        status="COMPLETED"
    )
    db.add(log)
    db.commit()
    
    update_work_item_overall_status(id, db)
    return get_work_item_detail(id, db)

@app.post("/api/work-items/{id}/actions/{action_id}/reject")
def reject_action(id: int, action_id: int, db: Session = Depends(get_db)):
    """
    Rejects a human-review action, setting its status to REJECTED.
    """
    action = db.query(models.ActionItem).filter(
        models.ActionItem.id == action_id,
        models.ActionItem.work_item_id == id
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found.")
        
    action.status = "REJECTED"
    db.commit()
    
    # Log rejection activity
    log = models.ActivityLog(
        work_item_id=id,
        event="Action Rejected",
        details=f"Human rejected action: {action.description}",
        status="REJECTED"
    )
    db.add(log)
    db.commit()
    
    update_work_item_overall_status(id, db)
    return get_work_item_detail(id, db)

@app.post("/api/work-items/{id}/actions/{action_id}/edit")
def edit_action(id: int, action_id: int, req: EditActionRequest, db: Session = Depends(get_db)):
    """
    Edits the action description or its generated output (e.g. communication draft)
    before finalising it as COMPLETED.
    """
    action = db.query(models.ActionItem).filter(
        models.ActionItem.id == action_id,
        models.ActionItem.work_item_id == id
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found.")
        
    action.description = req.description
    action.output = req.output
    action.status = "COMPLETED"
    db.commit()
    
    # Log edit & approval activity
    log = models.ActivityLog(
        work_item_id=id,
        event="Action Edited & Approved",
        details=f"Human edited and approved action: {action.description}\nNew Output Preview: {action.output[:100]}...",
        status="COMPLETED"
    )
    db.add(log)
    db.commit()
    
    update_work_item_overall_status(id, db)
    return get_work_item_detail(id, db)

def update_work_item_overall_status(work_item_id: int, db: Session):
    """
    Recalculates the overall WorkItem status based on the statuses of its action items.
    """
    work_item = db.query(models.WorkItem).filter(models.WorkItem.id == work_item_id).first()
    if not work_item:
        return
        
    statuses = [a.status for a in work_item.actions]
    
    # Logic:
    # If any action is PENDING, AWAITING_CONFIRMATION, we remain in that review/processing state.
    # If any is BLOCKED, and no longer processing, status = NEEDS_CLARIFICATION.
    # If all are COMPLETED/REJECTED, status = COMPLETED (or FAILED if everything failed).
    
    if "AWAITING_CONFIRMATION" in statuses:
        work_item.status = "AWAITING_REVIEW"
    elif "PENDING" in statuses:
        work_item.status = "PROCESSING"
    elif "BLOCKED" in statuses:
        work_item.status = "NEEDS_CLARIFICATION"
    elif "FAILED" in statuses:
        # Check if everything failed or just some
        if len(set(statuses)) == 1 and statuses[0] == "FAILED":
            work_item.status = "FAILED"
        else:
            work_item.status = "NEEDS_CLARIFICATION"
    else:
        # All actions are resolved (COMPLETED, REJECTED, etc.)
        work_item.status = "COMPLETED"
        
    db.commit()


# Mounting Static Files

# Serve generated markdown briefs
app.mount("/briefs", StaticFiles(directory="briefs"), name="briefs")

# Serve UI frontend assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def home():
    """
    Serves the Single Page App (SPA) homepage.
    """
    return FileResponse("app/static/index.html")