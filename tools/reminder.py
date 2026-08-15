import datetime
import re

def run_simulate_reminder(due_date_or_duration: str) -> dict:
    """
    Translates a deadline string into a simulated target timestamp.
    Returns status, target date string, and message.
    """
    if not due_date_or_duration:
        return {
            "status": "FAILED",
            "error": "No deadline or duration specified for reminder."
        }
        
    now = datetime.datetime.now()
    cleaned = due_date_or_duration.lower().strip()
    
    # Try parsing patterns like "X days", "in X days"
    days_match = re.search(r"(\d+)\s*day", cleaned)
    weeks_match = re.search(r"(\d+)\s*week", cleaned)
    hours_match = re.search(r"(\d+)\s*hour", cleaned)
    
    target_time = None
    if days_match:
        days = int(days_match.group(1))
        target_time = now + datetime.timedelta(days=days)
    elif weeks_match:
        weeks = int(weeks_match.group(1))
        target_time = now + datetime.timedelta(weeks=weeks)
    elif hours_match:
        hours = int(hours_match.group(1))
        target_time = now + datetime.timedelta(hours=hours)
    elif "next friday" in cleaned:
        # Calculate days until next Friday
        # Monday is 0, Friday is 4
        days_ahead = 4 - now.weekday()
        if days_ahead <= 0:  # Already Friday or past Friday this week
            days_ahead += 7
        target_time = now + datetime.timedelta(days=days_ahead)
        target_time = target_time.replace(hour=9, minute=0, second=0, microsecond=0)
    elif "tomorrow" in cleaned:
        target_time = now + datetime.timedelta(days=1)
    else:
        # Fallback: assume 7 days if unrecognized
        target_time = now + datetime.timedelta(days=7)
        
    target_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "status": "SUCCESS",
        "input_deadline": due_date_or_duration,
        "calculated_reminder_time": target_str,
        "message": f"Simulated reminder successfully scheduled for {target_str} ({due_date_or_duration})."
    }
