"""
Custom Workflow Validation Metrics
Domain-specific quality checks for workflow generation
"""
import json
from typing import Dict, List, Tuple

class WorkflowMetrics:
    """Calculate custom metrics for workflow quality"""
    
    @staticmethod
    def validate_selector_accuracy(workflow: dict) -> Tuple[float, Dict]:
        """
        Check if keyboard actions have null selectors
        and mouse actions have proper selectors
        
        Returns: (score 0-1, details dict)
        """
        if not workflow or "steps" not in workflow:
            return 0.0, {"error": "Invalid workflow structure"}
        
        steps = workflow["steps"]
        if not steps:
            return 0.0, {"error": "No steps found"}
        
        keyboard_actions = ["TYPE_TEXT", "PRESS_KEY", "KEY_COMBINATION"]
        mouse_actions = ["CLICK", "RIGHT_CLICK", "DOUBLE_CLICK", "DRAG", "SCROLL"]
        
        correct_keyboard = 0
        total_keyboard = 0
        correct_mouse = 0
        total_mouse = 0
        
        for step in steps:
            action = step.get("action", "")
            selector = step.get("selector")
            
            if action in keyboard_actions:
                total_keyboard += 1
                if selector is None:
                    correct_keyboard += 1
            
            elif action in mouse_actions:
                total_mouse += 1
                if selector is not None:
                    correct_mouse += 1
        
        # Calculate score
        total_checks = total_keyboard + total_mouse
        correct_checks = correct_keyboard + correct_mouse
        
        score = correct_checks / total_checks if total_checks > 0 else 0.0
        
        details = {
            "keyboard_accuracy": correct_keyboard / total_keyboard if total_keyboard > 0 else 1.0,
            "mouse_accuracy": correct_mouse / total_mouse if total_mouse > 0 else 1.0,
            "total_keyboard": total_keyboard,
            "correct_keyboard": correct_keyboard,
            "total_mouse": total_mouse,
            "correct_mouse": correct_mouse
        }
        
        return score, details
    
    @staticmethod
    def validate_drag_parameters(workflow: dict) -> Tuple[float, Dict]:
        """
        Check if DRAG actions have end_x and end_y in parameters
        
        Returns: (score 0-1, details dict)
        """
        if not workflow or "steps" not in workflow:
            return 0.0, {"error": "Invalid workflow structure"}
        
        drag_steps = [s for s in workflow["steps"] if s.get("action") == "DRAG"]
        
        if not drag_steps:
            return 1.0, {"message": "No DRAG actions to validate"}
        
        correct_drags = 0
        for step in drag_steps:
            params = step.get("parameters", {})
            if "end_x" in params and "end_y" in params:
                correct_drags += 1
        
        score = correct_drags / len(drag_steps)
        
        details = {
            "total_drags": len(drag_steps),
            "correct_drags": correct_drags,
            "missing_parameters": len(drag_steps) - correct_drags
        }
        
        return score, details
    
    @staticmethod
    def validate_element_extraction(workflow: dict) -> Tuple[float, Dict]:
        """
        Check if element names are extracted for mouse actions
        
        Returns: (score 0-1, details dict)
        """
        if not workflow or "steps" not in workflow:
            return 0.0, {"error": "Invalid workflow structure"}
        
        mouse_actions = ["CLICK", "RIGHT_CLICK", "DOUBLE_CLICK", "DRAG"]
        mouse_steps = [s for s in workflow["steps"] if s.get("action") in mouse_actions]
        
        if not mouse_steps:
            return 1.0, {"message": "No mouse actions to validate"}
        
        with_elements = 0
        for step in mouse_steps:
            selector = step.get("selector")
            if selector and selector.get("type") == "text" and selector.get("value"):
                with_elements += 1
        
        score = with_elements / len(mouse_steps)
        
        details = {
            "total_mouse_actions": len(mouse_steps),
            "with_element_names": with_elements,
            "without_element_names": len(mouse_steps) - with_elements,
            "extraction_rate": f"{score*100:.1f}%"
        }
        
        return score, details
    
    @staticmethod
    def validate_key_format(workflow: dict) -> Tuple[float, Dict]:
        """
        Check if key names are clean (no "Key." prefix)
        
        Returns: (score 0-1, details dict)
        """
        if not workflow or "steps" not in workflow:
            return 0.0, {"error": "Invalid workflow structure"}
        
        key_steps = [s for s in workflow["steps"] 
                    if s.get("action") in ["PRESS_KEY", "KEY_COMBINATION"]]
        
        if not key_steps:
            return 1.0, {"message": "No key actions to validate"}
        
        clean_keys = 0
        for step in key_steps:
            params = step.get("parameters", {})
            key = params.get("key", "")
            keys = params.get("keys", [])
            
            # Check single key
            if key and not key.startswith("Key."):
                clean_keys += 1
            # Check key combination
            elif keys and not any(str(k).startswith("Key.") for k in keys):
                clean_keys += 1
        
        score = clean_keys / len(key_steps)
        
        details = {
            "total_key_actions": len(key_steps),
            "clean_format": clean_keys,
            "has_prefix": len(key_steps) - clean_keys
        }
        
        return score, details
    
    @staticmethod
    def validate_action_grouping(workflow: dict) -> Tuple[float, Dict]:
        """
        Check if sequential typing is grouped properly
        Look for absence of multiple TYPE_TEXT + PRESS_KEY(space) sequences
        
        Returns: (score 0-1, details dict)
        """
        if not workflow or "steps" not in workflow:
            return 0.0, {"error": "Invalid workflow structure"}
        
        steps = workflow["steps"]
        
        # Count typing patterns that should be grouped
        ungrouped_sequences = 0
        i = 0
        while i < len(steps) - 2:
            if (steps[i].get("action") == "TYPE_TEXT" and
                i + 1 < len(steps) and 
                steps[i+1].get("action") == "PRESS_KEY" and
                steps[i+1].get("parameters", {}).get("key") == "space"):
                ungrouped_sequences += 1
                i += 2
            else:
                i += 1
        
        # Perfect score if no ungrouped sequences found
        # Deduct points for each ungrouped sequence
        max_sequences = len([s for s in steps if s.get("action") == "TYPE_TEXT"])
        if max_sequences == 0:
            return 1.0, {"message": "No typing actions to validate"}
        
        score = max(0, 1.0 - (ungrouped_sequences * 0.2))  # -20% per ungrouped sequence
        
        details = {
            "ungrouped_sequences": ungrouped_sequences,
            "total_type_actions": max_sequences,
            "grouping_quality": "Good" if ungrouped_sequences == 0 else "Needs improvement"
        }
        
        return score, details
    
    @staticmethod
    def calculate_overall_score(workflow: dict) -> Tuple[float, Dict]:
        """
        Calculate aggregate quality score across all metrics
        
        Returns: (score 0-1, detailed breakdown)
        """
        selector_score, selector_details = WorkflowMetrics.validate_selector_accuracy(workflow)
        drag_score, drag_details = WorkflowMetrics.validate_drag_parameters(workflow)
        element_score, element_details = WorkflowMetrics.validate_element_extraction(workflow)
        key_score, key_details = WorkflowMetrics.validate_key_format(workflow)
        grouping_score, grouping_details = WorkflowMetrics.validate_action_grouping(workflow)
        
        # Weighted average (adjust weights as needed)
        weights = {
            "selector": 0.30,  # 30% - Most critical
            "drag": 0.15,  # 15%
            "element": 0.25,  # 25%
            "key": 0.15,  # 15%
            "grouping": 0.15  # 15%
        }
        
        overall = (
            selector_score * weights["selector"] +
            drag_score * weights["drag"] +
            element_score * weights["element"] +
            key_score * weights["key"] +
            grouping_score * weights["grouping"]
        )
        
        details = {
            "overall_score": overall,
            "individual_scores": {
                "selector_accuracy": selector_score,
                "drag_parameters": drag_score,
                "element_extraction": element_score,
                "key_format": key_score,
                "action_grouping": grouping_score
            },
            "details": {
                "selector": selector_details,
                "drag": drag_details,
                "element": element_details,
                "key": key_details,
                "grouping": grouping_details
            }
        }
        
        return overall, details


# Convenience function
def evaluate_workflow(workflow_json: str | dict) -> Dict:
    """
    Evaluate a workflow and return all metrics
    
    Args:
        workflow_json: Workflow as JSON string or dict
    
    Returns:
        Dictionary with all metrics and scores
    """
    if isinstance(workflow_json, str):
        workflow = json.loads(workflow_json)
    else:
        workflow = workflow_json
    
    score, details = WorkflowMetrics.calculate_overall_score(workflow)
    
    return {
        "overall_score": score,
        "grade": "A" if score >= 0.9 else "B" if score >= 0.8 else "C" if score >= 0.7 else "D" if score >= 0.6 else "F",
        **details
    }