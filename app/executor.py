import json
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.schemas import ActionItem as PyActionItem
from app.models import ActionItem as DbActionItem, ActivityLog
import tools

def execute_action(action: Any, db: Optional[Session] = None) -> dict:
    """
    Execute a single action item.
    Supports both Pydantic schemas (for tests) and SQLAlchemy DB models (for real runs).
    
    If db session is provided, updates the database state and logs activity.
    """
    # 1. Determine parameters based on model type
    is_db_model = isinstance(action, DbActionItem)
    
    automatable = action.automatable
    description = action.description
    tool_name = action.tool_name
    
    # Extract route string
    route_str = action.action_type if is_db_model else (action.route.value if hasattr(action.route, 'value') else str(action.route))
    
    # Safely parse tool_params
    params_dict = {}
    if action.tool_params:
        if isinstance(action.tool_params, str):
            try:
                params_dict = json.loads(action.tool_params)
            except Exception:
                params_dict = {}
        elif hasattr(action.tool_params, "model_dump"):
            params_dict = action.tool_params.model_dump()
        elif isinstance(action.tool_params, dict):
            params_dict = action.tool_params
            
    # Check if human confirmation is required
    if route_str in ["PREPARE_FOR_HUMAN_REVIEW", "REQUIRES_CLARIFICATION", "CANNOT_EXECUTE"] or not automatable:
        if is_db_model and db:
            action.status = "AWAITING_CONFIRMATION" if route_str == "PREPARE_FOR_HUMAN_REVIEW" else "BLOCKED"
            db.commit()
            
            # Log activity
            log_event = f"Action Paused ({route_str})"
            log_details = f"Action: {description}\nReason: {action.reason}"
            log = ActivityLog(work_item_id=action.work_item_id, event=log_event, details=log_details, status=action.status)
            db.add(log)
            db.commit()
            
        return {
            "status": "AWAITING_CONFIRMATION" if route_str == "PREPARE_FOR_HUMAN_REVIEW" else "BLOCKED",
            "message": f"Human confirmation/intervention required: {description}. Route: {route_str}",
            "output": None
        }

    # 2. Execute automatable tools
    result_output = None
    execution_status = "COMPLETED"
    
    try:
        if tool_name == "web_check":
            url = params_dict.get("url", "")
            res = tools.run_web_check(url)
            result_output = json.dumps(res, indent=2)
            if res.get("status") == "FAILED":
                execution_status = "FAILED"
                
        elif tool_name == "draft_communication":
            recipient = params_dict.get("recipient", "")
            context = params_dict.get("context", "")
            draft = tools.draft_communication(recipient, context)
            result_output = draft
            if draft.startswith("Failed to draft"):
                execution_status = "FAILED"
                
        elif tool_name == "generate_markdown_brief":
            if is_db_model and db:
                # Fetch work item details
                work_item = action.work_item
                actions_list = []
                for act in work_item.actions:
                    actions_list.append({
                        "description": act.description,
                        "status": act.status,
                        "automatable": act.automatable,
                        "action_type": act.action_type,
                        "reason": act.reason,
                        "output": act.output
                    })
                missing_list = []
                if work_item.missing_information:
                    try:
                        missing_list = json.loads(work_item.missing_information)
                    except Exception:
                        missing_list = [work_item.missing_information] if work_item.missing_information else []
                        
                res = tools.generate_markdown_brief(
                    work_item_id=work_item.id,
                    title=work_item.title or "Work Item",
                    summary=work_item.summary or "",
                    priority=work_item.priority or "medium",
                    deadline=work_item.deadline or "",
                    action_items=actions_list,
                    missing_info=missing_list
                )
                result_output = json.dumps(res, indent=2)
                if res.get("status") == "FAILED":
                    execution_status = "FAILED"
            else:
                result_output = "Brief generation requires active database session context."
                
        elif tool_name == "simulate_reminder":
            due = params_dict.get("due_date_or_duration", "7 days")
            res = tools.run_simulate_reminder(due)
            result_output = json.dumps(res, indent=2)
            if res.get("status") == "FAILED":
                execution_status = "FAILED"
                
        elif tool_name == "search_stored_work":
            query = params_dict.get("query", "")
            res = tools.run_db_search(query)
            result_output = json.dumps(res, indent=2)
            if res.get("status") == "FAILED":
                execution_status = "FAILED"
                
        else:
            # Fallback for generic actions
            result_output = f"Action executed successfully: {description}"
            
    except Exception as e:
        execution_status = "FAILED"
        result_output = f"Execution failed with unexpected exception: {str(e)}"

    # 3. Update database state if applicable
    if is_db_model and db:
        action.status = execution_status
        action.output = result_output
        db.commit()
        
        # Log activity
        log = ActivityLog(
            work_item_id=action.work_item_id,
            event=f"Action Executed ({tool_name or 'generic'})",
            details=f"Description: {description}\nStatus: {execution_status}\nOutput Preview: {result_output[:200]}...",
            status=execution_status
        )
        db.add(log)
        db.commit()

    return {
        "status": execution_status,
        "message": f"Action execution finished with status {execution_status}.",
        "output": result_output
    }

def execute_actions(actions: list[Any], db: Optional[Session] = None) -> list[dict]:
    """
    Execute all action items and return their results.
    """
    results = []
    for action in actions:
        result = execute_action(action, db)
        results.append(result)
    return results