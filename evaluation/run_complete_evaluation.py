"""
Complete evaluation pipeline
Runs everything: preparation, evaluation, analysis
"""
from evaluation.prepare_dataset import DatasetPreparation, prepare_for_evaluation
from evaluation.run_fmeval import run_evaluation
from evaluation.analyze_results import ResultsAnalyzer


def run_complete_pipeline():
    """
    Run the complete evaluation pipeline
    1. Prepare dataset
    2. Run evaluation on all models
    3. Analyze and compare results
    """
    print("\n" + "="*60)
    print("COMPLETE EVALUATION PIPELINE")
    print("="*60)
    
    # Step 1: Prepare dataset
    print("\n[STEP 1/3] Preparing dataset...")
    prep = DatasetPreparation()
    summary = prep.create_summary_report()
    
    if summary["total_cases"] == 0:
        print("\n❌ No test cases found!")
        print("Please add test cases first using prepare_dataset.py")
        return
    
    # Step 2: Run evaluation
    print("\n[STEP 2/3] Running evaluation on all models...")
    print("This may take 10-20 minutes depending on test case count...")
    results = run_evaluation()
    
    if not results:
        print("\n❌ Evaluation failed!")
        return
    
    # Step 3: Analyze results
    print("\n[STEP 3/3] Analyzing results...")
    analyzer = ResultsAnalyzer()
    analyzer.analyze_all()
    
    print("\n" + "="*60)
    print("✅ COMPLETE PIPELINE FINISHED!")
    print("="*60)
    print("\nCheck evaluation/results/analysis/ for:")
    print("- Comparison tables (Excel)")
    print("- Charts (PNG)")
    print("- Decision report (TXT)")


if __name__ == "__main__":
    run_complete_pipeline()