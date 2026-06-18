import json
from typing import Dict, Any, List


class TfLCommute:
    """
    Utility for estimating commute times and zones using static TfL data.
    MVP uses manual mapping; v2 could integrate TfL Unified API.
    """

    def __init__(self, station_zone_path: str = "data/station_zone_map.json"):
        with open(station_zone_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.stations = {k: v for k, v in data.items() if not k.startswith("_")}

    def get_station_zones(self, station_name: str) -> List[int]:
        """
        Return all zones associated with a station (some span 2-3 zones).
        """
        info = self.stations.get(station_name)
        if not info:
            return []
        zones = set()
        for mode, zone_list in info.items():
            zones.update(zone_list)
        return sorted(zones)

    def estimate_commute_time(
        self,
        home_station: str,
        work_station: str,
        mode: str = "tube",
    ) -> Dict[str, Any]:
        """
        Estimate door-to-door commute time.
        MVP uses simple heuristics; real implementation would call TfL Journey API.
        """
        # TODO: Implement heuristic or API call
        # Heuristic: base 10 min walk + 3 min per zone crossed + 5 min interchange buffer
        home_zones = self.get_station_zones(home_station)
        work_zones = self.get_station_zones(work_station)

        if not home_zones or not work_zones:
            return {
                "estimated_minutes": None,
                "confidence": "none",
                "reason": "Station not found in static database.",
            }

        zone_diff = abs(min(work_zones) - min(home_zones))
        estimated = 10 + (zone_diff * 3) + 5

        return {
            "estimated_minutes": estimated,
            "confidence": "low" if zone_diff > 4 else "medium",
            "zones_crossed": zone_diff,
            "note": "Heuristic estimate. Real times vary by line and peak hours.",
        }

    def suggest_nearby_stations(self, postcode_prefix: str) -> List[str]:
        """
        Suggest likely nearby stations based on postcode area.
        """
        # TODO: Build a postcode-to-station mapping
        mapping = {
            "SE14": ["New Cross Gate", "New Cross"],
            "SE13": ["Lewisham", "Hither Green"],
            "E1": ["Whitechapel", "Shoreditch High Street"],
            "E14": ["Canary Wharf"],
            "N1": ["Angel", "Highbury & Islington"],
        }
        return mapping.get(postcode_prefix, [])
