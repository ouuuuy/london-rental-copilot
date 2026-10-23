import os
import json
from typing import Dict, List, Any
from openai import OpenAI, APIError, APITimeoutError


class RedFlagDetector:
    """
    Agent 2: Analyzes a property listing for scam patterns, hidden costs,
    description mismatches, and urgency pressure tactics.
    """

    SYSTEM_PROMPT = """You are a consumer protection analyst specializing in UK rental listings.
Your job is to analyze a property listing and return a structured risk assessment.

Be CONSERVATIVE. It is better to miss a subtle red flag than to falsely accuse a legitimate landlord.
Every flag must cite specific text from the listing as evidence.

OUTPUT FORMAT (JSON):
{
  "overall_risk": "low|medium|high",
  "flags": [
    {
      "category": "SCAM_RISK|HIDDEN_COST_RISK|DESCRIPTION_MISMATCH|LANDLORD_PRESSURE",
      "severity": "low|medium|high",
      "evidence": "Exact quote from listing",
      "explanation": "Plain-English explanation for a renter",
      "recommendation": "What the user should do"
    }
  ],
  "missing_info": ["Important details not mentioned"],
  "notes": "Any additional context"
}

CATEGORY DEFINITIONS:
1. SCAM_RISK (High severity)
   - Triggers: Pre-viewing deposit demands, "landlord abroad", Western Union/money transfer requests, prices 30%+ below market rate for area.
   - Never flag "holding deposit" after viewing as scam — that is normal UK practice.

2. HIDDEN_COST_RISK (Medium severity)
   - Triggers: "rent excludes bills" / "bills not included" / "bills excluded" WITHOUT specifying which (gas, electricity, water, council tax); vague service charges; "admin fees" mentioned; council tax not mentioned when rent excludes bills.
   - Do NOT flag if listing explicitly states council tax band, says "all bills included", or lists specific excluded bills (e.g., "water included, gas and electricity excluded").
   - Do NOT flag if the listing JSON includes a council_tax_band field and there are no other unspecified costs (admin fees, service charges, ground rent). The presence of a known council tax band means the renter can calculate this cost.
   - Example (flag): "Rent excludes bills" with NO council tax band mentioned AND no specific bill breakdown → HIDDEN_COST_RISK because renter cannot estimate total monthly outlay.
   - Example (do NOT flag): "Rent excludes bills" but council_tax_band is provided in the listing data, and there are no admin fees or service charges mentioned → do NOT flag.
   - Example (do NOT flag): "Water rates included" + other bills not mentioned → normal partial disclosure, do not flag.

3. DESCRIPTION_MISMATCH (Low severity)
   - Triggers: Superlatives ("spacious", "luxury", "high-spec") unsupported by details or photos, "recently renovated" with no kitchen/bathroom mention.
   - Example (flag): "Incredibly spacious one bedroom flat... Approximately 300 sq ft" → DESCRIPTION_MISMATCH because "incredibly spacious" is contradicted by the objective size data (300 sq ft is compact for a 1-bed).
   - Do NOT flag standard marketing language like "lovely", "bright", "well-presented".

4. LANDLORD_PRESSURE (Medium severity)
   - Triggers: ALL CAPS urgency, "MUST view today", "FIRST COME FIRST SERVE", "20 enquiries already", "available immediately must move in this weekend".
   - Do NOT flag normal availability phrases like "Available from 1st June" or "Viewing highly recommended".
   - Do NOT flag normal marketing phrases like "many people interested", "popular property", or "high demand".

RULES:
- Only flag if there is textual evidence in the listing.
- Use "low" severity for minor omissions; "high" for active scam indicators.
- If no flags are found, return an empty flags array and overall_risk "low".
- Never make accusations without evidence.
- For clean listings, missing_info can still note useful omissions without raising a flag.
"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    # Fields that should NOT be sent to the LLM, because models may treat
    # structured booleans (e.g. bills_included=false) as implicit evidence
    # and violate the "Only flag textual evidence" rule.
    _STRUCTURED_FIELDS_TO_EXCLUDE = {
        "bills_included", "pets_allowed", "has_garden",
        "listing_url", "source", "images_count",
    }

    def _prepare_context(self, listing: Dict[str, Any]) -> str:
        """Return a filtered dict containing only textual fields."""
        filtered = {
            k: v for k, v in listing.items()
            if k not in self._STRUCTURED_FIELDS_TO_EXCLUDE
        }
        return json.dumps(filtered, ensure_ascii=False)

    @staticmethod
    def _post_process_flags(listing: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic guard: suppress HIDDEN_COST_RISK false positives when
        the listing includes a council_tax_band and the evidence is only a
        generic "bills not included" phrase (no specific admin/service charges).
        """
        has_band = bool(listing.get("council_tax_band"))
        if not has_band:
            return result

        filtered_flags = []
        for flag in result.get("flags", []):
            if flag.get("category") == "HIDDEN_COST_RISK":
                evidence = flag.get("evidence", "").lower()
                generic_phrases = ["bills not included", "rent excludes bills"]
                is_generic_only = any(phrase in evidence for phrase in generic_phrases)
                specific_costs = [
                    "admin fee", "service charge", "ground rent",
                    "agency fee", "referencing fee", "management fee",
                ]
                has_specific_costs = any(cost in evidence for cost in specific_costs)
                if is_generic_only and not has_specific_costs:
                    continue  # suppress false positive
            filtered_flags.append(flag)

        result["flags"] = filtered_flags
        if not filtered_flags:
            result["overall_risk"] = "low"
        return result

    def analyze(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single listing dictionary and return red flag assessment.
        """
        try:
            context = self._prepare_context(listing)
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this listing:\n{context}"},
                ],
                temperature=0.1,
            )
            result = json.loads(response.choices[0].message.content)
            return self._post_process_flags(listing, result)
        except (APIError, APITimeoutError):
            return {
                "overall_risk": "unknown",
                "flags": [],
                "missing_info": ["AI service temporarily unavailable. Please try again in a moment."],
                "notes": "Could not complete analysis.",
            }
        except json.JSONDecodeError:
            return {
                "overall_risk": "unknown",
                "flags": [],
                "missing_info": ["Received an unexpected response from the AI. Please try again."],
                "notes": "Could not complete analysis.",
            }
        except Exception:
            return {
                "overall_risk": "unknown",
                "flags": [],
                "missing_info": ["An unexpected error occurred. Please try again."],
                "notes": "Could not complete analysis.",
            }
