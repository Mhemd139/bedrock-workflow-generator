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
        
        prompt = f"""Analyze this user session recording and generate a structured workflow definition.

SESSION DATA:
{json.dumps(session_data, indent=2, default=str)}

Based on the event logs and screenshots provided, create a JSON workflow definition that can replay these actions.

Output ONLY valid JSON matching this schema:
{{
    "workflow_id": "string",
    "name": "string - descriptive name for the workflow",
    "description": "string - what this workflow accomplishes",
    "version": "1.0.0",
    "application": "string - target application name",
    "steps": [
        {{
            "step_id": "string",
            "action": "CLICK|TYPE_TEXT|PRESS_KEY|DOUBLE_CLICK|RIGHT_CLICK|SCROLL|DRAG|WAIT|NAVIGATE",
            "description": "string - human readable description",
            "selector": {{
                "type": "text",
                "value": "visible text or label of UI element",
                "fallback": {{
                    "type": "coordinates",
                    "value": {{"x": number, "y": number}}
                }}
            }},
            "parameters": {{}},
            "wait_after": 0.5,
            "retry_count": 3,
            "on_failure": "stop"
        }}
    ],
    "variables": {{}},
    "preconditions": [],
    "metadata": {{}}
}}

IMPORTANT: For CLICK actions, ALWAYS include both:
1. Primary selector with type "text" (the visible label/text of the element)
2. Fallback selector with type "coordinates" (the exact x,y from event data)

This ensures workflows are both intelligent (text-based) and reliable (coordinate backup).

Generate the workflow JSON:"""

        # For now, text-only analysis (we'll add vision in next iteration)
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