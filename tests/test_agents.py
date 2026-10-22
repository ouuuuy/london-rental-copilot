"""Unit tests for Agent exception handling — uses mocks, no real API calls."""
import json
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from openai import APIError, APITimeoutError
from agents.requirement_parser import RequirementParser
from agents.redflag_detector import RedFlagDetector
from agents.comparison_generator import ComparisonGenerator
from agents.inquiry_drafter import InquiryDrafter


# ---------------------------------------------------------------------------
# RequirementParser
# ---------------------------------------------------------------------------

def test_parser_api_error():
    parser = RequirementParser(api_key="fake-key")
    with patch.object(
        parser.client.chat.completions, "create",
        side_effect=APIError("test", body=None, request=MagicMock()),
    ):
        result = parser.parse("2 bed flat in London")
        assert result["confidence"] == "low"
        assert "temporarily unavailable" in result["constraint_warnings"][0].lower()


def test_parser_unexpected_error():
    parser = RequirementParser(api_key="fake-key")
    with patch.object(
        parser.client.chat.completions, "create", side_effect=Exception("something else"),
    ):
        result = parser.parse("2 bed flat in London")
        assert result["confidence"] == "low"
        assert "unexpected error" in result["constraint_warnings"][0].lower()


def test_parser_json_decode_error():
    parser = RequirementParser(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not valid json"
    with patch.object(
        parser.client.chat.completions, "create", return_value=mock_response
    ):
        result = parser.parse("2 bed flat in London")
        assert result["confidence"] == "low"
        assert "unexpected response" in result["constraint_warnings"][0].lower()


def test_parser_success():
    parser = RequirementParser(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "budget": 1800,
        "beds": 2,
        "pets_allowed": None,
        "has_garden": None,
        "commute_target": "Canary Wharf",
        "commute_time_minutes": 30,
        "lifestyle_tags": ["quiet"],
        "suggested_zones": [{"name": "Canada Water", "rationale": "cheaper"}],
        "constraint_warnings": [],
        "confidence": "high",
    })
    with patch.object(
        parser.client.chat.completions, "create", return_value=mock_response
    ):
        result = parser.parse("2 bed flat under 1800 near Canary Wharf")
        assert result["budget"] == 1800
        assert result["beds"] == 2
        assert len(result["suggested_zones"]) == 1


def test_parser_malformed_zones_guard():
    """If LLM returns a string instead of list for suggested_zones, coerce to []."""
    parser = RequirementParser(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "budget": 1000,
        "beds": 1,
        "suggested_zones": "Canada Water",
        "constraint_warnings": "too strict",
        "confidence": "medium",
    })
    with patch.object(
        parser.client.chat.completions, "create", return_value=mock_response
    ):
        result = parser.parse("cheap flat")
        assert result["suggested_zones"] == []
        assert result["constraint_warnings"] == []


# ---------------------------------------------------------------------------
# RedFlagDetector
# ---------------------------------------------------------------------------

def test_detector_api_error():
    detector = RedFlagDetector(api_key="fake-key")
    with patch.object(
        detector.client.chat.completions, "create",
        side_effect=APIError("test", body=None, request=MagicMock()),
    ):
        result = detector.analyze({"id": "l1", "title": "Test", "description": "desc"})
        assert result["overall_risk"] == "unknown"
        assert "temporarily unavailable" in result["missing_info"][0].lower()


def test_detector_unexpected_error():
    detector = RedFlagDetector(api_key="fake-key")
    with patch.object(
        detector.client.chat.completions, "create", side_effect=Exception("something else"),
    ):
        result = detector.analyze({"id": "l1", "title": "Test", "description": "desc"})
        assert result["overall_risk"] == "unknown"
        assert "unexpected error" in result["missing_info"][0].lower()


def test_detector_json_decode_error():
    detector = RedFlagDetector(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not valid json"
    with patch.object(
        detector.client.chat.completions, "create", return_value=mock_response
    ):
        result = detector.analyze({"id": "l1", "title": "Test", "description": "desc"})
        assert result["overall_risk"] == "unknown"
        assert "unexpected response" in result["missing_info"][0].lower()


def test_detector_success():
    detector = RedFlagDetector(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "overall_risk": "low",
        "flags": [],
        "missing_info": [],
        "notes": "Clean listing.",
    })
    with patch.object(
        detector.client.chat.completions, "create", return_value=mock_response
    ):
        result = detector.analyze({"id": "l1", "title": "Test", "description": "desc"})
        assert result["overall_risk"] == "low"


# ---------------------------------------------------------------------------
# ComparisonGenerator
# ---------------------------------------------------------------------------

def test_comparison_api_error():
    comparator = ComparisonGenerator(api_key="fake-key")
    with patch.object(
        comparator.client.chat.completions, "create",
        side_effect=APIError("test", body=None, request=MagicMock()),
    ):
        result = comparator.compare([])
        assert result["winner_for_budget"] == "tie"
        assert "temporarily unavailable" in result["caveats"][0].lower()


def test_comparison_unexpected_error():
    comparator = ComparisonGenerator(api_key="fake-key")
    with patch.object(
        comparator.client.chat.completions, "create", side_effect=Exception("something else"),
    ):
        result = comparator.compare([])
        assert result["winner_for_budget"] == "tie"
        assert "unexpected error" in result["caveats"][0].lower()


def test_comparison_json_decode_error():
    comparator = ComparisonGenerator(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not valid json"
    with patch.object(
        comparator.client.chat.completions, "create", return_value=mock_response
    ):
        result = comparator.compare([])
        assert result["winner_for_budget"] == "tie"
        assert "unexpected response" in result["caveats"][0].lower()


def test_comparison_success():
    comparator = ComparisonGenerator(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "summary": "- Good option",
        "trade_offs": [],
        "winner_for_budget": "l1",
        "winner_for_commute": "tie",
        "caveats": [],
    })
    with patch.object(
        comparator.client.chat.completions, "create", return_value=mock_response
    ):
        result = comparator.compare([{
            "listing": {
                "id": "l1",
                "title": "Test Flat",
                "location_postcode": "E1 6AN",
                "beds": 1,
                "bills_included": False,
                "has_garden": False,
                "pets_allowed": False,
            },
            "cost": {"rent": 1000, "council_tax": 100, "commute": 50, "utilities": 0, "true_cost": 1150},
        }])
        assert result["winner_for_budget"] == "l1"


# ---------------------------------------------------------------------------
# InquiryDrafter
# ---------------------------------------------------------------------------

def test_drafter_api_error():
    drafter = InquiryDrafter(api_key="fake-key")
    with patch.object(
        drafter.client.chat.completions, "create",
        side_effect=APIError("test", body=None, request=MagicMock()),
    ):
        result = drafter.draft({}, {}, {})
        assert "temporarily unavailable" in result.lower()


def test_drafter_unexpected_error():
    drafter = InquiryDrafter(api_key="fake-key")
    with patch.object(
        drafter.client.chat.completions, "create", side_effect=Exception("something else"),
    ):
        result = drafter.draft({}, {}, {})
        assert "unexpected error" in result.lower()


def test_drafter_success():
    drafter = InquiryDrafter(api_key="fake-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Subject: Enquiry\n\nDear landlord..."
    with patch.object(
        drafter.client.chat.completions, "create", return_value=mock_response
    ):
        result = drafter.draft(
            {"title": "Test", "price_pcm": 1000, "location_postcode": "E1", "beds": 1},
            {"flags": []},
            {"persona": "young professional", "move_in_date": "July", "has_pets": False},
        )
        assert "Dear landlord" in result
