# London Rental Copilot — Product Requirements Document

**Version**: 1.0 (MVP)  
**Date**: 2026-05-21  
**Author**: [Your Name]  
**Status**: In Development

---

## 1. Product Overview

| Field | Description |
|-------|-------------|
| **Product Name** | London Rental Copilot |
| **One-liner** | An AI-powered decision-support tool that helps renters navigate London's property market by parsing natural-language requirements, detecting listing red flags, calculating true monthly costs, and drafting personalized inquiry emails. |
| **Target User** | Young professionals and students moving to or within London, typically searching in the £1,200–£2,500/month range, time-constrained, unfamiliar with London's borough-level nuances. |
| **Platform** | Web application (Streamlit-based MVP) |
| **Core Value Proposition** | Existing portals (Rightmove, Zoopla) are **search engines**; Copilot is a **decision-support system** that actively warns, contextualizes, and explains. |

---

## 2. Problem Statement

### 2.1 Market Context
London is one of the most competitive rental markets globally. In Q1 2026, average time-on-market for a desirable property was **< 7 days**, and tenants typically compete with 5–10 other applicants.

### 2.2 User Pain Points (Validated via Personal Experience + 3 Peer Interviews)

| Pain Point | Evidence | Existing Tool Gap |
|------------|----------|-----------------|
| **Discovery is fragmented** | Users toggle between Rightmove, Zoopla, Spareroom, and Facebook groups. | No unified view; each portal has different filters and data quality. |
| **Hidden costs surprise tenants** | Council Tax bands vary £100–£250/month by borough; commute costs (TfL Zone 1–6) add £150–£300/month. | Portals show rent only. Users manually calculate total cost in spreadsheets. |
| **Scams and misleading listings** | "£900 for a studio in Zone 1" often lacks council tax info, has vague descriptions, or uses stock photos. | No automated flagging of suspicious patterns. |
| **Commute-time anxiety** | "30 minutes to Liverpool Street" can mean 30 min on one line or 45 min with 2 changes. | Portals show "distance" or rough time, not personalized door-to-door estimates. |
| **Analysis paralysis** | Users favorite 10+ properties but struggle to compare trade-offs (space vs. commute vs. price). | No intelligent comparison or recommendation logic. |

### 2.3 Why AI?
- **Natural Language Input**: Users think in goals ("I want to live somewhere lively, 30 min to Shoreditch, under £1,800"), not filter matrices.
- **Pattern Recognition**: LLMs can detect linguistic red flags (vagueness, urgency pressure, omitted fees) better than rule-based systems.
- **Synthesis**: Aggregating rent + tax + commute + utilities into a single "true cost" requires contextual reasoning about London-specific norms.

---

## 3. Product Principles

These principles guide every feature decision and are deliberately opinionated:

1. **Transparency over Magic**: Every AI recommendation must show its reasoning. Renting is a high-stakes decision; black-box suggestions erode trust.
2. **Local Context over Generic Knowledge**: The AI should know that "Elephant & Castle is undergoing regeneration" or "Parts of Peckham have excellent Overground links." Generic LLM knowledge about "London" is insufficient.
3. **Decision Support, Not Decisions**: The tool provides warnings, comparisons, and cost estimates. It never says "rent this flat" — the human makes the final call.
4. **Safety First**: We deliberately exclude contract review, legal advice, or deposit dispute guidance. Liability is too high for an MVP.

---

## 4. Functional Requirements (MVP)

### 4.1 Feature 1: Smart Requirement Parser
**User Story**: As a renter, I want to describe my ideal home in plain English so that the system suggests realistic areas I hadn't considered.

**Acceptance Criteria**:
- [ ] Accepts free-text input (e.g., "2 bed, £1,800 max, pet-friendly, commute to Canary Wharf under 35 min, want some nightlife nearby").
- [ ] Outputs a structured query object: `{budget: 1800, beds: 2, pets: true, commute_target: "Canary Wharf", commute_time: 35, lifestyle_tags: ["nightlife"]}`.
- [ ] **Data Handoff**: The structured JSON is passed to a Python deterministic engine that filters `sample_listings.json` against the constraints (budget cap, bedroom count, pet policy). The output includes `matched_listings` (array of matching listing IDs) and `match_count`.
- [ ] Filtered results are displayed with **highlighted match reasons** (e.g., "Matches budget", "Pet-friendly") and **explanation for excluded listings** (e.g., "£200 over budget" or "No pets allowed").
- [ ] Suggests 2–3 additional zones/boroughs with rationale (e.g., "Consider Canada Water — Jubilee line direct, 15% cheaper than Canary Wharf, has pubs and parks").
- [ ] Flags constraints that may be mutually exclusive (e.g., "A garden + Zone 1 + under £1,500 is extremely rare — consider dropping one constraint").

**AI Product Decisions**:
- **Model**: GPT-4o-mini via OpenAI API (structured JSON mode for reliability).
- **Prompt Strategy**: Few-shot examples with London-specific zone/commute knowledge injected via system prompt.
- **Deterministic Handoff**: Parser Agent outputs structured JSON; Python Engine (`app/main.py`) performs exact filtering. This separation ensures that **matching logic is explainable and testable**, while AI handles the fuzzy task of understanding natural language.
- **Fallback**: If parsing fails or produces impossible constraints, surface a clarifying question rather than crashing or guessing.

### 4.2 Feature 2: Listing Red Flag Detector
**User Story**: As a renter, I want suspicious patterns in a listing automatically highlighted so that I avoid scams or hidden-fee traps.

**Acceptance Criteria**:
- [ ] Analyzes listing title, description, and images (text-only in MVP; image analysis as v2).
- [ ] Detects and classifies risks into categories: `SCAM_RISK`, `HIDDEN_COST_RISK`, `DESCRIPTION_MISMATCH`, `LANDLORD_PRESSURE`.
- [ ] Provides a severity score (Low / Medium / High) and a plain-English explanation.
- [ ] Does not falsely flag legitimate listings > 90% of the time (qualitative evaluation with test set).

**Red Flag Taxonomy (MVP)**:

| Category | Example Trigger | Explanation to User |
|----------|----------------|---------------------|
| `SCAM_RISK` | "Send deposit before viewing," "Landlord abroad, use Western Union," price 40%+ below market rate. | "This listing shows classic pre-viewing deposit pressure. Never send money before viewing." |
| `HIDDEN_COST_RISK` | No mention of council tax, bills "not included" buried in text, service charges vague. | "Council tax and service charges aren't specified. Budget an extra £150–£250/month." |
| `DESCRIPTION_MISMATCH` | "Spacious" but square footage < 350 sq ft; "recently renovated" but no photos of kitchen/bathroom. | "Description claims 'spacious' but layout suggests compact. Request exact floorplan." |
| `LANDLORD_PRESSURE` | "Urgent — available immediately," "Many interested, act fast," all-caps urgency. | "Urgency tactics are common. Don't skip reference checks due to time pressure." |

**AI Product Decisions**:
- **Model**: GPT-4o-mini with carefully crafted system prompt emphasizing conservative flagging (better to miss a flag than falsely accuse a legit landlord).
- **Evaluation**: 30 hand-labelled listings; iterate prompt until precision > 0.9.
- **Bias Check**: Ensure the model doesn't disproportionately flag listings from certain boroughs or with non-native English descriptions.

### 4.3 Feature 3: True Cost Comparison Engine
**User Story**: As a renter, I want to compare my shortlisted properties by total monthly outlay, not just rent, so that I make an informed budget decision.

**Acceptance Criteria**:
- [ ] For each listing, calculates: `True Monthly Cost = Rent + Est. Council Tax + Commute Cost + Est. Utilities`.
- [ ] Council tax uses **heuristic dynamic band mapping**: Python `CostCalculator` infers the likely band from bedroom count, then looks up the borough-specific rate:
  - Studio / 1-bed → Band B or C (heuristic: Band B for studio, Band C for 1-bed)
  - 2-bed → Band C or D (heuristic: Band D)
  - 3-bed+ → Band D or E (heuristic: Band D)
  - Band rates are computed as proportions of the borough's Band D rate (e.g., Band C ≈ 8/9 of Band D).
- [ ] UI displays a **disclaimer** next to every Council Tax estimate: *"This is a heuristic estimate based on bedroom count. Actual band is determined by the VOA and may differ."*
- [ ] Commute cost derived from zones required to reach workplace (e.g., Zone 2–3 monthly Travelcard).
- [ ] Generates a natural-language summary: "Flat A is £150/month cheaper in rent, but Flat B includes bills and is in a lower council tax band. Net difference: only £40/month."
- [ ] Supports side-by-side comparison of up to 3 shortlisted listings.

**Data Sources (MVP)**:
- Council Tax bands: Static JSON mapping `borough → average Band D rate` (2026 rates).
- Commute zones: Static JSON mapping `station/postcode prefix → TfL zone`.
- Travelcard costs: Static JSON (`zone_range → monthly Oyster/Travelcard cost`).
- Utilities estimate: Fixed heuristic (`£120/month for 1-bed, £160/month for 2-bed`), with disclaimer that this varies.

**AI Product Decisions**:
- **Model**: GPT-4o-mini for natural-language summary generation; calculation logic is deterministic Python to prevent hallucinated arithmetic.
- **Heuristic over LLM Guessing**: Council Tax band inference is a deterministic Python algorithm based on bedroom count, not an LLM estimate. This guarantees consistency and testability across all listings.
- **Trust**: Every number is clickable/traceable to its source (e.g., "Council Tax: Lewisham Band D ≈ £1,850/year → £154/month"). A disclaimer is always shown because band assignment is ultimately a government decision, not an AI prediction.

### 4.4 Feature 4: Instant Inquiry Drafter
**User Story**: In London's hyper-competitive rental market, desirable properties receive enquiries within minutes of listing. As a renter, I want to generate a personalized, polite, and context-aware enquiry email in seconds so that I can respond faster than other applicants while still appearing professional.

**Acceptance Criteria**:
- [ ] Accepts user profile inputs: `persona_type` (student / young professional / family), `move_in_date`, `has_pets`, `preferred_tenancy_length`.
- [ ] Accepts a selected listing and its Red Flag detection report as context.
- [ ] Generates a single, cohesive enquiry email (English) with the following adaptive logic:
  - **Tone calibration**: Students get a slightly more deferential tone; professionals get concise and direct.
  - **Red-flag rebuttal**: If `HIDDEN_COST_RISK` was detected, the email politely asks: *"Could you please confirm the council tax band and any service charges?"*
  - **Student exemption**: If persona is "student", include: *"I am a full-time student and exempt from council tax."*
  - **Pet disclosure**: If `has_pets` is true, proactively mention responsible pet ownership and willingness to pay a higher deposit.
  - **Urgency without desperation**: Convey genuine interest and availability for viewings without sounding pressured.
- [ ] UI provides **"Copy to Clipboard"** and **"Regenerate"** buttons.
- [ ] A persistent disclaimer is shown: *"This is an AI-generated draft. Please review and personalize before sending."*

**AI Product Decisions**:
- **Model**: GPT-4o-mini.
- **Prompt Strategy**: Few-shot examples with explicit tone calibration. The prompt includes both positive examples (well-crafted emails) and negative examples (overly aggressive or desperate language).
- **Safety**: The tool never sends emails on behalf of the user. It is strictly a drafting assistant; the user must consciously copy, edit, and send via their own email client. This eliminates liability and respects user agency.

---

## 5. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | AI responses (parsing, flagging, comparison) complete in < 3 seconds. |
| **Cost** | MVP uses GPT-4o-mini; estimated API cost < £5 for full development + demo usage. |
| **Privacy** | No user data persisted server-side. Listing data is public-domain scraped samples. |
| **Accessibility** | Streamlit defaults are acceptable for MVP; ensure color-blind-friendly flag indicators (icons + color). |
| **Mobile** | Streamlit apps are responsive; primary use case is desktop research, but mobile should be usable. |

---

## 6. Data Strategy

### 6.1 Sample Dataset (MVP)
- **Size**: 30–50 manually curated listings spanning Zones 1–4, price ranges £1,000–£2,800, mixed property types.
- **Sources**: Public Rightmove/Zoopla listings (anonymized — exact addresses truncated to postcode district, e.g., "E1").
- **Schema**: `id, title, description, price_pcm, location_postcode, property_type, beds, baths, bills_included (bool), has_garden (bool), pets_allowed (bool), images_count, listing_url (optional)`.

### 6.2 Static Reference Data
- `borough_council_tax.json`: 32 London boroughs + City of London, average Band D monthly cost.
- `station_zone_map.json`: Major stations and their TfL zones.
- `travelcard_costs.json`: 2026 monthly Travelcard costs by zone combination.

---

## 7. Out of Scope (Intentionally Excluded)

**Scope Discipline Statement**: The MVP strictly uses a static dataset of 30–50 listings (`sample_listings.json`). There is **no live scraping, no third-party API integration for listings, and no real-time data pipeline**. This constraint is intentional: it keeps the project focused on AI product logic (parsing, flagging, synthesis) rather than brittle infrastructure. All listings are manually curated, anonymized samples.

| Feature | Reason for Exclusion |
|---------|----------------------|
| Live scraping/API integration | Rightmove/Zoopla have anti-bot measures and TOS restrictions. Static dataset is sufficient to demonstrate product logic. |
| Contract review / legal advice | High liability; requires legal expertise and regulatory compliance (unauthorized practice of law risk). |
| Real-time chatbot interface | Adds complexity without demonstrating better product thinking than a workflow-based UI. |
| Image analysis of listings | Vision API increases cost and latency; text-based red flags are sufficient for MVP. Planned for v2. |
| User accounts / save & sync | Increases engineering scope; browser session state + CSV export is sufficient for MVP. |

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM hallucinates commute or cost data | Medium | High (erodes trust) | All calculations use deterministic Python with static data; LLM only generates summaries from pre-computed numbers. |
| False positive red flags damage landlord reputation | Low | Medium | Flag explanations are tentative ("This may indicate..."); severity calibrated conservatively. |
| Static data becomes outdated (council tax, travelcard costs) | High | Low | Data files are versioned and easily updatable; UI shows "last updated" date. |
| Scope creep ("just add one more feature") | High | High | Strict MVP definition; all new ideas logged in `BACKLOG.md` for post-MVP evaluation. |

---

## 9. Success Metrics (for this Side Project)

Since this is a portfolio project, success is measured by **demonstrated product thinking** and **recruiter engagement**, not MAU:

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| End-to-end demo works without errors | 100% | Manual test of 5 representative user flows. |
| **Red Flag Detector — Precision** | ≥ 90% | Manual evaluation on 30 labelled listings. |
| **Red Flag Detector — Recall (overall)** | ≥ 85% | Manual evaluation on 30 labelled listings. |
| **Red Flag Detector — Recall (severe scams)** | **100%** | Zero tolerance for missing pre-viewing deposit scams, Western Union requests, or "landlord abroad" narratives. |
| Recruiter can understand value in < 60 seconds | Yes | README + 30-sec GIF meets this. |
| Personal learning: can explain 3 product trade-offs | Yes | Documented in `PRODUCT_DECISIONS.md`. |

### Gold Standard Dataset
- A curated set of **30 listings** with human-annotated red flags across all four categories (`SCAM_RISK`, `HIDDEN_COST_RISK`, `DESCRIPTION_MISMATCH`, `LANDLORD_PRESSURE`).
- Evaluation uses a confusion-matrix approach: **True Positives** (correctly flagged), **False Positives** (over-flagging), **False Negatives** (missed risks).
- Prompt iteration is driven by **false positive analysis** — each false positive is logged with the offending phrase to refine few-shot examples.
- Evaluation notebook planned at `notebooks/evaluation.ipynb`.

---

## 10. Roadmap

### v1.0 (MVP) — Current
- Smart Requirement Parser
- Red Flag Detector (text-only)
- True Cost Comparison (3 listings max)
- Instant Inquiry Drafter
- Static dataset of 30–50 listings

### v1.1 (Post-MVP Ideas — Not Committed)
- Image analysis for stock-photo detection
- Export shortlist to PDF/email
- Integration with TfL API for real-time commute times
- "Market rate" comparison (is this flat under/overpriced for the area?)

### v2.0 (Stretch Vision)
- Browser extension that injects Copilot analysis directly into Rightmove/Zoopla listing pages
- Community-sourced landlord/agent reviews
- Reminder bot for viewing scheduling

---

## 11. Open Questions

1. Should we include a "negotiation assistant" that suggests offer strategies based on days-on-market and listing red flags?
2. How do we handle listings where "bills included" is mentioned but unclear which bills (gas/electric vs. just water)?
3. Is there value in a "neighborhood vibe" feature that maps lifestyle tags ("quiet family area" vs. "young professional hub") to postcode districts?

---

*This PRD is a living document. Iterations will be tracked via Git commit history and reflected in version notes.*
