import sys
sys.path.insert(0, '.')
"""Test with realistic login scenario"""
import json
from datetime import datetime

from src.services.bedrock_client import BedrockClient

def test_realistic():
    session_data = {
        "session_id": "login-demo-001",
        "start_time": datetime.now().isoformat(),
        "application": "Chrome Browser",
        "events": [
            {
                "event_id": "evt-001",
                "timestamp": datetime.now().isoformat(),
                "event_type": "MOUSE_CLICK",
                "data": {"x": 540, "y": 320, "button": "left"},
                "ocr_text": "Login Page\nUsername:\nPassword:\nRemember me\nSign In"
            },
            {
                "event_id": "evt-002",
                "timestamp": datetime.now().isoformat(),
                "event_type": "TEXT_INPUT",
                "data": {"text": "admin@company.com"}
            },
            {
                "event_id": "evt-003",
                "timestamp": datetime.now().isoformat(),
                "event_type": "MOUSE_CLICK",
                "data": {"x": 540, "y": 420, "button": "left"},
                "ocr_text": "Login Page\nUsername: admin@company.com\nPassword:\nRemember me\nSign In"
            },
            {
                "event_id": "evt-004",
                "timestamp": datetime.now().isoformat(),
                "event_type": "TEXT_INPUT",
                "data": {"text": "SecurePass123"}
            },
            {
                "event_id": "evt-005",
                "timestamp": datetime.now().isoformat(),
                "event_type": "MOUSE_CLICK",
                "data": {"x": 540, "y": 520, "button": "left"},
                "ocr_text": "Login Page\nUsername: admin@company.com\nPassword: ••••••••••••\nRemember me\nSign In"
            }
        ]
    }
    
    client = BedrockClient()
    print("Generating workflow from login scenario...")
    result = client.generate_workflow(session_data, [])
    
    # Parse JSON
    clean = result.strip()
    if "```json" in clean:
        clean = clean[clean.find("```json")+7:clean.find("```", clean.find("```json")+7)].strip()
    
    workflow = json.loads(clean)
    
    print(f"\nWorkflow: {workflow['name']}")
    print(f"Description: {workflow['description']}")
    print(f"\nSteps:")
    for step in workflow['steps']:
        print(f"  {step['step_id']}: {step['action']}")
        print(f"    {step['description']}")
        if step.get('selector'):
            print(f"    Selector: {step['selector']['type']} = {step['selector']['value']}")
            if step['selector'].get('fallback'):
                print(f"    Fallback: {step['selector']['fallback']['value']}")
        print()

if __name__ == "__main__":
    test_realistic()