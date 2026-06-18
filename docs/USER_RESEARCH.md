# User Research — London Rental Copilot

## Research Goal
Validate that the pain points we are solving are real, frequent, and severe enough to justify an AI-powered solution.

## Methodology
- **Self-ethnography**: I am actively searching for a flat in London, so I documented my own frustrations over a 2-week period.
- **Peer interviews**: 3 informal interviews with friends/colleagues who moved to London in the last 12 months.
- **Secondary research**: Reddit threads (r/london, r/london_homes), Spareroom forums, and Trustpilot reviews of major portals.

---

## Key Findings

### Finding 1: Discovery is Fragmented and Exhausting
> "I had 8 tabs open every night — Rightmove, Zoopla, Spareroom, Facebook, Gumtree. Same listings appear on multiple sites with different prices." — Peer Interviewee A

- Users spend 1–2 hours/day across multiple platforms.
- No single source of truth; favorite lists don't sync.
- **Implication**: Our tool doesn't need to aggregate everything — it needs to help users make sense of what they've already found.

### Finding 2: "Bills Not Included" is a Trap
> "I found a £1,400 flat and thought I could afford it. Then I realized council tax was £180, commute was £200, and utilities another £150. My actual cost was £1,930." — Personal Experience

- Most portals only show rent.
- First-time London renters severely underestimate council tax variation by borough.
- **Implication**: True Cost Calculator must be front-and-center, not buried in a detail page.

### Finding 3: Scams are Common at the Lower End
> "I almost sent a deposit to a 'landlord in Dubai' for a flat that didn't exist. The photos were from a hotel." — Peer Interviewee B

- Pre-viewing deposit requests are universally recognized as a red flag by experienced renters, but newcomers often don't know.
- Fake listings often have perfect photos, vague descriptions, and below-market prices.
- **Implication**: Red flag detector should be especially calibrated for obvious scam language, not subtle marketing fluff.

### Finding 4: Commute Anxiety is Real
> "I found a nice place in Croydon. Google Maps said 25 minutes to London Bridge. What it didn't show was that the train only ran every 20 minutes and was packed by the time it reached me." — Peer Interviewee C

- Door-to-door time ≠ listed train time.
- Frequency and reliability matter as much as duration.
- **Implication**: In v2, integrate TfL API for real-time frequency data. For MVP, acknowledge limitations honestly.

### Finding 5: People Don't Know What They Don't Know
> "I didn't know what 'Zone 2' meant until after I moved. I just knew I wanted to be 'close to central.'" — Peer Interviewee A

- Many renters (especially international) lack mental models of London's geography.
- They express needs in terms of workplaces, vibes, or landmarks, not postcodes.
- **Implication**: Natural language input + zone suggestions is a killer feature for newcomers.

---

## Personas

### Primary: The Relocated Professional
- **Age**: 24–30
- **Background**: Moved to London for first/second job, likely from abroad or another UK city.
- **Tech comfort**: High. Uses apps for everything.
- **Budget**: £1,400–£2,200/month (solo or flatshare).
- **Pain**: Overwhelmed by choice, doesn't know neighborhoods, afraid of hidden costs.
- **Goal**: Find a safe, convenient flat within 3 weeks without getting scammed.

### Secondary: The Internal Mover
- **Age**: 27–35
- **Background**: Already lives in London, changing jobs or relationship status.
- **Tech comfort**: High, but skeptical of gimmicky apps.
- **Budget**: £1,800–£2,800/month.
- **Pain**: Knows the market but wants to optimize trade-offs (bigger space vs. shorter commute).
- **Goal**: Make an analytically sound decision, not an emotional one.

---

## Design Implications

1. **Simplicity over comprehensiveness**: Users are already overwhelmed. Adding more data sources without synthesis makes it worse.
2. **Trust through transparency**: Every AI suggestion must show its work. Hidden algorithms feel like black boxes in high-stakes decisions.
3. **Progressive disclosure**: Start with the natural language input (low friction). Reveal detailed cost breakdowns and red flags only after initial interest.
4. **Mobile-first viewing, desktop-first analysis**: People browse listings on phones during commutes, but do serious comparison on laptops at home. MVP targets desktop analysis use case.

---

## Open Questions for Future Research

1. Would users trust an AI-generated "fair market price" estimate for a listing?
2. How much do tenants value landlord/agent review scores? (OpenRent has these; Rightmove doesn't.)
3. Would a "saved search alert" feature be valuable, or do users prefer manual browsing?
4. How important is school catchment area data for our target demographic? (Probably low for v1, but critical for family-focused v2.)
