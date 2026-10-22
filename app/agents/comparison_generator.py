import os
import json
from typing import Dict, List, Any
from openai import OpenAI, APIError, APITimeoutError


class ComparisonGenerator:
    """
    Agent 3: Generates natural-language comparison summaries and recommendations
    across shortlisted listings, based on pre-computed true-cost data.
    """

    SYSTEM_PROMPT = """You are a London rental advisor. You help tenants compare shortlisted properties.
You will be given structured data about 2-3 listings, including pre-calculated true monthly costs.

Your job is to generate a helpful, balanced natural-language comparison.
Do not hallucinate numbers — use only the provided data.
Highlight trade-offs (e.g., cheaper rent but higher commute cost, or better amenities but no garden).

OUTPUT FORMAT (JSON):
{
  "summary": "String containing 2-3 concise bullet points (max 15 words each), separated by newlines. Use markdown bullet format. Example: '- Budget-friendly: studio in Central London offers significant monthly savings.\n- More space and garden: 2-bed flat in Hackney is worth the extra cost.'",
  "trade_offs": [
    {"dimension": "cost|commute|space|amenities", "comparison": "One-sentence comparison"}
  ],
  "winner_for_budget": "listing_id or 'tie'",
  "winner_for_commute": "listing_id or 'tie'",
  "caveats": ["Things the tenant should verify before deciding"]
}

TONE: Friendly, practical, cautious, concise. Never say "rent this one" — always frame as "consider X if you prioritize Y". Keep every field brief.
"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def compare(self, listings_with_costs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        listings_with_costs: List of dicts with 'listing' and 'cost' keys.
        """
        try:
            # Build concise context to keep token count low
            context_items = []
            for r in listings_with_costs:
                listing = r["listing"]
                cost = r["cost"]
                context_items.append({
                    "id": listing["id"],
                    "title": listing["title"],
                    "location": listing["location_postcode"],
                    "beds": listing.get("beds"),
                    "bills_included": listing.get("bills_included"),
                    "has_garden": listing.get("has_garden"),
                    "pets_allowed": listing.get("pets_allowed"),
                    "rent": cost["rent"],
                    "council_tax": cost["council_tax"],
                    "commute": cost["commute"],
                    "utilities": cost["utilities"],
                    "true_cost": cost["true_cost"],
                })
            context = json.dumps(context_items, ensure_ascii=False)

            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Compare these listings:\n{context}"},
                ],
                temperature=0.3,
            )
            return json.loads(response.choices[0].message.content)

        except (APIError, APITimeoutError):
            return {
                "summary": "Comparison summary unavailable. Please review the cost breakdown above.",
                "trade_offs": [],
                "winner_for_budget": "tie",
                "winner_for_commute": "tie",
                "caveats": ["AI service temporarily unavailable. Please try again in a moment."],
            }
        except json.JSONDecodeError:
            return {
                "summary": "Comparison summary unavailable. Please review the cost breakdown above.",
                "trade_offs": [],
                "winner_for_budget": "tie",
                "winner_for_commute": "tie",
                "caveats": ["Received an unexpected response from the AI. Please try again."],
            }
        except Exception:
            return {
                "summary": "Comparison summary unavailable. Please review the cost breakdown above.",
                "trade_offs": [],
                "winner_for_budget": "tie",
                "winner_for_commute": "tie",
                "caveats": ["An unexpected error occurred. Please try again."],
            }
