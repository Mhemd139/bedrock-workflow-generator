"""Convert friend's recording format to SessionTimeline format"""
from datetime import datetime
from src.models.events import SessionTimeline, EventLog, EventType

def convert_friend_format(friend_data: dict) -> SessionTimeline:
    """Convert friend's format to our SessionTimeline format"""
    
    metadata = friend_data.get("metadata", {})
    actions = friend_data.get("actions", [])
    
    # Build events list
    events = []
    for action in actions:
        if action.get("command") == "STOP":
            continue
            
        # Map his commands to our event types
        event_type = map_command_to_event_type(action.get("command"))
        if not event_type:
            continue
        
        # Extract element info for OCR text
        element = action.get("element", {})
        element_name = element.get("name", "")
        ocr_text = element_name if element_name and element_name != "Error" else None
        
        # Build event
        event = EventLog(
            timestamp=datetime.fromisoformat(action["timestamp"].replace("Z", "+00:00")),
            event_type=event_type,
            data=action.get("parameters", {}),
            screenshot_ref=action.get("screenshot"),
            ocr_text=ocr_text
        )
        events.append(event)
    
    # Build SessionTimeline
    session = SessionTimeline(
        session_id=f"session-{metadata.get('startTimeSeconds', 'unknown')}",
        start_time=datetime.fromisoformat(metadata.get("startTimeFormatted", datetime.now().isoformat()).replace("Z", "+00:00")),
        application="Firefox Browser",  # Could extract from element info
        events=events,
        metadata=metadata
    )
    
    return session


def map_command_to_event_type(command: str) -> EventType:
    """Map friend's command names to our EventType enum"""
    mapping = {
        "CLICK": EventType.MOUSE_CLICK,
        "TYPE": EventType.TEXT_INPUT,
        "PRESS": EventType.KEY_PRESS,
        "SCROLL": EventType.SCROLL,
        "DRAG": EventType.MOUSE_DRAG,
    }
    return mapping.get(command)