import os
import time
import json
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import SessionLocal, Base, engine
from app import models, schemas
from app.agent import plan_work
from app.executor import execute_action
from google.genai.errors import ClientError

# Ensure output directory exists
os.makedirs("sample_outputs", exist_ok=True)

# Recreate DB tables to start fresh
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def run_with_retry(func, *args, **kwargs):
    """
    Helper to run a function and retry on Gemini 429 quota exhaustion.
    """
    retries = 5
    delay = 10
    for i in range(retries):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            if e.code == 429:
                print(f"  [429 Quota Limit] Exceeded Gemini API rate limit. Retrying in {delay}s...")
                time.sleep(delay)
                delay += 15
            else:
                raise e
    raise RuntimeError("Failed to execute due to persistent rate limiting.")

def run_scenario(name, request_text, approve_actions=True):
    print(f"\n========================================\nRunning Scenario: {name}\nRequest: {request_text}\n")
    db = SessionLocal()
    try:
        # 1. Ingest
        print("1. Ingesting request...")
        interpretation = run_with_retry(plan_work, request_text)
        
        # 2. Save WorkItem
        work_item = models.WorkItem(
            original_request=request_text,
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
        
        # Log ingest
        log_ingest = models.ActivityLog(
            work_item_id=work_item.id,
            event="Work Request Ingested",
            details=f"Title: {work_item.title}\nPriority: {work_item.priority}\nSummary: {work_item.summary}",
            status="SUCCESS"
        )
        db.add(log_ingest)
        db.commit()
        
        # 3. Create ActionItems
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
            
        print(f"2. Planned {len(db_actions)} action items.")
        
        # 4. First-pass execution (automated + preparing reviews)
        for db_action in db_actions:
            route = db_action.action_type
            print(f"   Routing: '{db_action.description}' -> {route}")
            
            if route == "EXECUTE_AUTOMATICALLY":
                execute_action(db_action, db)
                print(f"     [Executed Automatically] Status: {db_action.status}")
                
            elif route == "PREPARE_FOR_HUMAN_REVIEW":
                if db_action.tool_name:
                    # Execute tool to generate draft
                    execute_action(db_action, db)
                    db_action.status = "AWAITING_CONFIRMATION"
                    db.commit()
                    print(f"     [Prepared for Review] Draft created. Status: {db_action.status}")
                else:
                    db_action.status = "AWAITING_CONFIRMATION"
                    db.commit()
                    print(f"     [Awaiting Review] Status: {db_action.status}")
                    
            elif route == "REQUIRES_CLARIFICATION":
                db_action.status = "BLOCKED"
                db.commit()
                log = models.ActivityLog(
                    work_item_id=work_item.id,
                    event="Action Blocked",
                    details=f"Requires clarification: {db_action.description}\nReason: {db_action.reason}",
                    status="BLOCKED"
                )
                db.add(log)
                db.commit()
                print(f"     [Blocked] Status: {db_action.status}")
                
            else:  # CANNOT_EXECUTE
                db_action.status = "FAILED"
                db.commit()
                log = models.ActivityLog(
                    work_item_id=work_item.id,
                    event="Action Failed (Unsupported)",
                    details=f"Cannot execute: {db_action.description}\nReason: {db_action.reason}",
                    status="FAILED"
                )
                db.add(log)
                db.commit()
                print(f"     [Failed/Unsupported] Status: {db_action.status}")

        # 5. Simulate human-in-the-loop approval step if required
        if approve_actions:
            print("3. Simulating Human-in-the-loop review approval/edits...")
            for db_action in db_actions:
                if db_action.status == "AWAITING_CONFIRMATION":
                    # Simulate human approving the draft
                    db_action.status = "COMPLETED"
                    db.commit()
                    log = models.ActivityLog(
                        work_item_id=work_item.id,
                        event="Action Approved (HITL)",
                        details=f"Human approved action: {db_action.description}",
                        status="COMPLETED"
                    )
                    db.add(log)
                    db.commit()
                    print(f"     [HITL Approved] {db_action.description} -> COMPLETED")
                    
        # Update overall status
        statuses = [a.status for a in work_item.actions]
        if "AWAITING_CONFIRMATION" in statuses:
            work_item.status = "AWAITING_REVIEW"
        elif "PENDING" in statuses:
            work_item.status = "PROCESSING"
        elif "BLOCKED" in statuses:
            work_item.status = "NEEDS_CLARIFICATION"
        elif "FAILED" in statuses:
            work_item.status = "FAILED" if (len(set(statuses)) == 1 and statuses[0] == "FAILED") else "NEEDS_CLARIFICATION"
        else:
            work_item.status = "COMPLETED"
        db.commit()
        db.refresh(work_item)
        print(f"4. Overall Workflow Status: {work_item.status}")
        
        # Log completion
        log_complete = models.ActivityLog(
            work_item_id=work_item.id,
            event="Workflow Closed",
            details=f"Work item set to status: {work_item.status}.",
            status="SUCCESS"
        )
        db.add(log_complete)
        db.commit()
        
        # Export final state representation
        db.refresh(work_item)
        
        actions_json = []
        for a in work_item.actions:
            actions_json.append({
                "description": a.description,
                "action_type": a.action_type,
                "reason": a.reason,
                "automatable": a.automatable,
                "tool_name": a.tool_name,
                "tool_params": json.loads(a.tool_params) if a.tool_params else None,
                "status": a.status,
                "output": a.output
            })
            
        activities_json = []
        for act in work_item.activities:
            activities_json.append({
                "event": act.event,
                "details": act.details,
                "status": act.status,
                "created_at": act.created_at.isoformat()
            })
            
        missing_info = []
        if work_item.missing_information:
            try:
                missing_info = json.loads(work_item.missing_information)
            except Exception:
                missing_info = [work_item.missing_information]

        output_state = {
            "work_item_id": work_item.id,
            "original_request": work_item.original_request,
            "title": work_item.title,
            "summary": work_item.summary,
            "priority": work_item.priority,
            "deadline": work_item.deadline,
            "missing_information": missing_info,
            "status": work_item.status,
            "actions": actions_json,
            "activity_trace": activities_json
        }
        return output_state
        
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting programmatic scenario runner...")
    
    # Scenario 1: Routine Business Work
    s1_req = "Summarize the partner discussion on product launch. We agreed to follow up next week. Draft a thank-you email to Sarah at sarah@partner.com and set a reminder in 7 days."
    s1_res = run_scenario("Routine Business Work", s1_req, approve_actions=True)
    with open("sample_outputs/scenario_1_routine.json", "w") as f:
        json.dump(s1_res, f, indent=2)
    print("-> Saved sample_outputs/scenario_1_routine.json")
    
    # Wait to avoid hitting rate limits
    print("Waiting 15 seconds to respect Gemini free tier rate limit...")
    time.sleep(15)
    
    # Scenario 2: Website check & Report
    s2_req = "Please run a website check audit on hedamo.com to see if the page load speed and title elements are operating correctly, and generate a markdown brief summarizing results."
    s2_res = run_scenario("Product/Website Check", s2_req, approve_actions=True)
    with open("sample_outputs/scenario_2_website.json", "w") as f:
        json.dump(s2_res, f, indent=2)
    print("-> Saved sample_outputs/scenario_2_website.json")
    
    # Wait to avoid hitting rate limits
    print("Waiting 15 seconds to respect Gemini free tier rate limit...")
    time.sleep(15)
    
    # Scenario 3: Ambiguous request
    s3_req = "Please take care of the documentation and send it to everyone before the meeting."
    s3_res = run_scenario("Ambiguous Request", s3_req, approve_actions=False)
    with open("sample_outputs/scenario_3_ambiguous.json", "w") as f:
        json.dump(s3_res, f, indent=2)
    print("-> Saved sample_outputs/scenario_3_ambiguous.json")
    
    print("\nScenario run complete! All outputs successfully written to sample_outputs/ directory.")
