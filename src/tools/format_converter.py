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
        command = action.get("command")
        
        if command == "STOP":
            continue
            
        # Map his commands to our event types
        event_type = map_command_to_event_type(command)
        if not event_type:
            continue
        
        # Extract element info
        element = action.get("element", {})
        element_name = element.get("name", "")
        element_type = element.get("control_type", "")
        automation_id = element.get("automation_id", "")
        
        # Get parameters and enrich with element data
        params = action.get("parameters", {}).copy()
        
        # Fix button format: "Button.left" → "left"
        if "button" in params and isinstance(params["button"], str):
            params["button"] = params["button"].replace("Button.", "").lower()
        
        # FIX: Clean key names - Remove "Key." prefix
        if "key" in params and isinstance(params["key"], str):
            key = params["key"]
            if key.startswith("Key."):
                params["key"] = key.replace("Key.", "").lower()
        
        # Handle COPY/PASTE commands specially
        if command == "COPY":
            params["user_intent"] = "copy_to_clipboard"
            params["clipboard_content"] = params.get("content", "")
        elif command == "PASTE":
            params["user_intent"] = "paste_from_clipboard"
            params["clipboard_content"] = params.get("content", "")
        
        # Store element metadata in data
        # Filter out "Unknown", "N/A", and empty strings
        if element_name and element_name not in ["Error", "N/A", "Unknown", ""]:
            params["element_name"] = element_name
        if element_type and element_type not in ["Unknown", ""]:
            params["element_type"] = element_type
        if automation_id and automation_id not in ["N/A", ""]:
            params["automation_id"] = automation_id
        
        # Parse timestamp with error handling for malformed format
        timestamp_str = action["timestamp"]
        # Fix malformed timestamp: "17:56M:47" → "17:56:47"
        timestamp_str = timestamp_str.replace("M:", ":")
        
        # Build event
        try:
            event = EventLog(
                timestamp=datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")),
                event_type=event_type,
                data=params,
                screenshot_ref=action.get("screenshot")
            )
            events.append(event)
        except ValueError as e:
            print(f"Warning: Failed to parse timestamp '{timestamp_str}': {e}")
            # Skip this event or use current time as fallback
            continue
    
    # Build SessionTimeline
    session = SessionTimeline(
        session_id=f"session-{metadata.get('startTimeSeconds', 'unknown')}",
        start_time=datetime.fromisoformat(
            metadata.get("startTimeFormatted", datetime.now().isoformat()).replace("Z", "+00:00")
        ),
        application="Firefox Browser",
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
        "HOTKEY": EventType.KEY_COMBINATION,
        "COPY": EventType.KEY_COMBINATION,
        "PASTE": EventType.KEY_COMBINATION,
    }
    return mapping.get(command)