"""Quick smoke test for ComparisonGenerator."""
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load env before importing agents
load_dotenv()

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from agents.comparison_generator import ComparisonGenerator
from utils.cost_calculator import CostCalculator


def main():
    with open("data/sample_listings.json", "r", encoding="utf-8") as f:
        listings = json.load(f)

    calc = CostCalculator()
    comparator = ComparisonGenerator()

    # Pick first 2 listings for a quick test
    selected = listings[:2]
    results = []
    for listing in selected:
        cost = calc.calculate_true_cost(listing, work_zone="1")
        results.append({"listing": listing, "cost": cost})

    print("=== INPUT ===")
    for r in results:
        print(f"- {r['listing']['title']} | true_cost={r['cost']['true_cost']}")

    print("\n=== COMPARISON RESULT ===")
    comparison = comparator.compare(results)
    output_path = Path("tests/comparison_test_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    print(f"Result saved to {output_path}")
    print(json.dumps(comparison, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
