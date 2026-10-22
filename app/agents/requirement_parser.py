import os
import json
from typing import Dict, List, Any
from openai import OpenAI


class RequirementParser:
    """
    Agent 1: Parses natural-language rental requirements into structured constraints.
    Also suggests additional zones and flags mutually exclusive constraints.
    """

    SYSTEM_PROMPT = """You are a structured data parser for a London rental search assistant.
Your job is to convert a user's free-text rental requirements into a strict JSON object.

OUTPUT FORMAT (JSON):
{
  "budget": integer or null,
  "beds": integer or null (studio=0),
  "pets_allowed": boolean or null,
  "has_garden": boolean or null,
  "commute_target": string or null (station or area name),
  "commute_time_minutes": integer or null,
  "lifestyle_tags": ["quiet", "nightlife", "family_friendly", "trendy", "green_space", ...],
  "suggested_zones": [],
  "constraint_warnings": ["List any impossible or conflicting constraints"],
  "confidence": "high|medium|low"
}

RULES:
1. Extract budget from phrases like "under £1800", "max 2000", "around 1500". If not mentioned, null.
2. Extract bedroom count: "studio"=0, "1 bed"=1, "2 bed"=2, "3 bed"=3. If not mentioned, null.
3. Extract pets: true only if user explicitly mentions pets/pet-friendly. false only if user says "no pets". Otherwise null.
4. Extract garden: true only if user mentions garden/terrace/balcony/outdoor space. Otherwise null.
5. Extract commute target: station name or area (e.g., "Canary Wharf", "City", "Shoreditch"). Otherwise null.
6. Extract commute time: number before "min" or "minutes". Otherwise null.
7. Extract lifestyle tags from adjectives describing vibe: "quiet", "lively", "trendy", "family-friendly", "green", "posh", etc.
8. suggested_zones: recommend 2-3 additional London zones or boroughs the user may not have considered.
   Base recommendations on the commute_target, lifestyle_tags, and budget.
   Each item must be an object: {"name": "Borough or Zone name", "rationale": "One sentence why it fits"}.
   If no useful suggestion can be made, return an empty array.
9. Flag impossible constraints (e.g., "Zone 1 studio under £800" → "Statistically unlikely in London").
10. If information is missing, use null. Do not guess or hallucinate.
11. confidence = "high" if budget+beds+commute all present, "medium" if 2 present, "low" if 1 or fewer.
"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def parse(self, query: str) -> Dict[str, Any]:
        """
        Convert a natural language query into structured rental constraints.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=0.2,
            )
            result = json.loads(response.choices[0].message.content)
            # Guard against malformed LLM output
            if not isinstance(result.get("suggested_zones"), list):
                result["suggested_zones"] = []
            if not isinstance(result.get("constraint_warnings"), list):
                result["constraint_warnings"] = []
            return result
        except Exception as e:
            # Graceful fallback: return low-confidence empty result with error info
            return {
                "budget": None,
                "beds": None,
                "pets_allowed": None,
                "has_garden": None,
                "commute_target": None,
                "commute_time_minutes": None,
                "lifestyle_tags": [],
                "suggested_zones": [],
                "constraint_warnings": [f"Parser error: {str(e)}"],
                "confidence": "low",
            }
