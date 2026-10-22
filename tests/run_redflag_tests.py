import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from agents.redflag_detector import RedFlagDetector

def main():
    with open("data/sample_listings.json", "r", encoding="utf-8") as f:
        listings = json.load(f)

    test_ids = ["listing_003", "listing_004", "listing_005", "listing_006", "listing_008"]
    detector = RedFlagDetector()

    results = {}
    for lid in test_ids:
        listing = next(l for l in listings if l["id"] == lid)
        print(f"\n{'='*60}")
        print(f"Testing {lid}: {listing['title']}")
        print(f"{'='*60}")
        result = detector.analyze(listing)
        results[lid] = result
        print(json.dumps(result, indent=2, ensure_ascii=False))

    with open("tests/redflag_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n\nAll results saved to tests/redflag_results.json")

if __name__ == "__main__":
    main()
