"""Unit tests for CostCalculator — uses static JSON data, no API calls."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from utils import CostCalculator


def test_council_tax_with_known_band():
    calc = CostCalculator()
    result = calc.estimate_council_tax("E1 6AN", band="D")
    assert result["band"] == "D"
    assert result["borough"] == "Tower Hamlets"
    assert result["disclaimer"] is None
    assert result["monthly"] > 0


def test_council_tax_estimate_without_band():
    calc = CostCalculator()
    result = calc.estimate_council_tax("E1 6AN")
    assert result["band"] is None
    assert "midpoint" in result["disclaimer"].lower()
    assert result["monthly"] > 0


def test_commute_cost_same_zone():
    calc = CostCalculator()
    cost = calc.estimate_commute_cost("2", work_zone="2")
    assert cost > 0


def test_commute_cost_cross_zone():
    calc = CostCalculator()
    cost = calc.estimate_commute_cost("3", work_zone="1")
    assert cost > 0


def test_utilities_by_beds():
    calc = CostCalculator()
    assert calc.estimate_utilities(0) == 100
    assert calc.estimate_utilities(1) == 120
    assert calc.estimate_utilities(2) == 160
    assert calc.estimate_utilities(3) == 200


def test_true_cost_bills_included():
    calc = CostCalculator()
    listing = {
        "id": "l1",
        "price_pcm": 1500,
        "location_postcode": "E1 6AN",
        "bills_included": True,
        "beds": 1,
    }
    cost = calc.calculate_true_cost(listing, work_zone="2")
    assert cost["rent"] == 1500
    assert cost["utilities"] == 0
    assert cost["true_cost"] == cost["rent"] + cost["council_tax"] + cost["commute"]


def test_true_cost_bills_excluded():
    calc = CostCalculator()
    listing = {
        "id": "l1",
        "price_pcm": 1500,
        "location_postcode": "E1 6AN",
        "bills_included": False,
        "beds": 1,
    }
    cost = calc.calculate_true_cost(listing, work_zone="2")
    assert cost["rent"] == 1500
    assert cost["utilities"] == 120
    assert cost["true_cost"] == cost["rent"] + cost["council_tax"] + cost["commute"] + cost["utilities"]


def test_postcode_to_borough_mapping():
    calc = CostCalculator()
    assert calc._postcode_to_borough("E1 6AN") == "Tower Hamlets"
    assert calc._postcode_to_borough("SW1A 1AA") == "Westminster"
    assert calc._postcode_to_borough("N1 1AA") == "Islington"


def test_postcode_to_zone_mapping():
    calc = CostCalculator()
    assert calc._postcode_to_zone("E1 6AN") == "2"
    assert calc._postcode_to_zone("W1D 1AA") == "1"
    assert calc._postcode_to_zone("N1 1AA") == "1"
