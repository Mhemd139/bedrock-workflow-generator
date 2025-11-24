"""
List ALL available Bedrock models in your region
This will show us exactly what's accessible
"""
import boto3
import json
from botocore.exceptions import ClientError

def list_all_models():
    """List all foundation models available in Bedrock"""
    
    region = "us-east-1"
    
    try:
        # Use 'bedrock' service (not bedrock-runtime) to list models
        client = boto3.client(
            service_name="bedrock",
            region_name=region
        )
        
        print("\n" + "="*70)
        print("📋 LISTING ALL AVAILABLE BEDROCK MODELS")
        print("="*70)
        print(f"Region: {region}\n")
        
        # Get all foundation models
        response = client.list_foundation_models()
        
        models = response.get('modelSummaries', [])
        
        if not models:
            print("❌ No models found!")
            return
        
        print(f"Found {len(models)} total models\n")
        
        # Group by provider
        by_provider = {}
        for model in models:
            provider = model.get('providerName', 'Unknown')
            if provider not in by_provider:
                by_provider[provider] = []
            by_provider[provider].append(model)
        
        # Show the ones we care about
        target_providers = ['Anthropic', 'Mistral AI', 'DeepSeek', 'Cohere', 'Meta']
        
        for provider in target_providers:
            if provider in by_provider:
                print(f"\n{'='*70}")
                print(f"🔹 {provider} Models")
                print(f"{'='*70}")
                
                for model in by_provider[provider]:
                    model_id = model.get('modelId', 'N/A')
                    model_name = model.get('modelName', 'N/A')
                    input_mods = ', '.join(model.get('inputModalities', []))
                    output_mods = ', '.join(model.get('outputModalities', []))
                    
                    print(f"\n  Model: {model_name}")
                    print(f"  ID: {model_id}")
                    print(f"  Input: {input_mods}")
                    print(f"  Output: {output_mods}")
        
        print("\n" + "="*70)
        print("💾 Saving full list to 'available_models.json'")
        print("="*70)
        
        # Save to file for reference
        with open('available_models.json', 'w') as f:
            json.dump(models, f, indent=2, default=str)
        
        print("\n✅ Done! Check available_models.json for complete list")
        
    except ClientError as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have permissions for bedrock:ListFoundationModels")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    list_all_models()