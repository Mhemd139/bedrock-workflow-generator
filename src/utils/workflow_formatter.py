from src.models.workflow import WorkflowDefinition
from typing import Dict, Any

def format_workflow_as_text(workflow: WorkflowDefinition) -> str:
    """
    Convert WorkflowDefinition to human-readable text format
    """
    lines = []
    
    # Header
    lines.append("=" * 70)
    lines.append(f"   WORKFLOW: {workflow.name}")
    lines.append("=" * 70)
    lines.append("")
    
    # Metadata
    lines.append(f"Description: {workflow.description}")
    if workflow.application:
        lines.append(f"Application: {workflow.application}")
    lines.append(f"Version: {workflow.version}")
    lines.append(f"Workflow ID: {workflow.workflow_id}")
    lines.append(f"Total Steps: {len(workflow.steps)}")
    lines.append("")
    
    # Steps
    lines.append("=" * 70)
    lines.append("   WORKFLOW STEPS")
    lines.append("=" * 70)
    lines.append("")
    
    for idx, step in enumerate(workflow.steps, 1):
        lines.append("-" * 70)
        lines.append(f"STEP {idx}: {step.step_id}")
        lines.append("-" * 70)
        lines.append(f"Action: {step.action}")
        lines.append(f"Description: {step.description}")
        lines.append("")
        
        # Selector details
        if step.selector:
            lines.append("Target:")
            if step.selector.type == "coordinates":
                coords = step.selector.value
                if isinstance(coords, dict):
                    # Handle DRAG action with start/end coordinates
                    if "start_x" in coords:
                        lines.append(f"  • Drag from ({coords['start_x']}, {coords['start_y']}) to ({coords['end_x']}, {coords['end_y']})")
                    else:
                        lines.append(f"  • Coordinates: ({coords.get('x', 0)}, {coords.get('y', 0)})")
            elif step.selector.type == "text":
                lines.append(f"  • Text Selector: \"{step.selector.value}\"")
                if step.selector.fallback:
                    fb = step.selector.fallback.value
                    lines.append(f"  • Fallback Coordinates: ({fb.get('x', 0)}, {fb.get('y', 0)})")
            lines.append("")
        
        # Parameters
        if step.parameters:
            lines.append("Parameters:")
            for key, value in step.parameters.items():
                lines.append(f"  • {key}: {value}")
            lines.append("")
        
        # Execution settings
        lines.append("Execution Settings:")
        lines.append(f"  • Wait After: {step.wait_after}s")
        lines.append(f"  • Retry Count: {step.retry_count}")
        lines.append(f"  • On Failure: {step.on_failure}")
        lines.append("")
    
    # Footer
    lines.append("=" * 70)
    lines.append("   END OF WORKFLOW")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def format_workflow_as_dict(workflow: WorkflowDefinition) -> Dict[str, Any]:
    """
    Convert WorkflowDefinition to dictionary for JSON serialization
    """
    return workflow.model_dump(mode="json")