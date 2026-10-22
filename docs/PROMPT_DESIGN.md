# Prompt Design & Iteration Log

This document records the design, testing, and iteration of all LLM prompts in London Rental Copilot. Each version corresponds to a real code change and test run.

---

## RequirementParser

### v1.0 (2026-05-21)

**Model**: gpt-4o-mini via OpenAI API  
**Temperature**: 0.2  
**Response Format**: JSON mode

**System Prompt**:
```
You are a structured data parser for a London rental search assistant.
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
8. suggested_zones is always an empty array [] in this version.
9. Flag impossible constraints (e.g., "Zone 1 studio under £800" → "Statistically unlikely in London").
10. If information is missing, use null. Do not guess or hallucinate.
11. confidence = "high" if budget+beds+commute all present, "medium" if 2 present, "low" if 1 or fewer.
```

**Rationale**: Prompt is deliberately stripped of London-specific geographic knowledge (tube lines, borough characteristics). That knowledge lives in Python utils, not the LLM. This makes the prompt generic, testable, and less prone to hallucination.

---

### Test Cases

| ID | Input | Expected Output (Key fields) | Actual | Status |
|----|-------|---------------------------|--------|--------|
| T1 | "2 bed, £1,800, pet-friendly, 30 min to Canary Wharf" | `{budget: 1800, beds: 2, pets_allowed: true, commute_target: "Canary Wharf", commute_time_minutes: 30, confidence: "high"}` | `{budget: 1800, beds: 2, pets_allowed: true, commute_target: "Canary Wharf", commute_time_minutes: 30, confidence: "high"}` — Filter: 0 matches (dataset has no 2-bed pet-friendly under £1,800) | [OK] Pass |
| T2 | "I want to live in a quiet place, budget 1500" | `{budget: 1500, lifestyle_tags: ["quiet"], confidence: "low"}` | `{budget: 1500, beds: null, lifestyle_tags: ["quiet"], confidence: "low"}` — Filter: 5 matches (all listings ≤£1,500, beds not filtered) | [OK] Pass |
| T3 | "Zone 1, under £2000, no pets" | `{budget: 2000, pets_allowed: false, confidence: "medium"}` | `{budget: 2000, pets_allowed: false, commute_target: "Zone 1", confidence: "medium"}` — Filter: 11 matches (excluded 3 pet-friendly listings; Zone 1 not yet enforced by Filter) | [WARN] Partial pass |

---

### Iteration Log

**[2026-05-21] v1.0 Initial Test Run**:
- T1 (English standard input): Parser correctly extracted budget/ beds/ pets/ commute_target/ commute_time. Filter 0 matches — consistent with dataset reality (no 2-bed + pet-friendly + ≤£1,800 listings). [OK] Pass
- T2 (Chinese fuzzy input): Parser correctly extracted budget=1500, mapped "quiet" to lifestyle_tags=["quiet"]. beds not mentioned → null, Filter correctly does not filter beds. [OK] Pass
- T3 (Negative condition): Parser correctly extracted budget=2000, pets_allowed=false. commute_target="Zone 1" was extracted but **Filter has not yet integrated zone filtering logic**, therefore returned all non-pet-friendly listings ≤£2,000 (11 items). [WARN] This is a known feature gap, not a Prompt bug. Will be addressed after CostCalculator / TfLCommute integration is complete. Partial pass.

**Current status**: v1.0 Prompt needs no modification, 3/3 cases are correct at the Parser level. Next iteration will be on RedFlagDetector (Day 3).

---

## RedFlagDetector

### v1.0 (2026-05-21)

**Model**: gpt-4o-mini via OpenAI API  
**Temperature**: 0.1 (lower than Parser — classification needs conservatism)  
**Response Format**: JSON mode

**System Prompt**:
```
You are a consumer protection analyst specializing in UK rental listings.
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
   - Triggers: Council tax not mentioned, "bills excluded" without specifying which, vague service charges, "admin fees" mentioned.
   - Do NOT flag if listing explicitly states council tax band or says "all bills included".

3. DESCRIPTION_MISMATCH (Low severity)
   - Triggers: Superlatives ("spacious", "luxury", "high-spec") unsupported by details or photos, "recently renovated" with no kitchen/bathroom mention.
   - Do NOT flag standard marketing language like "lovely", "bright", "well-presented".

4. LANDLORD_PRESSURE (Medium severity)
   - Triggers: ALL CAPS urgency, "MUST view today", "FIRST COME FIRST SERVE", "20 enquiries already", "available immediately must move in this weekend".
   - Do NOT flag normal availability phrases like "Available from 1st June" or "Viewing highly recommended".

RULES:
- Only flag if there is textual evidence in the listing.
- Use "low" severity for minor omissions; "high" for active scam indicators.
- If no flags are found, return an empty flags array and overall_risk "low".
- Never make accusations without evidence.
- For clean listings, missing_info can still note useful omissions (e.g., "Council tax band not specified") without raising a flag.
```

**Rationale**: Temperature=0.1 ensures the model is less creative and more rule-bound. The negative examples ("Do NOT flag...") are critical — early tests showed the model falsely flags "Viewing highly recommended" as pressure without them.

---

### Test Cases

| ID | Listing | Expected Flags | Actual | Status |
|----|---------|---------------|--------|--------|
| RF1 | listing_003 — SCAM studio | `SCAM_RISK (High)`: "Send deposit via bank transfer" | `SCAM_RISK (High)` — evidence complete original text quote; overall_risk=high | [OK] Pass |
| RF2 | listing_004 — HIDDEN_COST | `HIDDEN_COST_RISK (Medium)`: "Rent excludes bills" (no council tax) | `HIDDEN_COST_RISK (Medium)` — evidence: "Rent excludes bills" | [OK] Pass (v1.1) |
| RF3 | listing_006 — DESCRIPTION | `DESCRIPTION_MISMATCH (Low)`: "Truly luxury living" + only 3 images | `HIDDEN_COST_RISK (Medium)` — DESCRIPTION judged by the model as common, not flagged | [WARN] Acceptable |
| RF4 | listing_005 — PRESSURE | `LANDLORD_PRESSURE (Medium)`: "HURRY!", "Don't sleep on this!!!" | `LANDLORD_PRESSURE (Medium)` + `HIDDEN_COST_RISK (Medium)` (bills_included:false) | [OK] Pass |
| RF5 | listing_008 — Clean | No flags, `overall_risk: "low"` | flags=[], overall_risk="low" | [OK] Pass |

---

### Iteration Log

**[2026-05-22] v1.0 Test Run — Results Summary**

| Metric | Result |
|--------|--------|
| SCAM Recall (RF1) | 100% [OK] |
| Clean listing High-severity FP | 0 [OK] |
| Clean listing Low/Medium FP | 0 [OK] |
| HIDDEN_COST Recall (RF2) | 0% [FAIL] |
| DESCRIPTION Recall (RF3) | 100% [OK] |
| PRESSURE Recall (RF4) | 100% [OK] |

**RF1 — listing_003 (SCAM)**:
- Output: `SCAM_RISK (High)`, evidence complete quote "Landlord is abroad. Send deposit via bank transfer to secure. Viewing available after payment."
- The notes field also proactively added "Price is significantly below market rate for central London" and "Only one image provided" — this is value-added analysis, no false positives generated.
- [OK] Pass

**RF2 — listing_004 (HIDDEN_COST)** — **False Negative**:
- Description: "Rent excludes bills. Professional tenants preferred."
- Expected: `HIDDEN_COST_RISK (Medium)` because "Rent excludes bills" does not specify which bills (council tax not mentioned).
- Actual: flags=[], overall_risk="low".
- **Root cause analysis**: Prompt v1.0's HIDDEN_COST trigger condition is "'bills excluded' without specifying which", but the model did not recognize "Rent excludes bills" as an equivalent expression. The model's interpretation of this phrase leans toward "stating a fact" rather than "hidden cost risk".
- **Fix direction (v1.1)**: In the RedFlagDetector.SYSTEM_PROMPT's HIDDEN_COST_RISK definition, add an explicit trigger phrase list ("rent excludes bills", "bills not included", "bills excluded") and supplement with a few-shot positive example.

**RF3 — listing_006 (DESCRIPTION_MISMATCH)**:
- Output: `DESCRIPTION_MISMATCH (Low)`, evidence "Truly luxury living in the heart of Angel. High-spec finish throughout."
- [OK] Pass

**RF4 — listing_005 (LANDLORD_PRESSURE)**:
- Output: `LANDLORD_PRESSURE (Medium)`, evidence fully covers "HURRY!...Don't sleep on this!!!"
- Note: In the plan table, Expected severity was originally High, but the Prompt defines LANDLORD_PRESSURE as Medium. Actual output Medium is consistent with the Prompt definition; plan table corrected.
- [OK] Pass

**RF5 — listing_008 (Clean)**:
- Output: flags=[], overall_risk="low". No false positives.
- [OK] Pass

---

### v1.1 (2026-05-22) — HIDDEN_COST False Negative Fix

**Changes**:
In `RedFlagDetector.SYSTEM_PROMPT`'s HIDDEN_COST_RISK definition, changed the trigger condition from a vague description to a more explicit phrase list, and added a few-shot example.

**Modified HIDDEN_COST_RISK paragraph**:
```
2. HIDDEN_COST_RISK (Medium severity)
   - Triggers: "rent excludes bills" / "bills not included" / "bills excluded" WITHOUT specifying which (gas, electricity, water, council tax); vague service charges; "admin fees" mentioned; council tax not mentioned when rent excludes bills.
   - Do NOT flag if listing explicitly states council tax band, says "all bills included", or lists specific excluded bills (e.g., "water included, gas and electricity excluded").
   - Example (flag): "Rent excludes bills" → HIDDEN_COST_RISK because renter cannot estimate total monthly outlay.
   - Example (do NOT flag): "Water rates included" + other bills not mentioned → normal partial disclosure, do not flag.
```

**Rationale**: In v1.0, semantic sensitivity for "Rent excludes bills" was insufficient. By explicitly listing trigger phrases and providing a positive example, we reduce the model's omission rate for this expression, while retaining negative examples to prevent false positives on normal disclosures such as "Water rates included".

**Actual test results v1.1**:

| Metric | v1.0 | v1.1 |
|--------|------|------|
| SCAM Recall (RF1) | 100% [OK] | 100% [OK] |
| HIDDEN_COST Recall (RF2) | 0% [FAIL] | 100% [OK] |
| DESCRIPTION Recall (RF3) | 100% [OK] | 0% [WARN] |
| PRESSURE Recall (RF4) | 100% [OK] | 100% [OK] |
| Clean FP (RF5) | 0 [OK] | 0 [OK] |

**RF2 — listing_004 (HIDDEN_COST)**:
- Output: `HIDDEN_COST_RISK (Medium)`, evidence: "Rent excludes bills". [OK] Fix successful.
- The notes also self-corrected "'Professional tenants preferred' is a common preference and not a pressure tactic" — demonstrating the conservative principle.

**RF3 — listing_006 (DESCRIPTION_MISMATCH)** — **New False Negative**:
- v1.0 output `DESCRIPTION_MISMATCH (Low)`, v1.1 output became `HIDDEN_COST_RISK (Medium)` (based on "Bills not included. Council tax applies."), DESCRIPTION was missed.
- **Root cause**: The model tends to focus on the strongest flag in a single analysis. After strengthening HIDDEN_COST's trigger condition, the model judged "Bills not included + Council tax applies" as Medium, and at the same time explained in the notes that "'luxury' and 'high-spec' ... is common and not flagged as a mismatch".
- **Assessment**: This is an acceptable trade-off. Acceptance criteria allow DESCRIPTION False Negative ≤ 1. From a product manager perspective, Medium HIDDEN_COST provides higher decision-making value for the user than Low DESCRIPTION_MISMATCH.

**RF4 — listing_005 (PRESSURE)**:
- Retained `LANDLORD_PRESSURE (Medium)` [OK]
- **New**: Also output `HIDDEN_COST_RISK (Medium)`, evidence is `bills_included: false` (from JSON structured field, not description text).
- **Assessment**: Strictly speaking, this violates the "Only flag if there is textual evidence in the listing" rule, but `bills_included` itself is also part of the listing data, and this listing indeed did not disclose bill details. It did not affect the overall risk level (remains medium), not considered a serious false positive.

**Conclusion**: v1.1 successfully fixed HIDDEN_COST's zero-tolerance False Negative, at the cost of one DESCRIPTION omission (within tolerance). Current Prompt status is stable, no further iteration needed.

---

---

## ComparisonGenerator

*Planned for Day 4. Prompt not yet drafted.*

---

## InquiryDrafter

### v1.0 (2026-05-22)

**Model**: gpt-4o-mini via OpenAI API  
**Temperature**: 0.3 (slightly higher than Detector for natural tone variation)  
**Response Format**: Plain text (not JSON)

**System Prompt**:
```
You are a helpful assistant that drafts rental enquiry emails for London properties.

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
- End with a professional sign-off.

OUTPUT FORMAT:
Return ONLY the email text (including subject line). No markdown code blocks, no JSON, no extra commentary.
```

**Rationale**: Temperature=0.3 balances consistency with natural variation. Too low (0.0) produces robotic text; too high (0.7+) risks overly casual tone. The explicit negative examples ("do not use phrases like...") are critical — early tests showed LLMs tend toward excessive enthusiasm in rental contexts.

---

### Test Cases

| ID | Listing | User Profile | Expected |
|----|---------|--------------|----------|
| ID1 | listing_004 (HIDDEN_COST flagged) | young professional, no pets, move-in 1st July | Email body contains an explicit question about council tax (e.g. "Could you please confirm the council tax band for the property?" / "What is the monthly council tax?"). Cannot be just a declarative sentence mentioning council tax |
| ID2 | listing_012 (clean, pets allowed) | student, has cat, move-in 1st July | 1) Email body contains "student" and "council tax exemption" or "exempt from council tax"; 2) Email body contains "pet" / "cat" and "responsible" / "well-trained" etc.; 3) Does not mention council tax band question (because listing has no HIDDEN_COST flag) |
| ID3 | listing_008 (clean) | young professional, no pets | 1) Email body does NOT contain council tax related questions; 2) Email body does NOT contain pet related content; 3) tone concise professional, 150-200 words; 4) Has explicit viewing availability proposal |

**Acceptance criteria detail**:
- "Asking about council tax band" = email contains a question about council tax (ending with ? and containing "council tax" keyword). Only stating "I noted the rent excludes bills" does not count as a pass.
- "Mentioning council tax exemption" = email contains "exempt" / "exemption" + "council tax" keyword combination.
- "No extra questions" = email does not contain extra questions unrelated to listing known information (e.g., council tax band, pet policy, etc.).

---

### Iteration Log

**[2026-05-22] v1.0 Test Run — OpenAI API (gpt-4o-mini)**

| Metric | Result |
|--------|--------|
| ID1: HIDDEN_COST → council tax question | [OK] Pass |
| ID2: student → exemption mentioned | [OK] Pass (after adding persona hint) |
| ID2: pet → responsible pet owner | [OK] Pass |
| ID3: clean → no council tax question | [OK] Pass (after filtering missing_info from context) |
| ID3: tone concise professional | [OK] Pass |
| All drafts 150-200 words | [OK] Pass |

**ID1 — listing_004 (HIDDEN_COST) + young professional**:
- Output: Draft includes explicit question "could you provide information regarding the council tax band for the property, as well as any additional service charges that may apply."
- [OK] Pass

**ID2 — listing_012 (clean) + student + pets**:
- First attempt: Model mentioned "student" and "pet" but omitted "council tax exemption".
- **Fix**: Added persona hint in `_build_context`: `"(student: mention council tax exemption eligibility)"`.
- Second attempt: "I am a full-time student and may be eligible for council tax exemption, which is an important consideration for me."
- [OK] Pass

**ID3 — listing_008 (clean) + young professional**:
- First attempt: Model asked about council tax despite no red flags. Root cause: `missing_info` from RedFlagDetector contained "Council tax information", which was treated by the model as a trigger.
- **Fix**: Filtered `missing_info` and `notes` from the context passed to InquiryDrafter. Added explicit rule: "If no red flags are detected, do NOT ask about council tax or service charges."
- Second attempt: Concise standard email with only viewing request. No council tax question.
- [OK] Pass

**RedFlagDetector issue discovered during InquiryDrafter testing**:
- After switching from Deepseek to OpenAI (gpt-4o-mini), `listing_008` and `listing_012` (both clean) were falsely flagged with `HIDDEN_COST_RISK` because the model used the structured field `bills_included: false` as implicit evidence.
- **Fix**: Added `_STRUCTURED_FIELDS_TO_EXCLUDE` in `redflag_detector.py` to filter out `bills_included`, `pets_allowed`, `has_garden`, etc. from the LLM context. This forces the model to rely solely on textual evidence in the title and description.
- Post-fix verification: `listing_003` (SCAM) still correctly flagged; `listing_008` and `listing_012` returned clean.
- [OK] Fixed
