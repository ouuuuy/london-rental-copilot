"""Integration regression tests — validate cross-module consistency without API calls."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from unittest.mock import MagicMock, patch
from openai import APIError

from agents.requirement_parser import RequirementParser
from agents.redflag_detector import RedFlagDetector
from agents.comparison_generator import ComparisonGenerator
from agents.inquiry_drafter import InquiryDrafter
from utils import CostCalculator
from utils.filter_engine import filter_listings


# ---------------------------------------------------------------------------
# 1. Module importability & no circular deps
# ---------------------------------------------------------------------------

def test_all_modules_importable():
    """Every module must import cleanly."""
    assert RequirementParser is not None
    assert RedFlagDetector is not None
    assert ComparisonGenerator is not None
    assert InquiryDrafter is not None
    assert CostCalculator is not None
    assert filter_listings is not None


# ---------------------------------------------------------------------------
# 2. Data integrity: 30 listings, required fields present
# ---------------------------------------------------------------------------

def test_data_loads_30_listings():
    with open("data/sample_listings.json", "r", encoding="utf-8") as f:
        listings = json.load(f)
    assert len(listings) == 30, f"Expected 30 listings, got {len(listings)}"
    required = {"id", "title", "price_pcm", "location_postcode", "description"}
    for l in listings:
        missing = required - l.keys()
        assert not missing, f"Listing {l.get('id')} missing keys: {missing}"


def test_listing_price_range():
    with open("data/sample_listings.json", "r", encoding="utf-8") as f:
        listings = json.load(f)
    prices = [l["price_pcm"] for l in listings]
    assert min(prices) >= 800
    assert max(prices) <= 2800


# ---------------------------------------------------------------------------
# 3. Cross-module integration: Filter + CostCalculator
# ---------------------------------------------------------------------------

def test_filter_then_calculate_true_cost():
    """Filter outputs must be valid inputs for CostCalculator."""
    calc = CostCalculator()
    with open("data/sample_listings.json", "r", encoding="utf-8") as f:
        listings = json.load(f)

    constraints = {"budget": 1800, "beds": 2}
    matched, excluded = filter_listings(constraints, listings)

    assert len(matched) > 0, "Expected at least one match for 2-bed under £1,800"
    for m in matched:
        assert m["price_pcm"] <= 1800
        assert m["beds"] == 2
        cost = calc.calculate_true_cost(m, work_zone="1")
        assert cost["rent"] == m["price_pcm"]
        assert cost["true_cost"] >= cost["rent"]
        assert "council_tax_borough" in cost

    assert len(excluded) > 0, "Expected at least one excluded listing"
    for e in excluded:
        assert "reasons" in e
        assert len(e["reasons"]) > 0


def test_filter_no_constraints_returns_all():
    with open("data/sample_listings.json", "r", encoding="utf-8") as f:
        listings = json.load(f)
    matched, excluded = filter_listings({}, listings)
    assert len(matched) == 30
    assert len(excluded) == 0


# ---------------------------------------------------------------------------
# 4. Agent fallback interface consistency (what main.py expects)
# ---------------------------------------------------------------------------

def test_parser_fallback_shape():
    """Parser fallback must contain keys that main.py reads."""
    parser = RequirementParser(api_key="fake")
    with patch.object(
        parser.client.chat.completions, "create",
        side_effect=APIError("test", body=None, request=MagicMock()),
    ):
        result = parser.parse("test query")
    assert "suggested_zones" in result
    assert "constraint_warnings" in result
    assert "confidence" in result
    assert "budget" in result
    assert "beds" in result
    assert isinstance(result["suggested_zones"], list)
    assert isinstance(result["constraint_warnings"], list)


def test_detector_fallback_shape():
    detector = RedFlagDetector(api_key="fake")
    with patch.object(
        detector.client.chat.completions, "create",
        side_effect=APIError("test", body=None, request=MagicMock()),
    ):
        result = detector.analyze({"id": "l1", "title": "Test", "description": "desc"})
    assert "overall_risk" in result
    assert "flags" in result
    assert "missing_info" in result
    assert "notes" in result
    assert result["overall_risk"] == "unknown"


def test_comparison_fallback_shape():
    comparator = ComparisonGenerator(api_key="fake")
    with patch.object(
        comparator.client.chat.completions, "create",
        side_effect=APIError("test", body=None, request=MagicMock()),
    ):
        result = comparator.compare([])
    assert "winner_for_budget" in result
    assert "winner_for_commute" in result
    assert "caveats" in result
    assert "summary" in result
    assert "trade_offs" in result


def test_drafter_fallback_is_string():
    drafter = InquiryDrafter(api_key="fake")
    with patch.object(
        drafter.client.chat.completions, "create",
        side_effect=APIError("test", body=None, request=MagicMock()),
    ):
        result = drafter.draft({}, {}, {})
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# 5. Email tab session-state cleanup logic (simulated)
# ---------------------------------------------------------------------------

def test_email_listing_switch_clears_draft():
    """Simulate the session-state guard from main.py: switching listings clears draft."""
    session = {"email_draft": "Dear landlord...", "last_email_listing_id": "listing_001"}
    new_listing_id = "listing_002"

    if session.get("last_email_listing_id") != new_listing_id:
        session["email_draft"] = None
        session["last_email_listing_id"] = new_listing_id

    assert session["email_draft"] is None
    assert session["last_email_listing_id"] == "listing_002"


def test_email_same_listing_preserves_draft():
    session = {"email_draft": "Dear landlord...", "last_email_listing_id": "listing_001"}
    same_listing_id = "listing_001"

    if session.get("last_email_listing_id") != same_listing_id:
        session["email_draft"] = None
        session["last_email_listing_id"] = same_listing_id

    assert session["email_draft"] == "Dear landlord..."


# ---------------------------------------------------------------------------
# 6. RedFlagDetector context filtering (security/reliability)
# ---------------------------------------------------------------------------

def test_detector_excludes_structured_fields():
    """Verify _STRUCTURED_FIELDS_TO_EXCLUDE is applied so booleans don't leak to LLM context."""
    detector = RedFlagDetector(api_key="fake")
    listing = {
        "id": "l1",
        "title": "Test",
        "description": "desc",
        "bills_included": False,
        "pets_allowed": True,
        "has_garden": False,
        "listing_url": "http://example.com",
        "source": "test",
        "images_count": 5,
    }
    context = detector._prepare_context(listing)
    ctx = json.loads(context)
    for forbidden in detector._STRUCTURED_FIELDS_TO_EXCLUDE:
        assert forbidden not in ctx, f"{forbidden} should not appear in LLM context"


# ---------------------------------------------------------------------------
# 7. Security: no hardcoded secrets in source
# ---------------------------------------------------------------------------

def test_no_hardcoded_api_keys_in_agents():
    """Agents must read API key from env, never hardcode it."""
    import inspect
    for cls in [RequirementParser, RedFlagDetector, ComparisonGenerator, InquiryDrafter]:
        source = inspect.getsource(cls)
        assert "sk-" not in source, f"{cls.__name__} appears to contain a hardcoded key"


def test_env_example_is_template():
    """.env.example must not contain a real-looking key."""
    with open(".env.example", "r", encoding="utf-8") as f:
        content = f.read()
    assert "sk-your-key-here" in content or "sk-..." in content
    assert "sk-live" not in content
    assert "sk-proj" not in content
