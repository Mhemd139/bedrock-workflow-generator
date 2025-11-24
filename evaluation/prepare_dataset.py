"""
Prepare evaluation dataset from test cases
Converts test sessions to format needed for AWS Bedrock evaluation
"""
import json
import os
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from evaluation.config import config
from src.tools.format_converter import convert_friend_format


class DatasetPreparation:
    """Prepare test dataset for evaluation"""
    
    def __init__(self):
        self.base_dir = Path("evaluation")
        self.test_cases_dir = self.base_dir / "test_cases"
        self.ground_truth_dir = self.base_dir / "ground_truth"
        self.output_dir = self.base_dir / "results"
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def save_test_case(self, session_data: dict, category: str, name: str):
        """
        Save a test case to the appropriate category folder
        
        Args:
            session_data: The session JSON (in friend's format)
            category: 'simple', 'medium', or 'complex'
            name: Unique name for this test case
        """
        category_dir = self.test_cases_dir / category
        category_dir.mkdir(exist_ok=True, parents=True)
        
        filepath = category_dir / f"{name}.json"
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print(f"✅ Saved test case: {category}/{name}.json")
    
    def load_all_test_cases(self) -> List[Dict]:
        """
        Load all test cases from all categories
        
        Returns:
            List of (category, name, session_data) tuples
        """
        test_cases = []
        
        for category in ["simple", "medium", "complex"]:
            category_dir = self.test_cases_dir / category
            
            if not category_dir.exists():
                continue
            
            for filepath in category_dir.glob("*.json"):
                with open(filepath, 'r') as f:
                    session_data = json.load(f)
                
                test_cases.append({
                    "category": category,
                    "name": filepath.stem,
                    "filepath": str(filepath),
                    "session_data": session_data
                })
        
        return test_cases
    
    def create_evaluation_jsonl(self, output_filename: str = "evaluation_dataset.jsonl"):
        """
        Create JSONL file for AWS Bedrock evaluation
        
        Format:
        {"prompt": "session data...", "reference": "expected workflow..."}
        """
        test_cases = self.load_all_test_cases()
        
        if not test_cases:
            print("❌ No test cases found! Please add test cases first.")
            return None
        
        output_path = self.output_dir / output_filename
        
        with open(output_path, 'w') as f:
            for tc in test_cases:
                # Convert to SessionTimeline format
                session = convert_friend_format(tc["session_data"])
                session_dict = session.model_dump(mode="json")
                
                # Create prompt (this is what we send to the model)
                prompt = f"Generate a workflow definition from this session: {json.dumps(session_dict)}"
                
                # Load ground truth if exists
                ground_truth_file = self.ground_truth_dir / f"{tc['name']}.json"
                if ground_truth_file.exists():
                    with open(ground_truth_file, 'r') as gt:
                        reference = json.load(gt)
                else:
                    reference = None  # Will generate later
                
                # Write JSONL entry
                entry = {
                    "prompt": prompt,
                    "reference": json.dumps(reference) if reference else "",
                    "category": tc["category"],
                    "name": tc["name"]
                }
                
                f.write(json.dumps(entry) + "\n")
        
        print(f"✅ Created evaluation dataset: {output_path}")
        print(f"   Total test cases: {len(test_cases)}")
        
        return str(output_path)
    
    def generate_ground_truth_template(self, session_data: dict, name: str):
        """
        Generate a template ground truth workflow
        You'll need to manually verify/edit this
        
        Args:
            session_data: The session JSON
            name: Test case name
        """
        from src.services.bedrock_client import BedrockClient
        from src.core.workflow_generator import WorkflowGenerator
        
        # Convert and generate workflow
        session = convert_friend_format(session_data)
        generator = WorkflowGenerator(BedrockClient())
        workflow = generator.generate_from_session(session)
        
        # Save as ground truth template
        output_file = self.ground_truth_dir / f"{name}.json"
        
        with open(output_file, 'w') as f:
            json.dump(workflow.model_dump(mode="json"), f, indent=2)
        
        print(f"✅ Generated ground truth template: {output_file}")
        print(f"   ⚠️  Please manually verify this workflow is correct!")
    
    def create_summary_report(self):
        """Generate a summary of the test dataset"""
        test_cases = self.load_all_test_cases()
        
        summary = {
            "total_cases": len(test_cases),
            "by_category": {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        for category in ["simple", "medium", "complex"]:
            count = len([tc for tc in test_cases if tc["category"] == category])
            summary["by_category"][category] = count
        
        # Save summary
        summary_file = self.output_dir / "dataset_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("\n" + "="*60)
        print("DATASET SUMMARY")
        print("="*60)
        print(f"Total test cases: {summary['total_cases']}")
        print(f"  - Simple: {summary['by_category'].get('simple', 0)}")
        print(f"  - Medium: {summary['by_category'].get('medium', 0)}")
        print(f"  - Complex: {summary['by_category'].get('complex', 0)}")
        print("="*60)
        
        return summary


# Convenience functions for quick usage
def add_test_case(session_json_path: str, category: str, name: str):
    """
    Quick function to add a test case
    
    Args:
        session_json_path: Path to the session JSON file
        category: 'simple', 'medium', or 'complex'
        name: Unique identifier for this test case
    """
    with open(session_json_path, 'r') as f:
        session_data = json.load(f)
    
    prep = DatasetPreparation()
    prep.save_test_case(session_data, category, name)


def prepare_for_evaluation():
    """
    Main function to prepare dataset for evaluation
    Call this after adding all test cases
    """
    prep = DatasetPreparation()
    
    # Generate summary
    summary = prep.create_summary_report()
    
    if summary["total_cases"] == 0:
        print("\n⚠️  No test cases found!")
        print("Add test cases using: add_test_case(path, category, name)")
        return None
    
    # Create JSONL for AWS Bedrock
    jsonl_path = prep.create_evaluation_jsonl()
    
    return jsonl_path


# Quick script to add your Rick Astley example
if __name__ == "__main__":
    # Example: Add the Rick Astley session as a complex test case
    rick_astley_path = "path/to/your/rick_astley_session.json"  # Update this!
    
    if os.path.exists(rick_astley_path):
        add_test_case(rick_astley_path, "complex", "youtube_rick_astley")
        print("✅ Added Rick Astley test case!")
    else:
        print("ℹ️  To add test cases, use:")
        print("   add_test_case('session.json', 'complex', 'test_name')")