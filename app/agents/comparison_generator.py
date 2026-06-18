import os
import json
from typing import Dict, List, Any
from openai import OpenAI


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
  "summary": "2-3 sentence overall recommendation",
  "trade_offs": [
    {"dimension": "cost|commute|space|amenities", "comparison": "Natural language comparison"}
  ],
  "winner_for_budget": "listing_id or 'tie'",
  "winner_for_commute": "listing_id or 'tie'",
  "caveats": ["Things the tenant should verify before deciding"]
}

TONE: Friendly, practical, cautious. Never say "rent this one" — always frame as "consider X if you prioritize Y".
"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def compare(self, listings_with_costs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
 listings_with_costs: List of listing dicts enriched with 'true_cost' and cost breakdown.
        """
        # TODO: Implement OpenAI API call with JSON mode
        # context = json.dumps(listings_with_costs, ensure_ascii=False)
        # response = self.client.chat.completions.create(
        #     model=self.model,
        #     response_format={"type": "json_object"},
        #     messages=[
        #         {"role": "system", "content": self.SYSTEM_PROMPT},
        #         {"role": "user", "content": f"Compare these listings:\n{context}"},
        #     ],
        #     temperature=0.3,
        # )
        # return json.loads(response.choices[0].message.content)

        return {
            "summary": "Comparison generator not yet implemented.",
            "trade_offs": [],
            "winner_for_budget": "tie",
            "winner_for_commute": "tie",
            "caveats": ["Implement me!"],
        }
