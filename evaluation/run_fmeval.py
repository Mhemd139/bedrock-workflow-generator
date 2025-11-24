"""
Run custom fmeval evaluation on multiple Bedrock models
Tests each model and applies custom workflow metrics
"""
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from evaluation.config import config
from evaluation.custom_metrics import WorkflowMetrics, evaluate_workflow
from evaluation.prepare_dataset import DatasetPreparation
from src.services.bedrock_client import BedrockClient
from src.tools.format_converter import convert_friend_format


class FMEvalRunner:
    """Run fmeval-style evaluation with custom metrics"""
    
    def __init__(self):
        self.results_dir = Path("evaluation/results")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        self.prep = DatasetPreparation()
    
    def evaluate_model(self, model_config: Dict[str, str], test_cases: List[Dict]) -> Dict:
        """
        Evaluate a single model on all test cases
        
        Args:
            model_config: Model configuration dict with id, name, short_name
            test_cases: List of test case dicts
        
        Returns:
            Evaluation results dictionary
        """
        model_id = model_config["id"]
        model_name = model_config["name"]
        
        print(f"\n{'='*60}")
        print(f"Evaluating: {model_name}")
        print(f"{'='*60}")
        
        # Initialize Bedrock client for this model
        client = BedrockClient(model_id=model_id)
        
        results = {
            "model_id": model_id,
            "model_name": model_name,
            "short_name": model_config["short_name"],
            "evaluated_at": datetime.utcnow().isoformat(),
            "test_cases": [],
            "aggregate_metrics": {}
        }
        
        total_cases = len(test_cases)
        
        for idx, test_case in enumerate(test_cases, 1):
            print(f"\n[{idx}/{total_cases}] Testing: {test_case['name']} ({test_case['category']})")
            
            try:
                # Convert session format
                session = convert_friend_format(test_case["session_data"])
                session_dict = session.model_dump(mode="json")
                
                # Time the generation
                start_time = time.time()
                
                # Generate workflow using this model
                workflow_json = client.generate_workflow(session_dict, [])
                
                elapsed_time = time.time() - start_time
                
                # Parse workflow
                workflow_json_clean = self._extract_json(workflow_json)
                workflow_dict = json.loads(workflow_json_clean) if isinstance(workflow_json_clean, str) else workflow_json_clean
                
                # Apply custom metrics
                metrics = evaluate_workflow(workflow_dict)
                
                # Store result
                case_result = {
                    "name": test_case["name"],
                    "category": test_case["category"],
                    "success": True,
                    "latency_seconds": round(elapsed_time, 2),
                    "overall_score": metrics["overall_score"],
                    "grade": metrics["grade"],
                    "individual_scores": metrics["individual_scores"],
                    "details": metrics["details"],
                    "workflow": workflow_dict
                }
                
                results["test_cases"].append(case_result)
                
                print(f"  ✅ Score: {metrics['overall_score']:.2%} (Grade: {metrics['grade']})")
                print(f"  ⏱️  Latency: {elapsed_time:.2f}s")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                
                results["test_cases"].append({
                    "name": test_case["name"],
                    "category": test_case["category"],
                    "success": False,
                    "error": str(e),
                    "overall_score": 0.0,
                    "grade": "F"
                })
        
        # Calculate aggregate metrics
        results["aggregate_metrics"] = self._calculate_aggregates(results["test_cases"])
        
        return results
    
    def evaluate_all_models(self) -> Dict[str, Any]:
        """
        Evaluate all configured models on all test cases
        
        Returns:
            Complete evaluation results for all models
        """
        print("\n" + "="*60)
        print("FMEVAL MODEL EVALUATION")
        print("="*60)
        
        # Load test cases
        test_cases = self.prep.load_all_test_cases()
        
        if not test_cases:
            print("❌ No test cases found! Run prepare_dataset.py first.")
            return None
        
        print(f"\nLoaded {len(test_cases)} test cases")
        print(f"Models to evaluate: {len(config.MODELS_TO_EVALUATE)}")
        
        # Evaluate each model
        all_results = {
            "evaluation_timestamp": datetime.utcnow().isoformat(),
            "total_test_cases": len(test_cases),
            "models": []
        }
        
        for model_config in config.MODELS_TO_EVALUATE:
            model_results = self.evaluate_model(model_config, test_cases)
            all_results["models"].append(model_results)
            
            # Save intermediate results
            self._save_model_results(model_results)
        
        # Save complete results
        self._save_complete_results(all_results)
        
        # Print summary
        self._print_summary(all_results)
        
        return all_results
    
    def _calculate_aggregates(self, test_results: List[Dict]) -> Dict:
        """Calculate aggregate metrics across all test cases"""
        successful_cases = [r for r in test_results if r.get("success", False)]
        
        if not successful_cases:
            return {
                "success_rate": 0.0,
                "average_score": 0.0,
                "average_latency": 0.0
            }
        
        # Overall metrics
        avg_score = sum(r["overall_score"] for r in successful_cases) / len(successful_cases)
        avg_latency = sum(r.get("latency_seconds", 0) for r in successful_cases) / len(successful_cases)
        
        # Individual metric averages
        individual_metrics = {}
        for metric_name in ["selector_accuracy", "drag_parameters", "element_extraction", 
                           "key_format", "action_grouping"]:
            scores = [r["individual_scores"][metric_name] for r in successful_cases 
                     if metric_name in r.get("individual_scores", {})]
            if scores:
                individual_metrics[metric_name] = sum(scores) / len(scores)
        
        # By category
        by_category = {}
        for category in ["simple", "medium", "complex"]:
            category_cases = [r for r in successful_cases if r["category"] == category]
            if category_cases:
                by_category[category] = {
                    "count": len(category_cases),
                    "average_score": sum(r["overall_score"] for r in category_cases) / len(category_cases)
                }
        
        return {
            "success_rate": len(successful_cases) / len(test_results),
            "total_successful": len(successful_cases),
            "total_failed": len(test_results) - len(successful_cases),
            "average_score": avg_score,
            "average_latency_seconds": round(avg_latency, 2),
            "individual_metrics": individual_metrics,
            "by_category": by_category
        }
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from AI response"""
        text = text.strip()
        
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        return text
    
    def _save_model_results(self, results: Dict):
        """Save results for a single model"""
        filename = f"{results['short_name']}_results.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Saved results: {filepath}")
    
    def _save_complete_results(self, all_results: Dict):
        """Save complete evaluation results"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"complete_evaluation_{timestamp}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\n💾 Saved complete results: {filepath}")
    
    def _print_summary(self, all_results: Dict):
        """Print evaluation summary"""
        print("\n" + "="*60)
        print("EVALUATION SUMMARY")
        print("="*60)
        
        for model_result in all_results["models"]:
            metrics = model_result["aggregate_metrics"]
            
            print(f"\n{model_result['model_name']}:")
            print(f"  Overall Score: {metrics['average_score']:.2%}")
            print(f"  Success Rate: {metrics['success_rate']:.2%}")
            print(f"  Avg Latency: {metrics['average_latency_seconds']:.2f}s")
            print(f"  Individual Metrics:")
            for metric, score in metrics.get("individual_metrics", {}).items():
                print(f"    - {metric}: {score:.2%}")
        
        print("\n" + "="*60)


def run_evaluation():
    """Main function to run fmeval evaluation"""
    runner = FMEvalRunner()
    results = runner.evaluate_all_models()
    return results


if __name__ == "__main__":
    print("Starting fmeval evaluation...")
    results = run_evaluation()
    print("\n✅ Evaluation complete!")