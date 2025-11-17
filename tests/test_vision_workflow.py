"""Test workflow generation with screenshots"""
import sys
import json
from datetime import datetime
sys.path.insert(0, '.')

from src.services.bedrock_client import BedrockClient
from src.services.image_processor import ImageProcessor

def test_vision_workflow():
    print("Testing workflow generation WITH screenshots...")
    
    # Create test image
    processor = ImageProcessor()
    test_image = processor.create_test_image()
    image_base64 = processor.image_to_base64(test_image)
    
    print(f"Created test image: {processor.get_image_info(test_image)}")
    print(f"Base64 length: {len(image_base64)} chars")
    
    # Create simple session data
    session_data = {
        "session_id": "vision-test-001",
        "start_time": datetime.now().isoformat(),
        "events": [
            {
                "event_id": "evt-001",
                "timestamp": datetime.now().isoformat(),
                "event_type": "MOUSE_CLICK",
                "coordinates": {"x": 400, "y": 300},
                "screenshot_ref": "screenshot_001.png"
            }
        ]
    }
    
    # Call Bedrock with screenshot
    client = BedrockClient()
    print("\nSending to Nova Pro with screenshot...")
    
    result = client.generate_workflow(session_data, [image_base64])
    
    print("\n--- NOVA PRO RESPONSE ---")
    print(result)
    print("--- END RESPONSE ---")
    
    # Try to parse JSON
    # Try to parse JSON (strip markdown if present)
    try:
        # Strip markdown code blocks if present
        clean_result = result.strip()
        if "```json" in clean_result:
            start = clean_result.find("```json") + 7
            end = clean_result.find("```", start)
            clean_result = clean_result[start:end].strip()
        elif "```" in clean_result:
            start = clean_result.find("```") + 3
            end = clean_result.find("```", start)
            clean_result = clean_result[start:end].strip()
        
        workflow = json.loads(clean_result)
        print("\n✅ Valid JSON returned!")
        print(f"Workflow name: {workflow.get('name', 'N/A')}")
        print(f"Steps: {len(workflow.get('steps', []))}")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON parsing failed: {e}")

if __name__ == "__main__":
    test_vision_workflow()