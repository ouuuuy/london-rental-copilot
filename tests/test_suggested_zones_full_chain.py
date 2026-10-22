"""
Regression test for suggested_zones propagation.
Mimics the Streamlit import path and verifies the full call chain.
"""
import os
import sys
import json

import pytest

# Add app to path (same as Streamlit does)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from dotenv import load_dotenv
load_dotenv()

# Simulate a stale sys.modules cache by pre-loading the module,
# then forcing a reload exactly as main.py does.
import agents.requirement_parser as rp_mod
import importlib
importlib.reload(rp_mod)

from agents.requirement_parser import RequirementParser

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable",
)


def test_suggested_zones_not_empty():
    parser = RequirementParser()
    query = "2-bed flat under £1,800, commute to Canary Wharf in 30 min, want nightlife"
    result = parser.parse(query)

    suggested = result.get("suggested_zones", [])
    warnings = result.get("constraint_warnings", [])

    print("=== Full Chain Test Result ===")
    print(f"suggested_zones count: {len(suggested)}")
    print(f"constraint_warnings count: {len(warnings)}")
    print(json.dumps(suggested, indent=2, ensure_ascii=False))

    assert isinstance(suggested, list), "suggested_zones must be a list"
    assert len(suggested) > 0, "suggested_zones should not be empty for this query"
    for zone in suggested:
        assert "name" in zone, "Each suggestion must have a name"
        assert "rationale" in zone, "Each suggestion must have a rationale"
        assert isinstance(zone["name"], str) and zone["name"].strip()
        assert isinstance(zone["rationale"], str) and zone["rationale"].strip()

    print("[PASS] suggested_zones full chain test passed.")


if __name__ == "__main__":
    test_suggested_zones_not_empty()
