"""
Collect RedFlagDetector predictions for all 30 sample listings.
Results are cached to data/redflag_predictions.json so evaluation can be
re-run without consuming API tokens.
"""
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from agents.redflag_detector import RedFlagDetector


def main():
    detector = RedFlagDetector()

    listings_path = os.path.join("data", "sample_listings.json")
    output_path = os.path.join("data", "redflag_predictions.json")

    with open(listings_path, "r", encoding="utf-8") as f:
        listings = json.load(f)

    predictions = {}
    for listing in listings:
        lid = listing["id"]
        print(f"Analyzing {lid}...")
        result = detector.analyze(listing)
        predictions[lid] = result

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=2, ensure_ascii=False)

    print(f"\nSaved predictions for {len(predictions)} listings to {output_path}")


if __name__ == "__main__":
    main()
