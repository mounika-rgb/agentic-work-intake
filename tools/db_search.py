from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import WorkItem, ActionItem

def run_db_search(query: str) -> dict:
    """
    Searches the SQLite database for work items and action items containing the query.
    Returns structured search results.
    """
    if not query:
        return {
            "status": "FAILED",
            "error": "No query provided for database search."
        }
        
    db = SessionLocal()
    try:
        # Search work items
        work_items = db.query(WorkItem).filter(
            WorkItem.title.like(f"%{query}%") | 
            WorkItem.summary.like(f"%{query}%") |
            WorkItem.original_request.like(f"%{query}%")
        ).all()
        
        # Search action items
        action_items = db.query(ActionItem).filter(
            ActionItem.description.like(f"%{query}%") |
            ActionItem.output.like(f"%{query}%")
        ).all()
        
        results = {
            "status": "SUCCESS",
            "query": query,
            "work_items_found": [
                {
                    "id": item.id,
                    "title": item.title,
                    "summary": item.summary,
                    "priority": item.priority,
                    "status": item.status,
                    "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                } for item in work_items
            ],
            "action_items_found": [
                {
                    "id": item.id,
                    "work_item_id": item.work_item_id,
                    "description": item.description,
                    "status": item.status,
                    "output_preview": item.output[:100] + "..." if item.output else None
                } for item in action_items
            ]
        }
        return results
    except Exception as e:
        return {
            "status": "FAILED",
            "error": f"Database search failed: {str(e)}"
        }
    finally:
        db.close()
