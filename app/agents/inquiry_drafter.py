import os
from typing import Dict, Any
from openai import OpenAI, APIError, APITimeoutError


class InquiryDrafter:
    """
    Agent 4: Drafts a personalised, polite enquiry email for a rental listing.
    Adapts tone and content based on red flags and user profile.
    """

    SYSTEM_PROMPT = """You are a helpful assistant that drafts rental enquiry emails for London properties.

TONE: Professional, polite, warm but not overly casual. Use British English spelling.

STRUCTURE:
1. Subject line (concise, under 10 words)
2. Greeting
3. Expression of interest + brief self-introduction (1 sentence)
4. 1-2 specific questions based on context:
   - If the listing has HIDDEN_COST_RISK red flags: ask about council tax band and any service charges
   - If the user is a student: mention council tax exemption status
   - If the user has pets: mention responsible pet ownership
5. Propose viewing availability
6. Polite closing

RULES:
- Never sound desperate or pressured. Do not use phrases like "I REALLY need this flat" or "Please please reply".
- Do not mention red flags as "warnings" — frame any concerns as polite, natural questions.
- Keep to 150-200 words.
- Do not invent personal details not provided in the user profile (e.g., do not invent a job title).
- If the listing is clean (no red flags) and the user is a standard professional without pets, keep the email concise and standard.
- If persona is "student", proactively mention that you are a full-time student and may be eligible for council tax exemption. Do this in a natural, brief sentence.
- End with a professional sign-off.

OUTPUT FORMAT:
Return ONLY the email text (including subject line). No markdown code blocks, no JSON, no extra commentary.
"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def draft(
        self,
        listing: Dict[str, Any],
        red_flags: Dict[str, Any],
        user_profile: Dict[str, str],
    ) -> str:
        """
        Generate a personalised enquiry email.

        Args:
            listing: A single listing dict from sample_listings.json.
            red_flags: Output from RedFlagDetector for this listing.
            user_profile: Dict with keys like persona, move_in_date, has_pets.
        """
        try:
            context = self._build_context(listing, red_flags, user_profile)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context},
                ],
                temperature=0.3,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except (APIError, APITimeoutError):
            return "AI service temporarily unavailable. Please try again in a moment."
        except Exception:
            return "An unexpected error occurred while drafting the email. Please try again."

    @staticmethod
    def _build_context(
        listing: Dict[str, Any],
        red_flags: Dict[str, Any],
        user_profile: Dict[str, str],
    ) -> str:
        lines = [
            "Listing Details:",
            f"- Title: {listing.get('title', '')}",
            f"- Price: £{listing.get('price_pcm', 0)}/month",
            f"- Location: {listing.get('location_postcode', '')}",
            f"- Bedrooms: {listing.get('beds', 'unknown')}",
            "",
            "Red Flags (only use these for adaptive logic):",
        ]

        flags = red_flags.get("flags", [])
        if flags:
            for f in flags:
                lines.append(
                    f"- {f.get('category')} ({f.get('severity')}): {f.get('evidence')}"
                )
        else:
            lines.append("- No red flags detected. Keep the email concise and standard.")

        persona = user_profile.get('persona', 'young professional')
        persona_hint = ""
        if persona == 'student':
            persona_hint = " (student: mention council tax exemption eligibility)"
        elif persona == 'family':
            persona_hint = " (family: mention suitability for family living)"

        lines.extend(
            [
                "",
                "User Profile:",
                f"- Persona: {persona}{persona_hint}",
                f"- Move-in date: {user_profile.get('move_in_date', 'ASAP')}",
                f"- Has pets: {user_profile.get('has_pets', False)}",
                "",
                "Please draft a polite, professional enquiry email based on the above.",
                "IMPORTANT: Only ask about council tax if there is a HIDDEN_COST_RISK flag above.",
                "If no red flags are detected, do NOT ask about council tax or service charges.",
            ]
        )

        return "\n".join(lines)
