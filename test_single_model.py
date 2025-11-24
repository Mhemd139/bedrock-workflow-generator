"""
Quick test with a single model
"""
import json
from evaluation.prepare_dataset import DatasetPreparation
from evaluation.custom_metrics import evaluate_workflow
from src.services.bedrock_client import BedrockClient
from src.tools.format_converter import convert_friend_format

# Load the test case
prep = DatasetPreparation()
test_cases = prep.load_all_test_cases()

if not test_cases:
    print("❌ No test cases found!")
    exit(1)

print(f"✅ Found {len(test_cases)} test case(s)")

# Test with Nova Pro
test_case = test_cases[0]
print(f"\n🧪 Testing: {test_case['name']}")

# Convert session
session = convert_friend_format(test_case["session_data"])
session_dict = session.model_dump(mode="json")

# Generate workflow
print("⏳ Generating workflow with Nova Pro...")
client = BedrockClient(model_id="amazon.nova-pro-v1:0")
workflow_json = client.generate_workflow(session_dict, [])

# Extract and parse
if "```json" in workflow_json:
    start = workflow_json.find("```json") + 7
    end = workflow_json.find("```", start)
    workflow_json = workflow_json[start:end].strip()

workflow = json.loads(workflow_json)

# Evaluate
print("📊 Evaluating quality...")
metrics = evaluate_workflow(workflow)

# Print results
print("\n" + "="*60)
print("RESULTS")
print("="*60)
print(f"Overall Score: {metrics['overall_score']:.1%}")
print(f"Grade: {metrics['grade']}")
print(f"\nIndividual Scores:")
for metric, score in metrics['individual_scores'].items():
    print(f"  - {metric.replace('_', ' ').title()}: {score:.1%}")

print("\n✅ Single model test successful!")
print("Ready to run full evaluation on all models.")