"""
Analyze and compare evaluation results
Generate comparison tables and charts
"""
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict
import matplotlib.pyplot as plt
from datetime import datetime

from evaluation.config import config


class ResultsAnalyzer:
    """Analyze and visualize evaluation results"""
    
    def __init__(self, results_dir: str = "evaluation/results"):
        self.results_dir = Path(results_dir)
        self.output_dir = self.results_dir / "analysis"
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def load_latest_results(self) -> Dict:
        """Load the most recent complete evaluation results"""
        complete_files = list(self.results_dir.glob("complete_evaluation_*.json"))
        
        if not complete_files:
            print("❌ No evaluation results found!")
            return None
        
        # Get most recent
        latest_file = max(complete_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, 'r') as f:
            results = json.load(f)
        
        print(f"✅ Loaded results from: {latest_file.name}")
        return results
    
    def create_comparison_table(self, results: Dict) -> pd.DataFrame:
        """Create comparison table of all models"""
        
        rows = []
        
        for model_result in results["models"]:
            metrics = model_result["aggregate_metrics"]
            individual = metrics.get("individual_metrics", {})
            
            # Calculate cost (estimated)
            pricing = config.MODEL_PRICING.get(model_result["model_id"], {})
            # Rough estimate: 5000 input tokens, 3000 output tokens per workflow
            cost_per_workflow = (pricing.get("input", 0) * 5 + pricing.get("output", 0) * 3)
            
            row = {
                "Model": model_result["model_name"],
                "Overall Score": f"{metrics['average_score']:.1%}",
                "Selector Accuracy": f"{individual.get('selector_accuracy', 0):.1%}",
                "Element Extraction": f"{individual.get('element_extraction', 0):.1%}",
                "DRAG Parameters": f"{individual.get('drag_parameters', 0):.1%}",
                "Key Format": f"{individual.get('key_format', 0):.1%}",
                "Action Grouping": f"{individual.get('action_grouping', 0):.1%}",
                "Success Rate": f"{metrics['success_rate']:.1%}",
                "Avg Latency (s)": f"{metrics['average_latency_seconds']:.2f}",
                "Cost per 1000": f"${cost_per_workflow*1000:.2f}"
            }
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Save to Excel
        excel_path = self.output_dir / "model_comparison.xlsx"
        df.to_excel(excel_path, index=False)
        print(f"✅ Saved comparison table: {excel_path}")
        
        # Also save as CSV
        csv_path = self.output_dir / "model_comparison.csv"
        df.to_csv(csv_path, index=False)
        
        return df
    
    def create_detailed_breakdown(self, results: Dict) -> pd.DataFrame:
        """Create detailed breakdown by test case category"""
        
        rows = []
        
        for model_result in results["models"]:
            model_name = model_result["model_name"]
            by_category = model_result["aggregate_metrics"].get("by_category", {})
            
            for category, data in by_category.items():
                row = {
                    "Model": model_name,
                    "Category": category.capitalize(),
                    "Test Cases": data["count"],
                    "Average Score": f"{data['average_score']:.1%}"
                }
                rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Save
        excel_path = self.output_dir / "category_breakdown.xlsx"
        df.to_excel(excel_path, index=False)
        print(f"✅ Saved category breakdown: {excel_path}")
        
        return df
    
    def create_score_chart(self, results: Dict):
        """Create bar chart comparing overall scores"""
        
        models = []
        scores = []
        
        for model_result in results["models"]:
            models.append(model_result["model_name"])
            scores.append(model_result["aggregate_metrics"]["average_score"] * 100)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(models, scores, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        
        ax.set_ylabel('Overall Score (%)', fontsize=12)
        ax.set_title('Model Evaluation: Overall Quality Score', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom', fontsize=10)
        
        # Add threshold line
        ax.axhline(y=config.MIN_OVERALL_QUALITY * 100, color='green', 
                  linestyle='--', label=f'Target: {config.MIN_OVERALL_QUALITY*100}%')
        ax.legend()
        
        plt.tight_layout()
        
        # Save
        chart_path = self.output_dir / "score_comparison.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved score chart: {chart_path}")
        
        plt.close()
    
    def create_cost_performance_chart(self, results: Dict):
        """Create scatter plot of cost vs performance"""
        
        models = []
        scores = []
        costs = []
        
        for model_result in results["models"]:
            model_id = model_result["model_id"]
            pricing = config.MODEL_PRICING.get(model_id, {})
            cost_per_workflow = (pricing.get("input", 0) * 5 + pricing.get("output", 0) * 3) * 1000
            
            models.append(model_result["model_name"])
            scores.append(model_result["aggregate_metrics"]["average_score"] * 100)
            costs.append(cost_per_workflow)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        scatter = ax.scatter(costs, scores, s=200, alpha=0.6, c=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        
        # Add labels
        for i, model in enumerate(models):
            ax.annotate(model, (costs[i], scores[i]), 
                       xytext=(10, 10), textcoords='offset points',
                       fontsize=9, fontweight='bold')
        
        ax.set_xlabel('Cost per 1000 Workflows ($)', fontsize=12)
        ax.set_ylabel('Overall Score (%)', fontsize=12)
        ax.set_title('Model Evaluation: Cost vs Performance', fontsize=14, fontweight='bold')
        
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save
        chart_path = self.output_dir / "cost_performance.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved cost-performance chart: {chart_path}")
        
        plt.close()
    
    def generate_decision_report(self, results: Dict) -> str:
        """Generate a decision report with recommendation"""
        
        # Find best model
        best_model = max(results["models"], 
                        key=lambda m: m["aggregate_metrics"]["average_score"])
        
        best_name = best_model["model_name"]
        best_score = best_model["aggregate_metrics"]["average_score"]
        
        # Calculate cost
        pricing = config.MODEL_PRICING.get(best_model["model_id"], {})
        cost = (pricing.get("input", 0) * 5 + pricing.get("output", 0) * 3) * 1000
        
        report = f"""
MODEL SELECTION DECISION REPORT
{'='*60}

Evaluation Date: {results['evaluation_timestamp']}
Total Test Cases: {results['total_test_cases']}
Models Evaluated: {len(results['models'])}

RECOMMENDED MODEL: {best_name}
{'='*60}

Key Metrics:
- Overall Quality Score: {best_score:.1%}
- Success Rate: {best_model['aggregate_metrics']['success_rate']:.1%}
- Average Latency: {best_model['aggregate_metrics']['average_latency_seconds']:.2f}s
- Cost per 1000 workflows: ${cost:.2f}

Individual Scores:
"""
        
        for metric, score in best_model["aggregate_metrics"]["individual_metrics"].items():
            report += f"- {metric.replace('_', ' ').title()}: {score:.1%}\n"
        
        report += f"\n{'='*60}\n"
        report += "COMPARISON WITH ALTERNATIVES:\n"
        report += f"{'='*60}\n\n"
        
        for model_result in results["models"]:
            if model_result["model_name"] == best_name:
                continue
            
            score = model_result["aggregate_metrics"]["average_score"]
            pricing = config.MODEL_PRICING.get(model_result["model_id"], {})
            alt_cost = (pricing.get("input", 0) * 5 + pricing.get("output", 0) * 3) * 1000
            
            score_diff = (best_score - score) * 100
            cost_diff = ((cost - alt_cost) / alt_cost * 100) if alt_cost > 0 else 0
            
            report += f"{model_result['model_name']}:\n"
            report += f"- Score: {score:.1%} ({score_diff:+.1f}% vs recommended)\n"
            report += f"- Cost: ${alt_cost:.2f} ({cost_diff:+.1f}% vs recommended)\n"
            
            if score > best_score:
                report += f"  Note: Higher quality but ${alt_cost - cost:.2f} more expensive\n"
            elif alt_cost < cost:
                report += f"  Note: ${cost - alt_cost:.2f} cheaper but {-score_diff:.1f}% lower quality\n"
            
            report += "\n"
        
        report += f"{'='*60}\n"
        report += "DECISION RATIONALE:\n"
        report += f"{'='*60}\n\n"
        report += f"Selected {best_name} based on:\n"
        report += f"1. Highest overall quality score ({best_score:.1%})\n"
        report += f"2. Meets minimum quality threshold ({config.MIN_OVERALL_QUALITY:.1%})\n"
        report += f"3. Best cost-performance ratio for production use\n"
        
        # Save report
        report_path = self.output_dir / "decision_report.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"✅ Saved decision report: {report_path}")
        
        return report
    
    def analyze_all(self):
        """Run complete analysis"""
        print("\n" + "="*60)
        print("RESULTS ANALYSIS")
        print("="*60)
        
        # Load results
        results = self.load_latest_results()
        
        if not results:
            return
        
        # Create all outputs
        print("\nGenerating comparison table...")
        self.create_comparison_table(results)
        
        print("Generating category breakdown...")
        self.create_detailed_breakdown(results)
        
        print("Creating score chart...")
        self.create_score_chart(results)
        
        print("Creating cost-performance chart...")
        self.create_cost_performance_chart(results)
        
        print("Generating decision report...")
        report = self.generate_decision_report(results)
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE!")
        print("="*60)
        print(f"\nAll outputs saved to: {self.output_dir}")
        print("\nFiles created:")
        print("- model_comparison.xlsx")
        print("- category_breakdown.xlsx")
        print("- score_comparison.png")
        print("- cost_performance.png")
        print("- decision_report.txt")
        
        # Print report summary
        print("\n" + report)


if __name__ == "__main__":
    analyzer = ResultsAnalyzer()
    analyzer.analyze_all()