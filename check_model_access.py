"""
Check which Bedrock models you have access to
Tests the 3 recommended models for workflow generation
"""
import boto3
from botocore.exceptions import ClientError
import os

# Models to test - THE BEST 3 ACTUALLY AVAILABLE
models_to_test = [
    {
        "id": "amazon.nova-pro-v1:0",
        "name": "Amazon Nova Pro",
        "description": "Your current model - Best balanced performance"
    },
    {
        "id": "amazon.nova-lite-v1:0",
        "name": "Amazon Nova Lite",
        "description": "Faster & cheaper - Good for speed comparison"
    },
    {
    "id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "name": "Claude 3.5 Sonnet v2",
    "description": "Latest stable Claude"
    }
]

def test_model_access(model_id: str, model_name: str, region: str) -> dict:
    """
    Test if a model is accessible
    
    Returns:
        dict with status, message, and latency
    """
    try:
        # Initialize Bedrock Runtime client
        client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region
        )
        
        # Simple test message
        import time
        import json
        
        start_time = time.time()
        
        # Build request body
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": "Say OK"}]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 10,
                "temperature": 0
            }
        }
        
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        elapsed = time.time() - start_time
        
        return {
            "status": "✅ ACCESSIBLE",
            "message": "Model is ready to use",
            "latency": f"{elapsed:.2f}s",
            "success": True
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == "AccessDeniedException":
            return {
                "status": "❌ NO ACCESS",
                "message": "Model not enabled - Enable in Bedrock Console",
                "latency": "N/A",
                "success": False
            }
        elif error_code == "ValidationException":
            if "model ID" in error_message.lower():
                return {
                    "status": "❌ NOT FOUND",
                    "message": "Model ID not available in your region",
                    "latency": "N/A",
                    "success": False
                }
            elif "throughput" in error_message.lower():
                return {
                    "status": "⚠️  THROUGHPUT ISSUE",
                    "message": "Model requires provisioned throughput - Try different region",
                    "latency": "N/A",
                    "success": False
                }
            else:
                return {
                    "status": "⚠️  VALIDATION ERROR",
                    "message": error_message[:100],
                    "latency": "N/A",
                    "success": False
                }
        elif error_code == "ResourceNotFoundException":
            return {
                "status": "❌ NOT FOUND",
                "message": "Model not available in this region",
                "latency": "N/A",
                "success": False
            }
        else:
            return {
                "status": "❌ ERROR",
                "message": f"{error_code}: {error_message[:100]}",
                "latency": "N/A",
                "success": False
            }
            
    except Exception as e:
        return {
            "status": "❌ ERROR",
            "message": str(e)[:150],
            "latency": "N/A",
            "success": False
        }


def check_all_models():
    """Check access to all recommended models"""
    
    print("\n" + "="*70)
    print("🔍 CHECKING MODEL ACCESS")
    print("="*70)
    
    # Get region from environment or use default
    region = os.environ.get("AWS_REGION", "us-east-1")
    print(f"\nAWS Region: {region}")
    print(f"Testing {len(models_to_test)} models...\n")
    
    results = []
    accessible_count = 0
    
    for model in models_to_test:
        model_id = model["id"]
        model_name = model["name"]
        description = model["description"]
        
        print(f"Testing: {model_name}")
        print(f"  ID: {model_id}")
        print(f"  Purpose: {description}")
        
        result = test_model_access(model_id, model_name, region)
        results.append({
            "model": model,
            "result": result
        })
        
        print(f"  Status: {result['status']}")
        print(f"  {result['message']}")
        if result['latency'] != "N/A":
            print(f"  Latency: {result['latency']}")
        print()
        
        if result['success']:
            accessible_count += 1
    
    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Accessible models: {accessible_count}/{len(models_to_test)}\n")
    
    # Show accessible models
    accessible_models = [r for r in results if r['result']['success']]
    if accessible_models:
        print("✅ Ready to use:")
        for r in accessible_models:
            print(f"  • {r['model']['name']}")
    
    # Show inaccessible models
    inaccessible_models = [r for r in results if not r['result']['success']]
    if inaccessible_models:
        print("\n❌ Need to enable:")
        for r in inaccessible_models:
            print(f"  • {r['model']['name']}")
            print(f"    Reason: {r['result']['message']}")
        
        print("\n📝 HOW TO ENABLE MODELS:")
        print("  1. Go to: https://console.aws.amazon.com/bedrock/")
        print("  2. Click: 'Model access' in left menu")
        print("  3. Click: 'Manage model access' button")
        print("  4. Check boxes for:")
        for r in inaccessible_models:
            print(f"     ☑️  {r['model']['name']}")
        print("  5. Click: 'Request model access'")
        print("  6. Wait 2-5 minutes for approval")
        print("  7. Run this script again to verify")
    
    print("\n" + "="*70)
    
    # Exit code
    if accessible_count == len(models_to_test):
        print("✅ ALL MODELS ACCESSIBLE - Ready for evaluation!")
        print("="*70 + "\n")
        return True
    elif accessible_count > 0:
        print(f"⚠️  {accessible_count}/{len(models_to_test)} models ready - Enable others to continue")
        print("="*70 + "\n")
        return False
    else:
        print("❌ NO MODELS ACCESSIBLE - Enable models in Bedrock Console")
        print("="*70 + "\n")
        return False


if __name__ == "__main__":
    import sys
    
    try:
        all_accessible = check_all_models()
        
        # Exit with appropriate code
        sys.exit(0 if all_accessible else 1)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("\nPossible issues:")
        print("  • AWS credentials not configured")
        print("  • boto3 not installed (pip install boto3)")
        print("  • Network connectivity issue")
        import traceback
        traceback.print_exc()
        sys.exit(2)