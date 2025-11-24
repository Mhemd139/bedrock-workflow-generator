# Model Evaluation Guide

Complete guide for evaluating Bedrock models for workflow generation.

## Quick Start

### 1. Add Your Test Cases
```python
from evaluation.prepare_dataset import add_test_case

# Add your Rick Astley example
add_test_case("rick_astley_session.json", "complex", "youtube_rick_astley")

# Add more test cases
add_test_case("simple_click.json", "simple", "single_click")
add_test_case("search_form.json", "medium", "search_and_click")
```

### 2. Run Complete Evaluation
```bash
python -m evaluation.run_complete_evaluation
```

This will:
- Prepare your dataset
- Evaluate all 3 models (Nova Pro, Nova Lite, Claude Sonnet)
- Generate comparison reports and charts

### 3. View Results

Check `evaluation/results/analysis/` for:
- `model_comparison.xlsx` - Side-by-side comparison
- `score_comparison.png` - Quality scores chart
- `cost_performance.png` - Cost vs quality scatter plot
- `decision_report.txt` - Recommendation with rationale

## Step-by-Step Guide

### Step 1: Add Test Cases

Place your session JSON files in:
- `evaluation/test_cases/simple/` - Simple workflows
- `evaluation/test_cases/medium/` - Medium complexity
- `evaluation/test_cases/complex/` - Complex workflows

Or use the helper:
```python
from evaluation.prepare_dataset import add_test_case
add_test_case("path/to/session.json", "category", "unique_name")
```

### Step 2: Run Evaluation
```bash
# Run everything
python -m evaluation.run_complete_evaluation

# Or run individually:
python -m evaluation.run_fmeval  # Evaluate models
python -m evaluation.analyze_results  # Analyze results
```

### Step 3: Review Results

Open the Excel files and view charts in `evaluation/results/analysis/`

## Custom Metrics

The evaluation measures:

1. **Selector Accuracy** (30% weight)
   - Keyboard actions have `selector: null`
   - Mouse actions have proper selectors

2. **DRAG Parameters** (15% weight)
   - DRAG actions include `end_x` and `end_y`

3. **Element Extraction** (25% weight)
   - Element names used when available

4. **Key Format** (15% weight)
   - Keys don't have "Key." prefix

5. **Action Grouping** (15% weight)
   - Sequential typing is grouped properly

## Configuration

Edit `evaluation/config.py` to:
- Change models to evaluate
- Adjust quality thresholds
- Update pricing information

## Troubleshooting

**No test cases found?**
- Add test cases using `add_test_case()`

**Model access denied?**
- Enable models in AWS Bedrock console → Model access

**Results look wrong?**
- Check `evaluation/results/*.json` for raw data
- Verify test cases are valid

## For Hackathon Presentation

Use these outputs:
1. `model_comparison.xlsx` - Show in slide
2. `score_comparison.png` - Visual comparison
3. `cost_performance.png` - Cost-benefit analysis
4. `decision_report.txt` - Justification for model choice
```

---

## ✅ **ALL FILES CREATED!**

You now have a complete evaluation system:
```
evaluation/
├── config.py                    # Configuration
├── custom_metrics.py            # Workflow quality metrics
├── prepare_dataset.py           # Dataset preparation
├── run_fmeval.py               # Model evaluation
├── analyze_results.py          # Results analysis
├── run_complete_evaluation.py  # Main pipeline
├── README.md                   # Usage guide
├── test_cases/                 # Your test sessions
│   ├── simple/
│   ├── medium/
│   └── complex/
├── ground_truth/               # Expected outputs
└── results/                    # Evaluation outputs
    └── analysis/               # Charts & reports