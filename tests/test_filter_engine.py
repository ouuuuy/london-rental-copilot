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
