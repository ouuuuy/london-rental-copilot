import json
import os

# Load station zone map once at module level
_STATION_ZONE_MAP_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "station_zone_map.json"
)
with open(_STATION_ZONE_MAP_PATH, "r", encoding="utf-8") as f:
    _STATION_ZONES = json.load(f)


def _postcode_to_zone(postcode: str) -> str:
    """Map a London postcode prefix to a TfL zone (simplified MVP mapping)."""
    prefix = postcode.split()[0] if " " in postcode else postcode
    mapping = {
        "W1D": "1",
        "NW1": "1",
        "N1": "1",
        "E1": "2",
        "E8": "2",
        "E2": "2",
        "SE13": "2",
        "SE14": "2",
        "SE16": "2",
        "SW9": "2",
        "SW11": "2",
        "SW15": "2",
        "SW17": "2",
        "SW19": "2",
        "SW6": "2",
        "E14": "2",
        "E15": "3",
        "NW10": "2",
        "SE10": "2",
        "SE15": "2",
        "W11": "2",
        "W12": "2",
        "N1C": "1",
    }
    return mapping.get(prefix, "2")


def _commute_target_to_zone(target: str) -> str:
    """Map a commute target (station or area name) to a TfL zone using station_zone_map.json."""
    if not target:
        return None
    # Try exact match first
    station_data = _STATION_ZONES.get(target)
    if station_data and isinstance(station_data, dict):
        all_zones = []
        for mode_zones in station_data.values():
            if isinstance(mode_zones, list):
                all_zones.extend(mode_zones)
        if all_zones:
            return str(min(all_zones))

    # Fallback: case-insensitive match
    target_lower = target.lower()
    for station_name, station_data in _STATION_ZONES.items():
        if isinstance(station_data, dict) and station_name.lower() == target_lower:
            all_zones = []
            for mode_zones in station_data.values():
                if isinstance(mode_zones, list):
                    all_zones.extend(mode_zones)
            if all_zones:
                return str(min(all_zones))

    return None


def filter_listings(constraints, all_listings):
    """Deterministic filter: matched + excluded with reasons."""
    matched = []
    excluded = []

    budget = constraints.get("budget")
    has_budget = isinstance(budget, int) and budget > 0
    target_beds = constraints.get("beds")
    needs_pets = constraints.get("pets_allowed") is True
    needs_garden = constraints.get("has_garden") is True

    commute_target = constraints.get("commute_target")
    commute_time_minutes = constraints.get("commute_time_minutes")
    target_commute_zone = _commute_target_to_zone(commute_target) if commute_target else None

    for listing in all_listings:
        reasons = []
        match_tags = []
        price = listing.get("price_pcm", 0)

        if has_budget and price > budget:
            reasons.append(f"£{price - budget} over budget")
        elif has_budget:
            match_tags.append("Budget")

        if target_beds is not None and listing.get("beds") != target_beds:
            reasons.append(f"Has {listing.get('beds')} beds, need {target_beds}")
        elif target_beds is not None:
            match_tags.append("Beds")

        if needs_pets and not listing.get("pets_allowed"):
            reasons.append("No pets allowed")
        elif needs_pets:
            match_tags.append("Pets")

        if needs_garden and not listing.get("has_garden"):
            reasons.append("No garden")
        elif needs_garden:
            match_tags.append("Garden")

        # Commute / Zone filter
        if target_commute_zone is not None:
            home_zone = _postcode_to_zone(listing.get("location_postcode", ""))
            try:
                zone_diff = abs(int(home_zone) - int(target_commute_zone))
            except (ValueError, TypeError):
                zone_diff = 0

            # Rough heuristic: each zone difference ≈ 10–15 min by tube
            if commute_time_minutes is not None and isinstance(commute_time_minutes, (int, float)):
                max_allowed_diff = max(1, int(commute_time_minutes) // 15)
            else:
                max_allowed_diff = 2  # sensible default fallback

            if zone_diff > max_allowed_diff:
                reasons.append(
                    f"Commute: Zone {home_zone} may exceed {commute_time_minutes or 'acceptable'} min to {commute_target}"
                )
            else:
                match_tags.append("Commute")

        if reasons:
            excluded.append({"id": listing["id"], "title": listing["title"], "reasons": reasons})
        else:
            listing_copy = dict(listing)
            listing_copy["match_tags"] = match_tags
            matched.append(listing_copy)
    return matched, excluded
