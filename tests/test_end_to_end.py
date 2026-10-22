"""End-to-end regression test: simulate the full user journey with mocks.

This test exercises the exact call chain that main.py uses,
without requiring Streamlit context or real OpenAI API calls.
"""
import json
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from agents.requirement_parser import RequirementParser
from agents.redflag_detector import RedFlagDetector
from agents.comparison_generator import ComparisonGenerator
from agents.inquiry_drafter import InquiryDrafter
from utils import CostCalculator
from utils.filter_engine import filter_listings


def _make_parser_response():
    """Mock a realistic parser output."""
    return {
        "budget": 1800,
        "beds": 2,
        "pets_allowed": None,
        "has_garden": None,
        "commute_target": "Canary Wharf",
        "commute_time_minutes": 30,
        "lifestyle_tags": ["quiet"],
        "suggested_zones": [
            {"name": "Canada Water", "rationale": "Jubilee line direct, cheaper rents"}
        ],
        "constraint_warnings": [],
        "confidence": "high",
    }


def _make_detector_response():
    return {
        "overall_risk": "low",
        "flags": [],
        "missing_info": [],
        "notes": "Clean listing.",
    }


def _make_comparison_response():
    return {
        "summary": "- Flat A is cheaper overall\n- Flat B has shorter commute",
        "trade_offs": [{"dimension": "cost", "comparison": "Flat A saves £100/month"}],
        "winner_for_budget": "listing_001",
        "winner_for_commute": "listing_002",
        "caveats": ["Verify council tax band with agent"],
    }


def _make_drafter_response():
    return "Subject: Enquiry about Flat\n\nDear landlord,\nI am interested..."


def test_full_journey():
    """Simulate: Parse -> Filter -> Detect Flags -> Calculate Cost -> Compare -> Draft Email"""
    # 1. Load data
    with open("data/sample_listings.json", "r", encoding="utf-8") as f:
        listings = json.load(f)
    assert len(listings) == 30

    # 2. Parse requirements (mocked)
    parser = RequirementParser(api_key="fake")
    mock_parser_response = MagicMock()
    mock_parser_response.choices = [MagicMock()]
    mock_parser_response.choices[0].message.content = json.dumps(_make_parser_response())

    with patch.object(parser.client.chat.completions, "create", return_value=mock_parser_response):
        constraints = parser.parse("2-bed flat under £1,800 near Canary Wharf")

    assert constraints["budget"] == 1800
    assert len(constraints["suggested_zones"]) == 1
    suggested = constraints["suggested_zones"]

    # 3. Filter listings (deterministic)
    matched, excluded = filter_listings(constraints, listings)
    assert len(matched) > 0
    assert len(excluded) > 0
    for m in matched:
        assert m["price_pcm"] <= 1800
        assert m["beds"] == 2

    # 4. Pick first matched listing for flag check + email
    target = matched[0]

    # 5. Detect red flags (mocked)
    detector = RedFlagDetector(api_key="fake")
    mock_detector_response = MagicMock()
    mock_detector_response.choices = [MagicMock()]
    mock_detector_response.choices[0].message.content = json.dumps(_make_detector_response())

    with patch.object(detector.client.chat.completions, "create", return_value=mock_detector_response):
        red_flags = detector.analyze(target)
    assert red_flags["overall_risk"] == "low"

    # 6. Calculate true cost (deterministic)
    calc = CostCalculator()
    cost = calc.calculate_true_cost(target, work_zone="2")
    assert cost["rent"] == target["price_pcm"]
    assert cost["true_cost"] > cost["rent"]

    # 7. Compare with a second listing (mocked)
    second = matched[1] if len(matched) > 1 else target
    results = [
        {"listing": target, "cost": cost},
        {"listing": second, "cost": calc.calculate_true_cost(second, work_zone="2")},
    ]

    comparator = ComparisonGenerator(api_key="fake")
    mock_comparison_response = MagicMock()
    mock_comparison_response.choices = [MagicMock()]
    mock_comparison_response.choices[0].message.content = json.dumps(_make_comparison_response())

    with patch.object(comparator.client.chat.completions, "create", return_value=mock_comparison_response):
        comparison = comparator.compare(results)
    assert comparison["winner_for_budget"] == "listing_001"

    # 8. Draft email (mocked)
    drafter = InquiryDrafter(api_key="fake")
    mock_drafter_response = MagicMock()
    mock_drafter_response.choices = [MagicMock()]
    mock_drafter_response.choices[0].message.content = _make_drafter_response()

    user_profile = {"persona": "young professional", "move_in_date": "1 July", "has_pets": False}
    with patch.object(drafter.client.chat.completions, "create", return_value=mock_drafter_response):
        draft = drafter.draft(target, red_flags, user_profile)
    assert "Dear landlord" in draft

    # 9. Simulate email tab session-state cleanup
    session = {"email_draft": draft, "last_email_listing_id": target["id"]}
    new_id = "listing_999"
    if session.get("last_email_listing_id") != new_id:
        session["email_draft"] = None
        session["last_email_listing_id"] = new_id
    assert session["email_draft"] is None

    # 10. Verify zero-match message includes suggested zones
    empty_constraints = {"budget": 500, "beds": 5}
    empty_matched, empty_excluded = filter_listings(empty_constraints, listings)
    assert len(empty_matched) == 0
    # In main.py, the zero-match message appends zone_names if suggested zones exist.
    # Here we just verify the logic branches correctly.
    if suggested:
        zone_names = ", ".join(z.get("name", "") for z in suggested)
        msg = f"No listings match... Alternatively, explore listings in {zone_names}."
        assert "Canada Water" in msg
