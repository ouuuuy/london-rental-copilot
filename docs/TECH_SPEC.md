# Technical Specification

**Design Principle**: LLMs handle fuzzy tasks (understanding, generation, pattern recognition). Python handles deterministic tasks (filtering, arithmetic, routing).

---

## Data Flow

```
User Input (natural language)
    |
    v
[Parser Agent] → Structured Constraints JSON
    |
    v
[Python Engine: Filter] → Matched Listings
    |
    v
[Critic Agent] → Risk Report per listing
    |
    v
[Python Engine: Cost Calc] → True Cost per listing
    |
    v
[Advisor Agent] → Comparison Summary + Email Draft
    |
    v
User Output (decision support)
```
## Running the App

```bash
# Clone and setup
git clone [repo_url]
cd london-rental-copilot
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-...

# Install dependencies
pip install -r requirements.txt

# Run
streamlit run app/main.py
```

Open `http://localhost:8501` in your browser.

---

## Agent Specifications

### 1. Parser Agent (`RequirementParser`)
**Role**: Convert natural language into structured, machine-readable constraints.

**Input**: `str` — raw user query.  
**Output**: `dict`
```json
{
  "budget": 1800,
  "beds": 2,
  "pets_allowed": true,
  "has_garden": false,
  "commute_target": "Canary Wharf",
  "commute_time_minutes": 35,
  "lifestyle_tags": ["nightlife", "parks"],
  "suggested_zones": [
    {"zone_name": "Canada Water", "rationale": "Jubilee line direct, 15% cheaper"}
  ],
  "constraint_warnings": ["Garden + Zone 1 + <£1,500 is rare"],
}
```

**Model**: GPT-4o-mini, JSON mode, temperature=0.2.

---

### 2. Python Engine: Filter (`app/main.py`)
**Role**: Deterministic matching between structured constraints and `sample_listings.json`.

**Input**: 
- `dict` (Parser output: structured constraints)
- `list[dict]` (all listings from `sample_listings.json`)

**Output**: `dict`
```json
{
  "matched_listings": ["listing_001", "listing_008"],
  "match_count": 2,
  "excluded_with_reasons": [
    {"id": "listing_003", "reason": "£200 over budget"},
    {"id": "listing_005", "reason": "No pets allowed"}
  ]
}
``` 

**Logic**:
- Budget: `listing.price_pcm <= constraints.budget`
- Beds: `listing.beds == constraints.beds` (or `>=` if user says "2+ bed")
- Pets: `listing.pets_allowed == true` if `constraints.pets_allowed == true`
- Garden: `listing.has_garden == true` if `constraints.has_garden == true`
- Excluded listings annotated with reason (e.g., "£200 over budget")

**Why deterministic?**: Matching logic must be explainable, testable, and hallucination-proof.

---

### 3. Critic Agent (`RedFlagDetector`)
**Role**: Analyze a single listing for scam patterns, hidden costs, description mismatches, and pressure tactics.

**Input**: `dict` — one listing from `sample_listings.json`.  
**Output**: `dict`
```json
{
  "overall_risk": "medium",
  "flags": [
    {
      "category": "HIDDEN_COST_RISK",
      "severity": "medium",
      "evidence": "Rent excludes bills",
      "explanation": "Council tax not specified. Budget extra £150–£250/month.",
      "recommendation": "Ask agent to confirm council tax band."
    }
  ],
  "missing_info": ["Council tax band"],
  "notes": ""
}
```

**Model**: GPT-4o-mini, JSON mode, temperature=0.1 (lower = more conservative).

---

### 4. Python Engine: Cost Calc (`CostCalculator` + `TfLCommute`)
**Role**: Compute true monthly outlay using static reference data.

**Input**: `dict` (listing) + `str` (commute target station).  
**Output**: `dict`
```json
{
  "rent": 1750,
  "council_tax": 165,
  "council_tax_band": "C",
  "council_tax_borough": "Lewisham",
  "council_tax_disclaimer": null,
  "commute": 162,
  "utilities": 160,
  "true_cost": 2237,
  "notes": "Estimates based on 2026 static data."
}
```

**Deterministic rules**:
- **Council Tax**: 
  - If listing has `council_tax_band` field → use exact rate from `borough_council_tax.json`
  - If band not specified → estimate as Band C-D midpoint for that borough
  - Add disclaimer: "[WARN] Actual band (A-H) set by VOA. Verify with landlord."
  - **Never infer band from bedroom count** (bands are based on 1991 valuations)
- Commute: postcode prefix → borough → station → TfL zone → travelcard cost from `travelcard_costs.json`.
- Utilities: fixed heuristic (`£120` for 1-bed, `£160` for 2-bed).

---

### 5. Advisor Agent (`ComparisonGenerator` + `InquiryDrafter`)
**Role**: Synthesize final outputs for the user — comparisons and personalized emails.

#### ComparisonGenerator
**Model**: GPT-4o-mini, temperature=0.1 (factual synthesis, minimal creativity).
**Input**: `list[dict]` — listings enriched with `true_cost` and `red_flags`.  
**Output**: `dict`
```json
{
  "summary": "Flat A is cheaper in rent, but Flat B includes bills...",
  "trade_offs": [
    {"dimension": "cost", "comparison": "Flat A: £2,237 vs Flat B: £2,198"}
  ],
  "winner_for_budget": "listing_008",
  "winner_for_commute": "listing_001",
  "caveats": ["Verify council tax band with agent"]
}
```

#### InquiryDrafter
**Input**: `dict` (listing) + `dict` (red flags) + `dict` (user profile: persona, move-in date, pets).  
**Output**: `str` — polished enquiry email.

**Adaptive logic**:
- If `HIDDEN_COST_RISK` detected → include polite request to confirm council tax.
- If persona == "student" → mention council tax exemption.
- If `has_pets` → mention responsible pet ownership.

**Model**: GPT-4o-mini, temperature=0.3 (slightly higher for natural tone variation).

**Why temperature=0.3?**: Email drafts benefit from slight creativity (varied greetings, 
natural phrasing) while maintaining professionalism. Too low (0.0) produces robotic text; 
too high (0.7+) risks overly casual tone.

---

## Deterministic Handoff Rationale

Every calculation that affects a user's wallet (rent + tax + commute) flows through tested Python functions. LLMs only handle tasks where ambiguity is acceptable or even desirable (understanding vague user goals, detecting linguistic patterns, generating natural language). This separation means:

1. **No hallucinated arithmetic**: £1,750 + £165 + £162 = £2,077, always.
2. **Testable matching**: "Show me 2-bed flats under £1,800" returns exactly the listings that satisfy both conditions.
3. **Clear accountability**: If a number is wrong, the bug is in Python. If a red flag feels off, the issue is in the prompt.
