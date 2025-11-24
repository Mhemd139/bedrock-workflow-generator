"""
Quick script to add test cases for evaluation
"""
from evaluation.prepare_dataset import add_test_case

# Add the Rick Astley session
add_test_case("rick_astley_session.json", "complex", "youtube_rick_astley")

print("\n✅ Test case added!")
print("Ready to run evaluation.")