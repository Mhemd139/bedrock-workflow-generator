import json
import uuid
import re
from datetime import datetime
from typing import Optional, List, Tuple

from src.models.events import SessionTimeline, EventType, EventLog
from src.models.workflow import WorkflowDefinition, WorkflowStep, ActionType, Selector
from src.services.bedrock_client import BedrockClient


class WorkflowGenerator:
    def __init__(self, bedrock_client: Optional[BedrockClient] = None):
        self.bedrock = bedrock_client or BedrockClient()
    
    def generate_from_session(self, session: SessionTimeline) -> WorkflowDefinition:
        """Generate a workflow definition from a recorded session using AI"""
        
        # Pre-process: group actions before sending to AI
        simplified_events = self.simplify_actions(session.events)
        
        # Create a simplified session for AI analysis
        simplified_session = SessionTimeline(
            session_id=session.session_id,
            start_time=session.start_time,
            end_time=session.end_time,
            application=session.application,
            events=simplified_events,
            metadata=session.metadata
        )
        
        # Convert session to dict for Bedrock
        session_dict = simplified_session.model_dump(mode="json")
        
        # Get AI-generated workflow
        ai_response = self.bedrock.generate_workflow(session_dict, [])
        
        # Parse and validate the response
        workflow_json = self._extract_json(ai_response)
        workflow = WorkflowDefinition(**workflow_json)
        
        # Post-process: ensure all selectors are properly populated
        workflow = self._enrich_workflow(workflow, session)

        # Insert WAIT steps based on timestamp analysis
        workflow = self.insert_wait_steps(workflow, session)

        return workflow
            
    def generate_from_events_only(self, session: SessionTimeline) -> WorkflowDefinition:
        """Generate workflow using only event logs (no AI, deterministic)"""
        
        # First, simplify actions (group typing sequences)
        simplified_events = self.simplify_actions(session.events)
        
        steps = []
        step_counter = 1
        
        for event in simplified_events:
            step = self._event_to_step(event, step_counter)
            if step:
                steps.append(step)
                step_counter += 1
        
        # Infer workflow name and description
        workflow_name, workflow_description = self._infer_workflow_intent(steps, session)
        
        workflow = WorkflowDefinition(
            workflow_id=f"{session.session_id}-workflow",
            name=workflow_name,
            description=workflow_description,
            application=session.application,
            steps=steps,
            metadata={
                "source_session": session.session_id,
                "generated_at": datetime.utcnow().isoformat(),
                "event_count": len(session.events),
                "simplified_count": len(simplified_events)
            }
        )

        # Insert WAIT steps based on timestamp analysis
        workflow = self.insert_wait_steps(workflow, session)

        return workflow
    
    # ============================================================================
    # ACTION GROUPING & SIMPLIFICATION
    # ============================================================================
    def insert_wait_steps(self, workflow: WorkflowDefinition, session: SessionTimeline, 
                        min_wait_threshold: float = 2.0, 
                        buffer_seconds: float = 1.0,
                        max_wait_seconds: float = 10.0) -> WorkflowDefinition:
        """
        Insert WAIT steps between actions where timestamp delta exceeds threshold
        
        Args:
            workflow: Generated workflow definition
            session: Original session timeline with timestamps
            min_wait_threshold: Minimum seconds gap to trigger WAIT insertion (default: 2.0)
            buffer_seconds: Additional seconds to add for page loading (default: 1.0)
            max_wait_seconds: Maximum wait duration cap (default: 10.0)
        
        Returns:
            Modified workflow with WAIT steps inserted
        """
        from datetime import datetime
        
        if not workflow.steps or not session.events:
            return workflow
        
        # Sort events by timestamp
        sorted_events = sorted(session.events, key=lambda e: e.timestamp)
        
        new_steps = []
        
        for i, step in enumerate(workflow.steps):
            # Add the current step
            new_steps.append(step)
            
            # Check if there's a next step
            if i < len(workflow.steps) - 1:
                next_step = workflow.steps[i + 1]
                
                # Try to find corresponding events
                current_event = self._find_step_event(step, sorted_events, i)
                next_event = self._find_step_event(next_step, sorted_events, i + 1)
                
                if current_event and next_event:
                    # Calculate time difference
                    time_delta = (next_event.timestamp - current_event.timestamp).total_seconds()
                    
                    # Insert WAIT if gap exceeds threshold
                    if time_delta >= min_wait_threshold:
                        # Calculate wait duration with buffer and cap
                        wait_duration = min(
                            round(time_delta + buffer_seconds, 1),
                            max_wait_seconds
                        )
                        
                        # Create descriptive wait message
                        wait_reason = self._infer_wait_reason(current_event, next_event)
                        
                        wait_step = WorkflowStep(
                            step_id=f"{step.step_id}-wait",
                            action=ActionType.WAIT,
                            description=f"Wait {wait_duration}s for {wait_reason}",
                            selector=None,
                            parameters={
                                "duration_seconds": wait_duration,
                                "original_gap": round(time_delta, 1)
                            }
                        )
                        new_steps.append(wait_step)
        
        # Update workflow with new steps
        original_step_count = len(workflow.steps)
        workflow.steps = new_steps
        workflow.metadata["total_steps"] = len(new_steps)
        workflow.metadata["wait_steps_inserted"] = len(new_steps) - original_step_count
        
        return workflow

    def _find_step_event(self, step: WorkflowStep, events: List[EventLog], step_index: int) -> Optional[EventLog]:
        """
        Find the original event corresponding to a workflow step
        Uses multiple matching strategies with fallback to index-based matching
        """
        
        # Strategy 1: Match by action type and element data
        for event in events:
            
            # Match CLICK/RIGHT_CLICK/DOUBLE_CLICK by coordinates
            if step.action in [ActionType.CLICK, ActionType.RIGHT_CLICK, ActionType.DOUBLE_CLICK]:
                if event.event_type == EventType.MOUSE_CLICK:
                    # Try fallback coordinates
                    if step.selector and step.selector.fallback and isinstance(step.selector.fallback.value, dict):
                        coords = step.selector.fallback.value
                        if (event.data.get("x") == coords.get("x") and 
                            event.data.get("y") == coords.get("y")):
                            return event
            
            # Match TYPE_TEXT by text content
            elif step.action == ActionType.TYPE_TEXT:
                if event.event_type == EventType.TEXT_INPUT:
                    if event.data.get("text") == step.parameters.get("text"):
                        return event
            
            # Match PRESS_KEY by key name
            elif step.action == ActionType.PRESS_KEY:
                if event.event_type == EventType.KEY_PRESS:
                    event_key = event.data.get("key", "").replace("Key.", "").lower()
                    step_key = step.parameters.get("key", "").lower()
                    if event_key == step_key:
                        return event
            
            # Match KEY_COMBINATION by keys
            elif step.action == ActionType.KEY_COMBINATION:
                if event.event_type == EventType.KEY_COMBINATION:
                    # Simple match - if both have Ctrl+C or Ctrl+V
                    event_keys = [str(k).lower() for k in event.data.get("keys", [])]
                    step_keys = [str(k).lower() for k in step.parameters.get("keys", [])]
                    
                    # Check for Ctrl+C
                    if "ctrl" in " ".join(step_keys) and "c" in " ".join(step_keys):
                        if "ctrl" in " ".join(event_keys) or "ctrl_l" in " ".join(event_keys):
                            if "c" in " ".join(event_keys) or "'\\x03'" in " ".join(event_keys):
                                return event
                    
                    # Check for Ctrl+V
                    if "ctrl" in " ".join(step_keys) and "v" in " ".join(step_keys):
                        if "ctrl" in " ".join(event_keys) or "ctrl_l" in " ".join(event_keys):
                            if "v" in " ".join(event_keys) or "'\\x16'" in " ".join(event_keys):
                                return event
            
            # Match DRAG by start coordinates
            elif step.action == ActionType.DRAG:
                if event.event_type == EventType.MOUSE_DRAG:
                    # Try selector.value (deterministic generator format)
                    if step.selector and isinstance(step.selector.value, dict):
                        if (event.data.get("start_x") == step.selector.value.get("start_x") and
                            event.data.get("start_y") == step.selector.value.get("start_y")):
                            return event
                    
                    # Try parameters (AI-generated format or fallback)
                    if (event.data.get("start_x") == step.parameters.get("start_x") and
                        event.data.get("start_y") == step.parameters.get("start_y")):
                        return event
                    
                    # Try fallback coordinates if present
                    if step.selector and step.selector.fallback and isinstance(step.selector.fallback.value, dict):
                        coords = step.selector.fallback.value
                        if (event.data.get("start_x") == coords.get("x") and
                            event.data.get("start_y") == coords.get("y")):
                            return event
            
            # Match SCROLL by coordinates
            elif step.action == ActionType.SCROLL:
                if event.event_type == EventType.SCROLL:
                    if step.selector and isinstance(step.selector.value, dict):
                        if (event.data.get("x") == step.selector.value.get("x") and
                            event.data.get("y") == step.selector.value.get("y")):
                            return event
        
        # Strategy 2: Fallback to index-based matching if no match found
        # This ensures we still insert waits even if selector matching fails
        if step_index < len(events):
            return events[step_index]
        
        return None



    def _infer_wait_reason(self, current_event: EventLog, next_event: EventLog) -> str:
        """Infer why we're waiting based on action context"""
        
        current_desc = current_event.data.get("element_name", "").lower()
        
        # Check for page navigation (pressing Enter)
        if current_event.event_type == EventType.KEY_PRESS:
            key = str(current_event.data.get("key", "")).lower()
            if "enter" in key:
                return "page load and navigation"
        
        # Check for search/address bar interaction
        if "search" in current_desc or "address" in current_desc:
            return "search results to load"
        
        # Check for clicks on navigation elements
        elif current_event.event_type == EventType.MOUSE_CLICK:
            element_name = current_event.data.get("element_name", "")
            element_type = current_event.data.get("element_type", "")
            
            if "tab" in element_name.lower():
                return "new tab to open"
            elif "button" in element_type.lower() or "link" in element_type.lower():
                return "page load after click"
            elif "window" in element_name.lower():
                return "window to open"
            else:
                return "UI response"
        
        # Check for clipboard operations
        elif current_event.event_type == EventType.KEY_COMBINATION:
            keys = [str(k).lower() for k in current_event.data.get("keys", [])]
            if any("c" in k or "'\\x03'" in k for k in keys):
                return "copy operation"
            elif any("v" in k or "'\\x16'" in k for k in keys):
                return "paste operation"
            else:
                return "keyboard shortcut"
        
        # Check for drag operations
        elif current_event.event_type == EventType.MOUSE_DRAG:
            return "text selection"
        
        # Default
        else:
            return "action to complete"
    
    def simplify_actions(self, events: List[EventLog]) -> List[EventLog]:
        """Group and simplify action sequences"""
        
        # Apply typing sequence grouping
        events = self.group_typing_sequences(events)
        
        # Apply copy-paste pattern recognition
        # REMOVED: Not needed since COPY/PASTE are explicit commands now
        # events = self.detect_copy_paste_patterns(events)
        
        return events
    
    def group_typing_sequences(self, events: List[EventLog]) -> List[EventLog]:
        """Combine TYPE → PRESS(space) → TYPE sequences into single TYPE_TEXT actions"""
        
        grouped = []
        i = 0
        
        while i < len(events):
            # Check if this starts a typing sequence
            if events[i].event_type == EventType.TEXT_INPUT:
                # Collect all consecutive TYPE + PRESS(space) actions
                text_parts = []
                j = i
                
                while j < len(events):
                    if events[j].event_type == EventType.TEXT_INPUT:
                        text_parts.append(events[j].data.get("text", ""))
                        j += 1
                        
                        # Check if next is space key
                        if j < len(events) and events[j].event_type == EventType.KEY_PRESS:
                            key = events[j].data.get("key", "")
                            if "space" in key.lower():
                                text_parts.append(" ")
                                j += 1
                            else:
                                # Not a space, stop grouping
                                break
                        else:
                            # No more events or not a key press
                            break
                    else:
                        break
                
                # If we grouped multiple actions, create a combined event
                if j > i + 1:
                    combined_text = "".join(text_parts).strip()
                    combined_event = EventLog(
                        timestamp=events[i].timestamp,
                        event_type=EventType.TEXT_INPUT,
                        data={
                            "text": combined_text,
                            "element_name": events[i].data.get("element_name"),
                            "element_type": events[i].data.get("element_type"),
                            "automation_id": events[i].data.get("automation_id"),
                            "grouped_from": j - i  # How many actions were grouped
                        },
                        screenshot_ref=events[i].screenshot_ref
                    )
                    grouped.append(combined_event)
                    i = j
                else:
                    # Single action, keep as is
                    grouped.append(events[i])
                    i += 1
            else:
                grouped.append(events[i])
                i += 1
        
        return grouped
    
    def detect_copy_paste_patterns(self, events: List[EventLog]) -> List[EventLog]:
        """Detect and label common keyboard shortcut patterns"""
        
        processed = []
        i = 0
        
        while i < len(events):
            event = events[i]
            
            # Pattern 1: DRAG + Ctrl+C = Copy selected text
            if (event.event_type == EventType.MOUSE_DRAG and 
                i + 1 < len(events) and 
                events[i + 1].event_type == EventType.KEY_COMBINATION):
                
                keys = events[i + 1].data.get("keys", [])
                if self._is_copy_shortcut(keys):
                    # Label the drag as "text selection for copy"
                    event.data["user_intent"] = "select_text_for_copy"
                    processed.append(event)
                    
                    # Label the copy action
                    copy_event = events[i + 1]
                    copy_event.data["user_intent"] = "copy_to_clipboard"
                    processed.append(copy_event)
                    i += 2
                    continue
            
            # Pattern 2: Ctrl+V + Enter = Paste and submit
            if (event.event_type == EventType.KEY_COMBINATION and
                i + 1 < len(events) and
                events[i + 1].event_type == EventType.KEY_PRESS):
                
                keys = event.data.get("keys", [])
                next_key = events[i + 1].data.get("key", "")
                
                if self._is_paste_shortcut(keys) and "enter" in next_key.lower():
                    event.data["user_intent"] = "paste_from_clipboard"
                    processed.append(event)
                    
                    events[i + 1].data["user_intent"] = "submit_input"
                    processed.append(events[i + 1])
                    i += 2
                    continue
            
            processed.append(event)
            i += 1
        
        return processed
    
    def _is_copy_shortcut(self, keys: List[str]) -> bool:
        """Check if keys represent Ctrl+C or Cmd+C"""
        keys_lower = [str(k).lower() for k in keys]
        return ("ctrl" in keys_lower or "ctrl_l" in keys_lower) and \
               ("c" in keys_lower or "'\\x03'" in keys_lower)
    
    def _is_paste_shortcut(self, keys: List[str]) -> bool:
        """Check if keys represent Ctrl+V or Cmd+V"""
        keys_lower = [str(k).lower() for k in keys]
        return ("ctrl" in keys_lower or "ctrl_l" in keys_lower) and \
               ("v" in keys_lower or "'\\x16'" in keys_lower)
    
    # ============================================================================
    # EVENT TO STEP CONVERSION
    # ============================================================================
    
    def _event_to_step(self, event: EventLog, step_num: int) -> Optional[WorkflowStep]:
        """Convert a single event log to a workflow step"""
        
        event_type = event.event_type
        data = event.data
        
        # Extract element info
        element_name = data.get("element_name", "")
        element_type = data.get("element_type", "")
        
        # Determine action type and create selector
        if event_type == EventType.MOUSE_CLICK:
            button = data.get("button", "left")
            
            # Determine action type based on button
            if button == "right":
                action = ActionType.RIGHT_CLICK
            else:
                action = ActionType.CLICK
            
            description = self._generate_description(action, element_name, element_type, data)
            selector = self._create_selector(element_name, element_type, data)
            
            return WorkflowStep(
                step_id=f"step-{step_num}",
                action=action,
                description=description,
                selector=selector,
                parameters={"button": button} if button != "left" else {},
                screenshot_before=event.screenshot_ref
            )
        
        elif event_type == EventType.MOUSE_DOUBLE_CLICK:
            description = self._generate_description(
                ActionType.DOUBLE_CLICK, element_name, element_type, data
            )
            selector = self._create_selector(element_name, element_type, data)
            
            return WorkflowStep(
                step_id=f"step-{step_num}",
                action=ActionType.DOUBLE_CLICK,
                description=description,
                selector=selector,
                parameters={}
            )
        
        elif event_type == EventType.MOUSE_DRAG:
            start_x = data.get("start_x", 0)
            start_y = data.get("start_y", 0)
            end_x = data.get("end_x", 0)
            end_y = data.get("end_y", 0)
            
            user_intent = data.get("user_intent", "")
            if user_intent == "select_text_for_copy":
                description = f"Select text by dragging from ({start_x}, {start_y}) to ({end_x}, {end_y})"
            else:
                description = f"Drag from ({start_x}, {start_y}) to ({end_x}, {end_y})"
            
            return WorkflowStep(
                step_id=f"step-{step_num}",
                action=ActionType.DRAG,
                description=description,
                selector=Selector(
                    type="coordinates",
                    value={
                        "start_x": start_x,
                        "start_y": start_y,
                        "end_x": end_x,
                        "end_y": end_y
                    }
                ),
                parameters={
                    "end_x": end_x,
                    "end_y": end_y
                }
            )
        
        elif event_type == EventType.TEXT_INPUT:
            text = data.get("text", "")
            grouped_count = data.get("grouped_from", 0)
            
            if grouped_count > 1:
                description = f"Type complete text: '{text}'"
            else:
                description = f"Type '{text}'"
            
            if element_name:
                description += f" into '{element_name}'"
            
            # For text input, selector should point to where we're typing
            selector = self._create_selector(element_name, element_type, data) if element_name else None
            
            return WorkflowStep(
                step_id=f"step-{step_num}",
                action=ActionType.TYPE_TEXT,
                description=description,
                selector=selector,
                parameters={"text": text}
            )
        
        elif event_type == EventType.KEY_PRESS:
            key = data.get("key", "")
            user_intent = data.get("user_intent", "")
            
            # Clean up key name
            key_clean = key.replace("Key.", "").lower()
            key_display = self._format_key_name(key_clean)
            
            if user_intent == "submit_input":
                description = f"Submit by pressing {key_display}"
            else:
                description = f"Press {key_display} key"
            
            return WorkflowStep(
                step_id=f"step-{step_num}",
                action=ActionType.PRESS_KEY,
                description=description,
                selector=None,
                parameters={"key": key_clean}
            )
        
        elif event_type == EventType.KEY_COMBINATION:
            keys = data.get("keys", [])
            user_intent = data.get("user_intent", "")
            clipboard_content = data.get("clipboard_content", "")
            
            # Handle COPY/PASTE actions
            if user_intent == "copy_to_clipboard":
                content_preview = clipboard_content.strip()[:50]  # First 50 chars
                if content_preview:
                    description = f"Copy text to clipboard: '{content_preview}'"
                else:
                    description = "Copy selected text to clipboard (Ctrl+C)"
                
                return WorkflowStep(
                    step_id=f"step-{step_num}",
                    action=ActionType.KEY_COMBINATION,
                    description=description,
                    selector=None,
                    parameters={
                        "keys": ["Ctrl", "C"],
                        "clipboard_content": clipboard_content
                    }
                )
            
            elif user_intent == "paste_from_clipboard":
                content_preview = clipboard_content.strip()[:50]
                if content_preview:
                    description = f"Paste text from clipboard: '{content_preview}'"
                else:
                    description = "Paste from clipboard (Ctrl+V)"
                
                return WorkflowStep(
                    step_id=f"step-{step_num}",
                    action=ActionType.KEY_COMBINATION,
                    description=description,
                    selector=None,
                    parameters={
                        "keys": ["Ctrl", "V"],
                        "clipboard_content": clipboard_content
                    }
                )
            
            # Regular hotkey handling
            else:
                key_combo = self._parse_key_combination(keys)
                description = f"Press {key_combo}"
                
                return WorkflowStep(
                    step_id=f"step-{step_num}",
                    action=ActionType.KEY_COMBINATION,
                    description=description,
                    selector=None,
                    parameters={"keys": keys}
                )
        
        elif event_type == EventType.SCROLL:
            delta_y = data.get("delta_y", 0)
            direction = "down" if delta_y > 0 else "up"
            
            return WorkflowStep(
                step_id=f"step-{step_num}",
                action=ActionType.SCROLL,
                description=f"Scroll {direction}",
                selector=Selector(
                    type="coordinates",
                    value={"x": data.get("x", 0), "y": data.get("y", 0)}
                ),
                parameters={
                    "delta_x": data.get("delta_x", 0),
                    "delta_y": delta_y
                }
            )
        
        elif event_type == EventType.NAVIGATION:
            url = data.get("url", "")
            return WorkflowStep(
                step_id=f"step-{step_num}",
                action=ActionType.NAVIGATE,
                description=f"Navigate to {url}",
                selector=None,
                parameters={"url": url}
            )
        
        elif event_type == EventType.SCREENSHOT:
            # Screenshots are reference points, not actions
            return None
        
        return None
    
    # ============================================================================
    # SEMANTIC DESCRIPTION GENERATION
    # ============================================================================
    
    def _generate_description(self, action: ActionType, element_name: str, 
                            element_type: str, data: dict) -> str:
        """Generate human-readable, context-aware descriptions"""
        
        # Get click button if applicable
        button = data.get("button", "left")
        
        # Build description based on element context
        if element_name:
            # Context-aware templates
            if "search" in element_name.lower() or "address" in element_name.lower():
                if action == ActionType.CLICK:
                    return f"Click on search/address bar: '{element_name}'"
                elif action == ActionType.RIGHT_CLICK:
                    return f"Right-click on '{element_name}'"
                    
            elif element_type == "Button":
                verb = "Right-click" if action == ActionType.RIGHT_CLICK else "Click"
                return f"{verb} the '{element_name}' button"
                
            elif element_type == "Hyperlink":
                verb = "Right-click" if action == ActionType.RIGHT_CLICK else "Click"
                return f"{verb} on '{element_name}' link"
                
            elif element_type == "ListItem":
                return f"Select '{element_name}' from menu"
                
            elif element_type == "Edit" or element_type == "ComboBox":
                verb = "Right-click" if action == ActionType.RIGHT_CLICK else "Click"
                return f"{verb} on '{element_name}' input field"
                
            else:
                # Generic but still uses element name
                verb = "Right-click" if action == ActionType.RIGHT_CLICK else "Click"
                return f"{verb} on '{element_name}'"
        else:
            # Fallback to coordinates
            x = data.get("x", 0)
            y = data.get("y", 0)
            verb = "Right-click" if action == ActionType.RIGHT_CLICK else "Click"
            return f"{verb} at coordinates ({x}, {y})"
    
    def _create_selector(self, element_name: str, element_type: str, 
                        data: dict) -> Selector:
        """Create selector with text primary and coordinate fallback"""
        
        x = data.get("x", 0)
        y = data.get("y", 0)
        
        if element_name:
            # Text-based primary selector with coordinate fallback
            return Selector(
                type="text",
                value=element_name,
                fallback=Selector(
                    type="coordinates",
                    value={"x": x, "y": y}
                )
            )
        else:
            # Coordinates only
            return Selector(
                type="coordinates",
                value={"x": x, "y": y}
            )
    
    def _format_key_name(self, key: str) -> str:
        """Format key name for display"""
        key_map = {
            "enter": "Enter",
            "esc": "Escape",
            "escape": "Escape",
            "space": "Space",
            "tab": "Tab",
            "backspace": "Backspace",
            "delete": "Delete",
            "up": "↑",
            "down": "↓",
            "left": "←",
            "right": "→"
        }
        return key_map.get(key.lower(), key.capitalize())
    
    def _parse_key_combination(self, keys: List[str]) -> str:
        """Parse key combination into readable format"""
        # Clean up key representations
        key_parts = []
        for key in keys:
            key_str = str(key).lower()
            
            if "ctrl" in key_str:
                key_parts.append("Ctrl")
            elif "alt" in key_str:
                key_parts.append("Alt")
            elif "shift" in key_str:
                key_parts.append("Shift")
            elif "'\\x03'" in key_str or "c" in key_str:
                key_parts.append("C")
            elif "'\\x16'" in key_str or "v" in key_str:
                key_parts.append("V")
            else:
                key_parts.append(key_str.replace("'", "").upper())
        
        return "+".join(key_parts)
    
    # ============================================================================
    # WORKFLOW INTELLIGENCE
    # ============================================================================
    
    def _infer_workflow_intent(self, steps: List[WorkflowStep], 
                               session: SessionTimeline) -> Tuple[str, str]:
        """Infer workflow name and description from steps"""
        
        # Analyze steps to understand intent
        has_typing = any(s.action == ActionType.TYPE_TEXT for s in steps)
        has_search = any("search" in s.description.lower() for s in steps)
        has_video = any("video" in s.description.lower() for s in steps)
        has_youtube = any("youtube" in s.description.lower() or 
                         "rick astley" in s.description.lower() for s in steps)
        
        # Generate appropriate name
        if has_youtube and has_video:
            name = "Search and Watch YouTube Video"
            description = "User searches for a video on YouTube and interacts with it"
        elif has_search and has_typing:
            # Extract search query if available
            search_step = next((s for s in steps if s.action == ActionType.TYPE_TEXT), None)
            if search_step:
                query = search_step.parameters.get("text", "")
                if query:
                    name = f"Search for '{query}'"
                    description = f"User performs a web search for '{query}' and navigates results"
                else:
                    name = "Web Search and Navigation"
                    description = "User performs a web search and navigates through results"
            else:
                name = "Web Search and Navigation"
                description = "User performs a web search and navigates through results"
        else:
            name = f"{session.application} - User Session"
            description = f"Recorded user session in {session.application}"
        
        return name, description
    
    def _enrich_workflow(self, workflow: WorkflowDefinition, 
                        session: SessionTimeline) -> WorkflowDefinition:
        """Post-process workflow to ensure quality"""
        
        # Ensure all steps have proper selectors
        for step in workflow.steps:
            if step.selector and step.selector.type == "text" and not step.selector.value:
                # Try to find element info from original session
                # This is a safety net in case AI didn't extract element names
                matching_event = self._find_matching_event(step, session)
                if matching_event:
                    element_name = matching_event.data.get("element_name")
                    if element_name:
                        step.selector.value = element_name
        
        return workflow
    
    def _find_matching_event(self, step: WorkflowStep, 
                            session: SessionTimeline) -> Optional[EventLog]:
        """Find the original event that corresponds to a workflow step"""
        # This is a helper for post-processing
        # Match by timestamp or action type + coordinates
        for event in session.events:
            if step.selector and step.selector.fallback:
                fallback_coords = step.selector.fallback.value
                if isinstance(fallback_coords, dict):
                    event_x = event.data.get("x", 0)
                    event_y = event.data.get("y", 0)
                    if event_x == fallback_coords.get("x") and event_y == fallback_coords.get("y"):
                        return event
        return None
    
    # ============================================================================
    # UTILITY
    # ============================================================================
    
    def _extract_json(self, text: str) -> dict:
        """Extract JSON from AI response text"""
        
        # Try to find JSON in the response
        text = text.strip()
        
        # If wrapped in code blocks, extract
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        # Parse JSON
        return json.loads(text)