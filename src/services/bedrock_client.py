import json
import boto3
import base64
from typing import Optional
from botocore.config import Config


class BedrockClient:
    def __init__(self, region: str = "us-east-1", model_id: str = "amazon.nova-pro-v1:0"):
        self.region = region
        self.model_id = model_id
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region,
            config=Config(retries={"max_attempts": 3, "mode": "adaptive"})
        )
    
    def analyze_screenshot(self, image_base64: str, prompt: str) -> str:
        """Analyze a screenshot with Nova Pro vision capabilities"""
        
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "png",
                                "source": {
                                    "bytes": image_base64
                                }
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 4096,
                "temperature": 0.1,
                "topP": 0.9
            }
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        response_body = json.loads(response["body"].read())
        return response_body["output"]["message"]["content"][0]["text"]
    
    def generate_workflow(self, session_data: dict, screenshots: list[str]) -> str:
        """Generate workflow definition from session timeline and screenshots"""
        
        prompt = f"""You are an expert at analyzing user interaction recordings and generating structured automation workflows.

    CRITICAL FOUNDATION RULES:
    ═══════════════════════════════════════════════════════════════════

    1️⃣ **COORDINATES ARE FOR MOUSE COMMANDS ONLY**
    ⚠️ THIS IS ABSOLUTELY CRITICAL ⚠️
    
    MOUSE COMMANDS (use coordinates):
    - CLICK, RIGHT_CLICK, DOUBLE_CLICK, DRAG, SCROLL
    - These actions target specific screen locations
    - MUST have selector with coordinates
    
    KEYBOARD COMMANDS (NO coordinates):
    - TYPE_TEXT, PRESS_KEY, KEY_COMBINATION
    - These actions send input to focused element
    - MUST have selector: null

    2️⃣ **ELEMENT NAME USAGE**
    - Extract "element_name" from event data
    - Use for mouse command selectors (CLICK, DRAG, etc.)
    - Provides semantic meaning and reliability

    3️⃣ **ACTION GROUPING**
    - Combine: TYPE + PRESS(space) + TYPE → Single TYPE_TEXT
    - Keep: DRAG + KEY_COMBINATION(Ctrl+C) separate but semantically linked

    ═══════════════════════════════════════════════════════════════════

    SESSION DATA:
    {json.dumps(session_data, indent=2, default=str)}

    ═══════════════════════════════════════════════════════════════════
    DETAILED RULES BY ACTION TYPE:
    ═══════════════════════════════════════════════════════════════════

    🖱️ **MOUSE COMMANDS** (CLICK, RIGHT_CLICK, DOUBLE_CLICK, SCROLL, DRAG)

    RULE: ALWAYS include selector with coordinates

    Structure:
    {{
    "action": "CLICK" | "RIGHT_CLICK" | "DOUBLE_CLICK" | "SCROLL" | "DRAG",
    "description": "Human-readable description using element_name",
    "selector": {{
        "type": "text",
        "value": "Extract from element_name field",
        "fallback": {{
        "type": "coordinates",
        "value": {{"x": number, "y": number}}
        }}
    }},
    "parameters": {{
        // For DRAG: MUST include "end_x" and "end_y"
        // For SCROLL: "delta_y": number
    }}
    }}

    SPECIAL CASE - Empty Element Names:
    If element_name is empty, "Unknown", or "N/A":
    {{
    "selector": {{
        "type": "coordinates",
        "value": {{"x": number, "y": number}}
    }}
    }}

    DRAG vs SCROLL Detection:
    - IF start_x > 1800 (scrollbar region) → action: "SCROLL"
    - IF element_name exists → action: "DRAG"
    - DRAG MUST have: "parameters": {{"end_x": number, "end_y": number}}

    ───────────────────────────────────────────────────────────────────

    ⌨️ **KEYBOARD COMMANDS** (TYPE_TEXT, PRESS_KEY, KEY_COMBINATION)

    RULE: NEVER include selector (set to null)

    Structure:
    {{
    "action": "TYPE_TEXT" | "PRESS_KEY" | "KEY_COMBINATION",
    "description": "Human-readable description of keyboard action",
    "selector": null,  // ⚠️ CRITICAL: No selector for keyboard!
    "parameters": {{
        // For TYPE_TEXT: "text": "string"
        // For PRESS_KEY: "key": "keyname" (no "Key." prefix)
        // For KEY_COMBINATION: "keys": ["Ctrl", "C"]
    }}
    }}

    KEY NAME FORMAT:
    ✅ Correct: "enter", "esc", "space", "tab"
    ❌ Wrong: "Key.enter", "Key.esc", "Key.space"

    ═══════════════════════════════════════════════════════════════════
    PERFECT EXAMPLES:
    ═══════════════════════════════════════════════════════════════════

    ✅ EXAMPLE 1: CLICK (Mouse - With Element Name)
    {{
    "step_id": "step-1",
    "action": "RIGHT_CLICK",
    "description": "Right-click on Firefox window to open context menu",
    "selector": {{
        "type": "text",
        "value": "Firefox - 1 running window",
        "fallback": {{
        "type": "coordinates",
        "value": {{"x": 170, "y": 1176}}
        }}
    }},
    "parameters": {{}},
    "screenshot_before": null,
    "screenshot_after": null,
    "wait_after": 0.5,
    "retry_count": 3,
    "on_failure": "stop"
    }}

    ✅ EXAMPLE 2: CLICK (Mouse - No Element Name)
    {{
    "step_id": "step-5",
    "action": "CLICK",
    "description": "Click to focus window",
    "selector": {{
        "type": "coordinates",
        "value": {{"x": 653, "y": 359}}
    }},
    "parameters": {{}},
    "screenshot_before": null,
    "screenshot_after": null,
    "wait_after": 0.5,
    "retry_count": 3,
    "on_failure": "stop"
    }}

    ✅ EXAMPLE 3: TYPE_TEXT (Keyboard - No Selector!)
    {{
    "step_id": "step-3",
    "action": "TYPE_TEXT",
    "description": "Type search query 'never gonna give pu uo'",
    "selector": null,
    "parameters": {{
        "text": "never gonna give pu uo"
    }},
    "screenshot_before": null,
    "screenshot_after": null,
    "wait_after": 0.5,
    "retry_count": 3,
    "on_failure": "stop"
    }}

    ✅ EXAMPLE 4: PRESS_KEY (Keyboard - No Selector!)
    {{
    "step_id": "step-4",
    "action": "PRESS_KEY",
    "description": "Press Enter to submit search query",
    "selector": null,
    "parameters": {{
        "key": "enter"
    }},
    "screenshot_before": null,
    "screenshot_after": null,
    "wait_after": 0.5,
    "retry_count": 3,
    "on_failure": "stop"
    }}

    ✅ EXAMPLE 5: DRAG (Mouse - Must Have end_x/end_y)
    {{
    "step_id": "step-15",
    "action": "DRAG",
    "description": "Drag to select 'Rick Astley' channel name",
    "selector": {{
        "type": "text",
        "value": "Rick Astley",
        "fallback": {{
        "type": "coordinates",
        "value": {{"x": 107, "y": 955}}
        }}
    }},
    "parameters": {{
        "end_x": 158,
        "end_y": 957
    }},
    "screenshot_before": null,
    "screenshot_after": null,
    "wait_after": 0.5,
    "retry_count": 3,
    "on_failure": "stop"
    }}

    ✅ EXAMPLE 6: KEY_COMBINATION (Keyboard - No Selector!)
    {{
    "step_id": "step-17",
    "action": "KEY_COMBINATION",
    "description": "Copy selected text to clipboard (Ctrl+C)",
    "selector": null,
    "parameters": {{
        "keys": ["Ctrl", "C"]
    }},
    "screenshot_before": null,
    "screenshot_after": null,
    "wait_after": 0.5,
    "retry_count": 3,
    "on_failure": "stop"
    }}

    ✅ EXAMPLE 7: SCROLL (Mouse - High X-Coordinate)
    {{
    "step_id": "step-6",
    "action": "SCROLL",
    "description": "Scroll down the search results page",
    "selector": {{
        "type": "coordinates",
        "value": {{"x": 1917, "y": 269}}
    }},
    "parameters": {{
        "delta_y": 141
    }},
    "screenshot_before": null,
    "screenshot_after": null,
    "wait_after": 0.5,
    "retry_count": 3,
    "on_failure": "stop"
    }}

    ═══════════════════════════════════════════════════════════════════
    COMMON MISTAKES TO AVOID:
    ═══════════════════════════════════════════════════════════════════

    ❌ WRONG: TYPE_TEXT with selector
    {{
    "action": "TYPE_TEXT",
    "selector": {{"type": "text", "value": "Search"}}  // ❌ NO!
    }}

    ❌ WRONG: PRESS_KEY with coordinates
    {{
    "action": "PRESS_KEY",
    "selector": {{"type": "coordinates", "value": {{"x": 0, "y": 0}}}}  // ❌ NO!
    }}

    ❌ WRONG: KEY_COMBINATION with selector
    {{
    "action": "KEY_COMBINATION",
    "selector": {{"type": "text", "value": "Rick Astley"}}  // ❌ NO!
    }}

    ❌ WRONG: DRAG without end_x/end_y
    {{
    "action": "DRAG",
    "parameters": {{}}  // ❌ Must have end_x and end_y!
    }}

    ❌ WRONG: Key with "Key." prefix
    {{
    "parameters": {{"key": "Key.enter"}}  // ❌ Should be "enter"
    }}

    ═══════════════════════════════════════════════════════════════════
    OPTIMIZATION RULES:
    ═══════════════════════════════════════════════════════════════════

    1. **Group Sequential Typing:**
    - Input: TYPE "never" + PRESS space + TYPE "gonna" + PRESS space...
    - Output: Single TYPE_TEXT with "never gonna give pu uo"

    2. **Semantic Descriptions:**
    - Use element names: "Click on 'Rick Astley' video link"
    - Not coordinates: "Click at (866, 363)"

    3. **Context Awareness:**
    - "Copy 'Rick Astley' to clipboard" (not just "Press Ctrl+C")
    - "Press Enter to submit search query" (not just "Press Enter")

    4. **Remove Duplicate Steps:**
    - If two consecutive DRAG actions select the same element
    - Keep only the final, complete selection

    ═══════════════════════════════════════════════════════════════════
    FINAL VALIDATION CHECKLIST:
    ═══════════════════════════════════════════════════════════════════

    Before outputting, verify:
    ✅ All MOUSE commands (CLICK, DRAG, SCROLL) have selectors
    ✅ All KEYBOARD commands (TYPE_TEXT, PRESS_KEY, KEY_COMBINATION) have selector: null
    ✅ All DRAG actions have end_x and end_y in parameters
    ✅ All key names are clean (no "Key." prefix)
    ✅ Element names are used for mouse command selectors when available
    ✅ Descriptions are semantic and context-aware
    ✅ Sequential typing is grouped into single TYPE_TEXT

    ═══════════════════════════════════════════════════════════════════

    OUTPUT SCHEMA:
    {{
        "workflow_id": "string",
        "name": "string - descriptive workflow name",
        "description": "string - what this workflow accomplishes",
        "version": "1.0.0",
        "application": "string - target application",
        "steps": [
            {{
                "step_id": "step-N",
                "action": "CLICK|RIGHT_CLICK|TYPE_TEXT|PRESS_KEY|KEY_COMBINATION|SCROLL|DRAG",
                "description": "string - semantic description",
                "selector": {{...}} | null,  // null for keyboard, object for mouse
                "parameters": {{}},
                "screenshot_before": null,
                "screenshot_after": null,
                "wait_after": 0.5,
                "retry_count": 3,
                "on_failure": "stop"
            }}
        ],
        "variables": {{}},
        "preconditions": [],
        "metadata": {{}}
    }}

    Generate the workflow JSON now:"""

        # Build content with text and optional screenshots
        content = []
        
        # Add screenshots if provided
        if screenshots:
            for i, screenshot_base64 in enumerate(screenshots):
                content.append({
                    "image": {
                        "format": "png",
                        "source": {
                            "bytes": screenshot_base64
                        }
                    }
                })
        
        # Add the text prompt
        content.append({"text": prompt})
        
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "inferenceConfig": {
                "maxTokens": 8192,
                "temperature": 0.1,
                "topP": 0.9
            }
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        response_body = json.loads(response["body"].read())
        return response_body["output"]["message"]["content"][0]["text"]
    
    def test_connection(self) -> bool:
        """Test if Bedrock connection works"""
        try:
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": "Say 'connected' if you receive this."}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 10,
                    "temperature": 0
                }
            }
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False