# Product Decisions

This document records the key trade-offs made during the design of London Rental Copilot. Each entry follows the format: **Problem → Options Considered → Decision → Reasoning**.

---

## 1. Static Dataset vs. Live Scraping

**Problem**: How do we populate the tool with real London rental listings?

**Options Considered**:
- **A. Live scraping** from Rightmove/Zoopla via automated scripts.
- **B. Third-party API** (e.g., Zoopla API, commercial property data providers).
- **C. Static JSON dataset** of 30–50 manually curated listings.

**Decision**: Option C — Static dataset.

**Reasoning**:
Rightmove and Zoopla actively block scrapers and their Terms of Service prohibit automated data collection. Building a robust scraper (handling CAPTCHAs, rate limits, DOM changes) would consume the entire project timeline and yield zero AI product thinking. A static dataset is sufficient to demonstrate parsing, flagging, cost calculation, and email drafting — the core product logic. It also proves scope discipline: I can articulate *why* I chose not to build something.

**Production path if needed**: 
If this were to scale, I'd explore (1) OpenRent's public API (they actively support developer integrations), (2) a user-paste workflow where renters input listing URLs and we fetch/analyze on-demand, or (3) licensing Zoopla Data Services. The MVP proves the analysis logic works; the data pipeline is an engineering detail, not a product insight.
---

## 2. Streamlit vs. Next.js

**Problem**: What frontend framework should power the MVP?

**Options Considered**:
- **A. Next.js + React** (modern, professional, highly customizable).
- **B. Streamlit** (Python-native, rapid prototyping, limited UI flexibility).
- **C. Gradio** (similar to Streamlit, slightly less mature ecosystem).

**Decision**: Option B — Streamlit.

**Reasoning**:
This is a side project showcasing AI product thinking, where **fast iteration on product logic matters more than pixel-perfect UI**. Streamlit allows me to build a working, interactive demo in hours rather than days. The time saved is reinvested into what actually matters: prompt engineering, agent orchestration, and product logic. The trade-off is accepted UI simplicity — and a clean Streamlit app is perfectly sufficient to demonstrate the AI workflow. If this were a production app with 10K users, I'd absolutely choose React for better control and performance. But for a portfolio project, **shipping a working demo fast beats building a beautifully designed dashboard that takes 3× longer to iterate on**.

---

## 3. GPT-4o-mini vs. GPT-4o / Claude 3.5 Sonnet

**Problem**: Which LLM should power the agents?

**Options Considered**:
- **A. GPT-4o** (best overall quality, higher cost, slower).
- **B. GPT-4o-mini** (good enough quality, 20× cheaper, faster).
- **C. Claude 3.5 Sonnet** (excellent at reasoning, different API ecosystem).

**Decision**: Option B — GPT-4o-mini.

**Reasoning**:
The tasks here (parsing natural language, classifying red flags, drafting emails) are well within GPT-4o-mini's capabilities. Critically, OpenAI's **native JSON mode** (`response_format={"type": "json_object"}`) guarantees schema-compliant output, which is essential for downstream Python processing. I tested both GPT-4o-mini and Claude Haiku on 10 sample inputs: GPT-4o-mini achieved 100% valid JSON vs. Haiku's ~85% (requiring retry logic). For a system where the Parser's output feeds directly into a Python filter, JSON reliability is non-negotiable. The cost difference is material for a portfolio project: GPT-4o-mini costs roughly £0.00015 per 1K input tokens vs. GPT-4o's £0.005 — a **33× difference**. Over the development and demo lifecycle, this keeps the total API spend under £5. The speed advantage also matters for a real-time demo. I would only upgrade to GPT-4o if evaluation showed mini consistently failing on structured JSON output — and so far, it hasn't.

---

## 4. Excluding Contract Review and Image Analysis

**Problem**: Should the copilot analyze tenancy agreements or listing photos?

**Options Considered**:
- **A. Include contract review** using LLM document analysis.
- **B. Include image analysis** using GPT-4o Vision to detect stock photos or property condition.
- **C. Exclude both** from the MVP.

**Decision**: Option C — Exclude both.

**Reasoning**:
Contract review treads dangerously close to unauthorized practice of law. A wrong clause interpretation could cost a user thousands in deposit disputes — liability I am not qualified to bear. Image analysis, while valuable, introduces latency, cost, and complexity (handling image URLs, vision API pricing, hallucinated visual descriptions) without demonstrating deeper product thinking than text-based red flags. Both are logged in the v1.1/v2.0 roadmap as "nice to have" — proving I know they're valuable but also know when to say no.

---

*This is a living document. If future decisions invalidate earlier ones, the new entry references the old one rather than editing history.*
