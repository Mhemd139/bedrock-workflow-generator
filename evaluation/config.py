"""
Evaluation Configuration
Contains all settings for model evaluation
"""
import os
from typing import List, Dict

class EvaluationConfig:
    """Configuration for model evaluation"""
    
    # AWS Settings
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET = os.getenv("S3_BUCKET_NAME", "bedrock-workflow-evaluation")
    S3_EVALUATION_PREFIX = "evaluation-data"
    S3_RESULTS_PREFIX = "evaluation-results"
    
    MODELS_TO_EVALUATE: List[Dict[str, str]] = [
        {
            "id": "amazon.nova-pro-v1:0",
            "name": "Amazon Nova Pro",
            "short_name": "nova-pro"
        },
        {
            "id": "amazon.nova-lite-v1:0",
            "name": "Amazon Nova Lite",
            "short_name": "nova-lite"
        },
        {
            "id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "name": "Claude 3.5 Sonnet",
            "short_name": "claude-3.5"
        }
    ]

    MODEL_PRICING = {
        "amazon.nova-pro-v1:0": {"input": 0.0008, "output": 0.0032},
        "amazon.nova-lite-v1:0": {"input": 0.00006, "output": 0.00024},
        "anthropic.claude-3-5-sonnet-20240620-v1:0": {"input": 0.003, "output": 0.015}
    }
            
    # Evaluation Dataset Sizes
    NUM_SIMPLE_CASES = 10
    NUM_MEDIUM_CASES = 10
    NUM_COMPLEX_CASES = 10
    
    # Evaluation Thresholds (Quality targets)
    MIN_SELECTOR_ACCURACY = 0.90  # 90%
    MIN_ELEMENT_EXTRACTION = 0.80  # 80%
    MIN_OVERALL_QUALITY = 0.85  # 85%
    
    
    # Test Case Categories
    SIMPLE_WORKFLOWS = [
        "open_app_single_click",
        "type_text_submit",
        "right_click_menu",
        "single_button_click",
        "scroll_page"
    ]
    
    MEDIUM_WORKFLOWS = [
        "search_query_click_result",
        "copy_text_selection",
        "paste_and_submit",
        "multiple_clicks_sequence",
        "drag_to_select"
    ]
    
    COMPLEX_WORKFLOWS = [
        "youtube_video_search",  # Your Rick Astley example
        "multi_window_navigation",
        "form_filling_multiple_inputs",
        "file_operations",
        "drag_copy_paste_combo"
    ]

# Singleton instance
config = EvaluationConfig()