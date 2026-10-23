"""Unit tests for filter_engine — no external API calls."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from utils.filter_engine import filter_listings


def test_filter_by_budget():
    listings = [
        {"id": "l1", "title": "Cheap", "price_pcm": 1000, "beds": 1, "pets_allowed": False, "has_garden": False},
        {"id": "l2", "title": "Expensive", "price_pcm": 2000, "beds": 1, "pets_allowed": False, "has_garden": False},
    ]
    matched, excluded = filter_listings({"budget": 1500}, listings)
    assert len(matched) == 1 and matched[0]["id"] == "l1"
    assert len(excluded) == 1 and "over budget" in excluded[0]["reasons"][0]


def test_filter_by_beds():
    listings = [
        {"id": "l1", "title": "Studio", "price_pcm": 1000, "beds": 0, "pets_allowed": False, "has_garden": False},
        {"id": "l2", "title": "1-bed", "price_pcm": 1200, "beds": 1, "pets_allowed": False, "has_garden": False},
    ]
    matched, excluded = filter_listings({"beds": 1}, listings)
    assert len(matched) == 1 and matched[0]["id"] == "l2"


def test_filter_by_pets():
    listings = [
        {"id": "l1", "title": "No pets", "price_pcm": 1000, "beds": 1, "pets_allowed": False, "has_garden": False},
        {"id": "l2", "title": "Pet friendly", "price_pcm": 1200, "beds": 1, "pets_allowed": True, "has_garden": False},
    ]
    matched, excluded = filter_listings({"pets_allowed": True}, listings)
    assert len(matched) == 1 and matched[0]["id"] == "l2"


def test_filter_by_garden():
    listings = [
        {"id": "l1", "title": "No garden", "price_pcm": 1000, "beds": 1, "pets_allowed": False, "has_garden": False},
        {"id": "l2", "title": "With garden", "price_pcm": 1200, "beds": 1, "pets_allowed": False, "has_garden": True},
    ]
    matched, excluded = filter_listings({"has_garden": True}, listings)
    assert len(matched) == 1 and matched[0]["id"] == "l2"


def test_filter_combined_no_match():
    listings = [
        {"id": "l1", "title": "A", "price_pcm": 900, "beds": 0, "pets_allowed": False, "has_garden": False},
        {"id": "l2", "title": "B", "price_pcm": 1500, "beds": 1, "pets_allowed": True, "has_garden": True},
        {"id": "l3", "title": "C", "price_pcm": 1200, "beds": 1, "pets_allowed": False, "has_garden": False},
    ]
    constraints = {"budget": 1300, "beds": 1, "pets_allowed": True, "has_garden": True}
    matched, excluded = filter_listings(constraints, listings)
    assert len(matched) == 0
    assert len(excluded) == 3


def test_filter_no_constraints():
    listings = [
        {"id": "l1", "title": "A", "price_pcm": 1000, "beds": 1, "pets_allowed": False, "has_garden": False},
    ]
    matched, excluded = filter_listings({}, listings)
    assert len(matched) == 1
    assert matched[0]["match_tags"] == []
    assert len(excluded) == 0


def test_filter_match_tags_populated():
    listings = [
        {"id": "l1", "title": "A", "price_pcm": 1000, "beds": 1, "pets_allowed": True, "has_garden": True},
    ]
    constraints = {"budget": 1500, "beds": 1, "pets_allowed": True, "has_garden": True}
    matched, excluded = filter_listings(constraints, listings)
    assert set(matched[0]["match_tags"]) == {"Budget", "Beds", "Pets", "Garden"}


# ---------------------------------------------------------------------------
# Commute / Zone filtering tests
# ---------------------------------------------------------------------------

def test_filter_by_commute_zone_match_same_zone():
    listings = [
        {"id": "l1", "title": "Canary Wharf flat", "price_pcm": 1500, "beds": 1, "pets_allowed": False, "has_garden": False, "location_postcode": "E14 5AB"},
    ]
    constraints = {"commute_target": "Canary Wharf", "commute_time_minutes": 30}
    matched, excluded = filter_listings(constraints, listings)
    assert len(matched) == 1
    assert "Commute" in matched[0]["match_tags"]


def test_filter_by_commute_zone_exclude_too_far():
    listings = [
        {"id": "l1", "title": "Stratford flat", "price_pcm": 1200, "beds": 1, "pets_allowed": False, "has_garden": False, "location_postcode": "E15 1AA"},
    ]
    # Oxford Circus is zone 1, Stratford (E15) is zone 3, diff=2
    # commute_time_minutes=15 → max_allowed = 1
    constraints = {"commute_target": "Oxford Circus", "commute_time_minutes": 15}
    matched, excluded = filter_listings(constraints, listings)
    assert len(matched) == 0
    assert len(excluded) == 1
    assert "Commute" in excluded[0]["reasons"][0]


def test_filter_by_commute_no_time_limit():
    listings = [
        {"id": "l1", "title": "Stratford flat", "price_pcm": 1200, "beds": 1, "pets_allowed": False, "has_garden": False, "location_postcode": "E15 1AA"},
    ]
    # No commute_time_minutes → default max_allowed_diff = 2
    # Oxford Circus (z1) vs E15 (z3), diff=2 → match
    constraints = {"commute_target": "Oxford Circus"}
    matched, excluded = filter_listings(constraints, listings)
    assert len(matched) == 1
    assert "Commute" in matched[0]["match_tags"]


def test_filter_by_commute_unknown_target():
    listings = [
        {"id": "l1", "title": "Stratford flat", "price_pcm": 1200, "beds": 1, "pets_allowed": False, "has_garden": False, "location_postcode": "E15 1AA"},
    ]
    # Unknown commute target → no commute filter applied
    constraints = {"commute_target": "Mars Station"}
    matched, excluded = filter_listings(constraints, listings)
    assert len(matched) == 1
    assert "Commute" not in matched[0]["match_tags"]


def test_filter_by_commute_target_none():
    listings = [
        {"id": "l1", "title": "Stratford flat", "price_pcm": 1200, "beds": 1, "pets_allowed": False, "has_garden": False, "location_postcode": "E15 1AA"},
    ]
    constraints = {}
    matched, excluded = filter_listings(constraints, listings)
    assert len(matched) == 1
    assert "Commute" not in matched[0]["match_tags"]


def test_filter_commute_combined_with_budget():
    listings = [
        {"id": "l1", "title": "Cheap far flat", "price_pcm": 900, "beds": 1, "pets_allowed": False, "has_garden": False, "location_postcode": "E15 1AA"},
        {"id": "l2", "title": "Expensive close flat", "price_pcm": 2000, "beds": 1, "pets_allowed": False, "has_garden": False, "location_postcode": "W1D 1AA"},
    ]
    # Oxford Circus (z1) vs E15 (z3) diff=2, max_allowed=1 (time=15) → exclude l1
    # Oxford Circus (z1) vs W1D (z1) diff=0 → include l2
    constraints = {"commute_target": "Oxford Circus", "commute_time_minutes": 15, "budget": 2500}
    matched, excluded = filter_listings(constraints, listings)
    assert len(matched) == 1 and matched[0]["id"] == "l2"
    assert len(excluded) == 1 and excluded[0]["id"] == "l1"
    assert "Commute" in excluded[0]["reasons"][0]
