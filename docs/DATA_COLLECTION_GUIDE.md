# Data Collection Guide for `sample_listings.json`

## Goal
Build a curated dataset of **30–50 listings** that spans diverse boroughs, price points, property types, and red-flag categories. This dataset is the backbone of the MVP — it must be rich enough to demonstrate all four features (Parser, Red Flag, Cost Calculation, Inquiry Draft).

---

## Where to Find Listings

Use these portals to browse real listings. **Do not scrape** — manually copy key fields.

| Portal | Best For | Notes |
|--------|----------|-------|
| **Rightmove** | Breadth, professional listings | Most listings have full descriptions. Good for "normal" baseline data. |
| **Zoopla** | Price history, area stats | Often has duplicate listings with slightly different wording. Good for comparison. |
| **Spareroom** | Flatshares, lower budgets | Different tone (more casual). Good for `LANDLORD_PRESSURE` variants. |
| **OpenRent** | Direct landlord listings | Often less polished descriptions. Higher scam risk signals here. |

---

## Step-by-Step Collection Workflow

### Step 1: Pick Your Borough Coverage Strategy
Aim to cover **at least 10 different boroughs** so the Council Tax calculator feels realistic. Use this checklist:

- [ ] Lewisham (SE13, SE14)
- [ ] Tower Hamlets (E1, E14)
- [ ] Hackney (E2, E8)
- [ ] Islington (N1)
- [ ] Camden (NW1, NW5)
- [ ] Westminster (W1, SW1)
- [ ] Wandsworth (SW11)
- [ ] Southwark (SE1, SE16)
- [ ] Lambeth (SW9, SE11)
- [ ] Newham (E15, E16)
- [ ] Brent (NW10)
- [ ] Croydon (CR0)

### Step 2: Pick Price Tiers
Aim for a spread across these tiers:

| Tier | Price Range | Typical Zone | Quantity Target |
|------|-------------|--------------|-----------------|
| Budget Studio | £1,000–£1,300 | Zone 2–3 | 4–6 listings |
| Mid 1-Bed | £1,350–£1,700 | Zone 1–2 | 8–10 listings |
| Standard 2-Bed | £1,750–£2,200 | Zone 1–3 | 10–12 listings |
| Premium 2+/3-Bed | £2,300–£2,800 | Zone 1–2 | 4–6 listings |

### Step 3: Copy Fields from Portal to JSON
For each listing you browse, copy these fields into the JSON schema:

| JSON Field | How to Fill | Example |
|------------|-------------|---------|
| `id` | Sequential: `listing_004`, `listing_005`, ... | `listing_004` |
| `title` | Copy the listing title exactly (or slightly anonymized) | "Bright 1 bed flat near Shoreditch" |
| `description` | Copy the main description text. Keep it raw — red flags live in the wording. | "Modern apartment..." |
| `price_pcm` | Monthly rent in GBP | `1650` |
| `location_postcode` | **Only the outward code** (first part before the space). Never store the full postcode. | `E1` (not `E1 6AN`) |
| `property_type` | `studio`, `flat`, `house`, `maisonette` | `flat` |
| `beds` | Number of bedrooms. Studio = 0 | `1` |
| `baths` | Number of bathrooms | `1` |
| `bills_included` | `true` if description says "bills included" or "all bills inc" | `false` |
| `has_garden` | `true` if garden/balcony/terrace mentioned | `true` |
| `pets_allowed` | `true` if explicitly pet-friendly. Default `false` if not mentioned. | `false` |
| `images_count` | Approximate number of photos shown | `6` |
| `listing_url` | Always `null` in the public repo (privacy) | `null` |
| `source` | Always `"sample"` | `"sample"` |

### Step 4: Intentionally Curate Red Flags
Don't just collect "nice" listings. You need a **balanced dataset** to demonstrate the Red Flag Detector.

Target this approximate distribution across 30 listings:

| Red Flag Category | Target Count | How to Curate |
|-------------------|--------------|---------------|
| **Clean / No flags** | 10–12 | Normal agency listings with clear descriptions, reasonable prices, standard phrasing. |
| **SCAM_RISK** | 3–4 | Look for: pre-viewing deposit demands, "landlord abroad," Western Union, prices 30%+ below market, stock-photo-only listings. OpenRent and Facebook groups are goldmines for these. |
| **HIDDEN_COST_RISK** | 5–6 | Look for: listings that never mention council tax, vague "bills excluded" without specifying which, "service charges may apply," or mention of "admin fees." |
| **DESCRIPTION_MISMATCH** | 4–5 | Look for: "spacious" studio under 300 sq ft, "luxury" at budget price, "recently renovated" with no kitchen/bathroom photos mentioned. |
| **LANDLORD_PRESSURE** | 4–5 | Look for: ALL CAPS, "URGENT," "FIRST COME FIRST SERVE," "many enquiries," "available immediately, must move in this weekend." Spareroom is full of these. |

**Important**: A single listing can have **multiple flags**. That's even better for testing.

---

## Red Flag Curation Examples

### SCAM_RISK Example
```json
{
  "id": "listing_010",
  "title": "Beautiful Studio Flat - £950pcm",
  "description": "I am the landlord but currently working overseas. If you are interested, please send the deposit and first month rent to secure the property. I will post the keys once payment is confirmed. No time wasters.",
  "price_pcm": 950,
  "location_postcode": "W1D",
  "property_type": "studio",
  "beds": 0,
  "baths": 1,
  "bills_included": false,
  "has_garden": false,
  "pets_allowed": false,
  "images_count": 3,
  "listing_url": null,
  "source": "sample"
}
```

### HIDDEN_COST_RISK Example
```json
{
  "id": "listing_011",
  "title": "1 Bedroom Flat in Camden",
  "description": "Lovely one bedroom flat in a great location. Close to Camden Town station. Available now. Rent excludes bills. Professional tenants only.",
  "price_pcm": 1700,
  "location_postcode": "NW1",
  "property_type": "flat",
  "beds": 1,
  "baths": 1,
  "bills_included": false,
  "has_garden": false,
  "pets_allowed": false,
  "images_count": 5,
  "listing_url": null,
  "source": "sample"
}
```
*Why it's flagged: No mention of council tax band. "Rent excludes bills" without specifying which bills.*

### LANDLORD_PRESSURE Example
```json
{
  "id": "listing_012",
  "title": "URGENT! DOUBLE ROOM AVAILABLE IMMEDIATELY!!",
  "description": "FIRST COME FIRST SERVE!! Amazing double room in Stratford. Already had 20 enquiries today. You MUST view today and move in by this weekend or I will give it to someone else. Call me NOW!!!",
  "price_pcm": 850,
  "location_postcode": "E15",
  "property_type": "flat",
  "beds": 1,
  "baths": 1,
  "bills_included": true,
  "has_garden": false,
  "pets_allowed": false,
  "images_count": 2,
  "listing_url": null,
  "source": "sample"
}
```

---

## Anonymization Rules

1. **Never store full postcodes**. Use only the outward code (e.g., `SE14`, `W1D`).
2. **Never store exact street addresses**. If the title says "2 bed on Brockley Road," change it to "2 bed flat in Brockley area."
3. **Never store real listing URLs** in the public repo. Keep them in a private note if needed.
4. **Never store landlord/agent contact details**.
5. **Photos**: Do not download or include images in the repo. Just note `images_count`.

---

## Efficiency Tips

1. **Batch by borough**: Spend 20 minutes on Rightmove filtering for one borough, collect 4–5 listings, then move to the next borough. This is faster than bouncing around.
2. **Use a scratchpad**: Open a temporary text file or spreadsheet while browsing. Copy-paste raw listing data there, then batch-convert to JSON at the end.
3. **Use JSON validation**: Before committing, run your `sample_listings.json` through a JSON linter (VS Code does this automatically). One missing comma breaks the whole app.
4. **Quality over quantity**: 30 well-curated listings with clear red flags is infinitely better than 50 generic ones.

---

## Recommended Minimum Starter Set (13 listings)

If you're pressed for time, aim for this minimum viable dataset before moving on to coding:

| ID | Borough | Price | Beds | Primary Flag | Purpose |
|----|---------|-------|------|--------------|---------|
| 001 | Lewisham | £1,750 | 2 | None (baseline) | Normal listing |
| 002 | Lewisham | £1,450 | 1 | None (baseline) | Normal listing with garden |
| 003 | Westminster | £900 | 0 | SCAM | Classic scam pattern |
| 004 | Tower Hamlets | £1,600 | 1 | HIDDEN_COST | No council tax mention |
| 005 | Hackney | £1,950 | 2 | LANDLORD_PRESSURE | Urgency tactics |
| 006 | Islington | £2,200 | 2 | DESCRIPTION_MISMATCH | "Luxury" at mid price |
| 007 | Camden | £1,700 | 1 | HIDDEN_COST | Vague bills |
| 008 | Wandsworth | £1,850 | 2 | None (baseline) | Standard 2-bed |
| 009 | Southwark | £2,400 | 2 | HIDDEN_COST | Service charges vague |
| 010 | Westminster | £950 | 0 | SCAM | Overseas landlord |
| 011 | Newham | £1,300 | 1 | LANDLORD_PRESSURE | Immediate move-in pressure |
| 012 | Lambeth | £1,550 | 1 | None (baseline) | Student-friendly area |
| 013 | Brent | £1,100 | 0 | DESCRIPTION_MISMATCH | "Spacious" studio |

This gives you **4 clean listings**, **2 scams**, **3 hidden costs**, **2 description mismatches**, and **2 pressure tactics** — enough to test and demo every feature.
