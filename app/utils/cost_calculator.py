import json
from typing import Dict, Any


class CostCalculator:
    """
    Deterministic utility to calculate the true monthly cost of a rental property.
    Uses static JSON data for council tax, commute, and utility estimates.
    """

    BAND_RATIOS = {
        "A": 6 / 9,
        "B": 7 / 9,
        "C": 8 / 9,
        "D": 1.0,
        "E": 11 / 9,
        "F": 13 / 9,
        "G": 15 / 9,
        "H": 18 / 9,
    }

    def __init__(
        self,
        council_tax_path: str = "data/borough_council_tax.json",
        travelcard_path: str = "data/travelcard_costs.json",
    ):
        with open(council_tax_path, "r", encoding="utf-8") as f:
            self.council_tax = json.load(f)
        with open(travelcard_path, "r", encoding="utf-8") as f:
            self.travelcards = json.load(f)["zones"]

    def estimate_council_tax(
        self, postcode: str, band: str = None, beds: int = None
    ) -> Dict[str, Any]:
        """
        Map a London postcode to an estimated monthly council tax.
        Uses borough prefix heuristics (e.g., SE14 -> Lewisham).

        Priority:
        1. If band is specified → exact monthly cost from the band ratio.
        2. If band is missing but beds is known → heuristic band based on bedroom count
           (studio→B, 1-bed→C, 2-bed+→D) as per PRD §4.3.
        3. Ultimate fallback → Band C-D midpoint.
        """
        borough = self._postcode_to_borough(postcode)
        band_d_monthly = self.council_tax.get(borough, 160)

        if band and band.upper() in self.BAND_RATIOS:
            monthly = round(band_d_monthly * self.BAND_RATIOS[band.upper()])
            return {
                "monthly": monthly,
                "band": band.upper(),
                "borough": borough,
                "disclaimer": None,
            }

        # Heuristic inference based on bedroom count (PRD §4.3)
        if beds is not None:
            if beds == 0:          # studio
                heuristic_band = "B"
            elif beds == 1:
                heuristic_band = "C"
            else:                  # 2-bed+
                heuristic_band = "D"
            monthly = round(band_d_monthly * self.BAND_RATIOS[heuristic_band])
            return {
                "monthly": monthly,
                "band": heuristic_band,
                "borough": borough,
                "disclaimer": (
                    f"Estimated as Band {heuristic_band} based on {beds}-bed heuristic. "
                    "Actual band (A-H) set by VOA. Verify with landlord."
                ),
            }

        # Ultimate fallback: Band C-D midpoint
        monthly = round(band_d_monthly * 0.944)
        return {
            "monthly": monthly,
            "band": None,
            "borough": borough,
            "disclaimer": "Estimated as Band C-D midpoint. Actual band (A-H) set by VOA. Verify with landlord.",
        }

    def estimate_commute_cost(self, home_zone: str, work_zone: str = "1") -> float:
        """
        Estimate monthly commute cost between two TfL zones.
        """
        min_zone = min(int(home_zone), int(work_zone))
        max_zone = max(int(home_zone), int(work_zone))

        if min_zone == max_zone:
            key = str(min_zone)
        else:
            key = f"{min_zone}-{max_zone}"

        return self.travelcards.get(key, {}).get("monthly", 180)

    def estimate_utilities(self, beds: int) -> float:
        """
        Rough utility estimate based on bedroom count.
        """
        if beds == 0:
            return 100
        elif beds == 1:
            return 120
        elif beds == 2:
            return 160
        else:
            return 200

    def calculate_true_cost(
        self,
        listing: Dict[str, Any],
        work_zone: str = "1",
    ) -> Dict[str, Any]:
        """
        Compute full monthly outlay for a listing.
        home_zone is auto-derived from the listing's postcode.
        work_zone is passed in from the UI (user's commute target).
        """
        rent = listing.get("price_pcm", 0)

        # Council Tax
        band = listing.get("council_tax_band")
        beds = listing.get("beds")
        council_tax_result = self.estimate_council_tax(
            listing.get("location_postcode", ""), band, beds
        )
        council_tax = council_tax_result["monthly"]
        council_tax_disclaimer = council_tax_result.get("disclaimer")

        # Commute (always calculated, independent of bills_included)
        home_zone = self._postcode_to_zone(listing.get("location_postcode", ""))
        commute = self.estimate_commute_cost(home_zone, work_zone)

        # Utilities (only if bills are not included)
        utilities = (
            0 if listing.get("bills_included") else self.estimate_utilities(listing.get("beds", 1))
        )

        true_cost = rent + council_tax + commute + utilities

        return {
            "rent": rent,
            "council_tax": council_tax,
            "council_tax_band": council_tax_result["band"],
            "council_tax_borough": council_tax_result["borough"],
            "council_tax_disclaimer": council_tax_disclaimer,
            "commute": commute,
            "utilities": utilities,
            "true_cost": true_cost,
            "notes": "Estimates based on 2026 static data. Actual costs vary.",
        }

    @staticmethod
    def _postcode_to_borough(postcode: str) -> str:
        """
        Simplified mapping for MVP. In production, use a full postcode database.
        """
        prefix = postcode.split()[0] if " " in postcode else postcode
        mapping = {
            "SE14": "Lewisham",
            "SE13": "Lewisham",
            "SE4": "Lewisham",
            "E1": "Tower Hamlets",
            "E2": "Hackney",
            "E8": "Hackney",
            "N1": "Islington",
            "W1": "Westminster",
            "W1D": "Westminster",
            "SW1": "Westminster",
            "SW11": "Wandsworth",
            "SW9": "Lambeth",
            "SE16": "Southwark",
            "E15": "Newham",
            "NW1": "Camden",
            "NW10": "Brent",
        }
        return mapping.get(prefix, "Westminster")

    @staticmethod
    def _postcode_to_zone(postcode: str) -> str:
        """
        Simplified postcode prefix to TfL zone mapping for MVP.
        For postcodes spanning multiple zones, returns the lowest zone
        (most optimistic commute cost estimate).
        """
        prefix = postcode.split()[0] if " " in postcode else postcode
        mapping = {
            "W1D": "1",
            "NW1": "1",
            "E1": "2",
            "E8": "2",
            "N1": "1",
            "SE13": "2",
            "SE14": "2",
            "SE16": "2",
            "SW9": "2",
            "SW11": "2",
            "E15": "3",
            "NW10": "2",
        }
        return mapping.get(prefix, "2")
