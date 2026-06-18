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

| ID | Input | Expected Output (关键字段) | Actual | Status |
|----|-------|---------------------------|--------|--------|
| T1 | "2 bed, £1,800, pet-friendly, 30 min to Canary Wharf" | `{budget: 1800, beds: 2, pets_allowed: true, commute_target: "Canary Wharf", commute_time_minutes: 30, confidence: "high"}` | `{budget: 1800, beds: 2, pets_allowed: true, commute_target: "Canary Wharf", commute_time_minutes: 30, confidence: "high"}` — Filter: 0 matches (dataset has no 2-bed pet-friendly under £1,800) | ✅ 通过 |
| T2 | "我想住在一个安静的地方，预算1500" | `{budget: 1500, lifestyle_tags: ["quiet"], confidence: "low"}` | `{budget: 1500, beds: null, lifestyle_tags: ["quiet"], confidence: "low"}` — Filter: 5 matches (all listings ≤£1,500, beds not filtered) | ✅ 通过 |
| T3 | "Zone 1, under £2000, no pets" | `{budget: 2000, pets_allowed: false, confidence: "medium"}` | `{budget: 2000, pets_allowed: false, commute_target: "Zone 1", confidence: "medium"}` — Filter: 11 matches (excluded 3 pet-friendly listings; Zone 1 not yet enforced by Filter) | ⚠️ 部分通过 |

---

### Iteration Log

**[2026-05-21] v1.0 Initial Test Run**:
- T1 (英文标准输入): Parser 正确提取 budget/ beds/ pets/ commute_target/ commute_time。Filter 0 matches — 符合数据集现实（无 2-bed + pet-friendly + ≤£1,800 房源）。✅
- T2 (中文模糊输入): Parser 正确提取 budget=1500，将"安静"映射为 lifestyle_tags=["quiet"]。beds 未提及 → null，Filter 正确不过滤 beds。✅
- T3 (否定条件): Parser 正确提取 budget=2000, pets_allowed=false。commute_target="Zone 1" 被提取但 **Filter 尚未接入 zone 过滤逻辑**，因此返回了所有非宠物友好的 ≤£2,000 房源（11条）。⚠️ 这是已知功能缺口，不是 Prompt bug。将在 CostCalculator / TfLCommute 集成后补充 zone-based filtering。

**当前状态**: v1.0 Prompt 无需修改，3/3 cases 在 Parser 层面表现正确。下一步迭代将发生在 RedFlagDetector（Day 3）。

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
| RF1 | listing_003 — SCAM studio | `SCAM_RISK (High)`: "Send deposit via bank transfer" | `SCAM_RISK (High)` — evidence 完整引用原文；overall_risk=high | ✅ 通过 |
| RF2 | listing_004 — HIDDEN_COST | `HIDDEN_COST_RISK (Medium)`: "Rent excludes bills" (no council tax) | `HIDDEN_COST_RISK (Medium)` — evidence: "Rent excludes bills" | ✅ 通过 (v1.1) |
| RF3 | listing_006 — DESCRIPTION | `DESCRIPTION_MISMATCH (Low)`: "Truly luxury living" + only 3 images | `HIDDEN_COST_RISK (Medium)` — DESCRIPTION 被模型判定为 common 未 flag | ⚠️ 可接受 |
| RF4 | listing_005 — PRESSURE | `LANDLORD_PRESSURE (Medium)`: "HURRY!", "Don't sleep on this!!!" | `LANDLORD_PRESSURE (Medium)` + `HIDDEN_COST_RISK (Medium)` (bills_included:false) | ✅ 通过 |
| RF5 | listing_008 — Clean | No flags, `overall_risk: "low"` | flags=[], overall_risk="low" | ✅ 通过 |

---

### Iteration Log

**[2026-05-22] v1.0 Test Run — Results Summary**

| Metric | Result |
|--------|--------|
| SCAM Recall (RF1) | 100% ✅ |
| Clean listing High-severity FP | 0 ✅ |
| Clean listing Low/Medium FP | 0 ✅ |
| HIDDEN_COST Recall (RF2) | 0% ❌ |
| DESCRIPTION Recall (RF3) | 100% ✅ |
| PRESSURE Recall (RF4) | 100% ✅ |

**RF1 — listing_003 (SCAM)**:
- Output: `SCAM_RISK (High)`，evidence 完整引用 "Landlord is abroad. Send deposit via bank transfer to secure. Viewing available after payment."
- notes 字段还主动补充了 "Price is significantly below market rate for central London" 和 "Only one image provided" — 属于增值分析，未产生误报。
- ✅ 通过

**RF2 — listing_004 (HIDDEN_COST)** — **False Negative**:
- Description: "Rent excludes bills. Professional tenants preferred."
- Expected: `HIDDEN_COST_RISK (Medium)` 因为 "Rent excludes bills" 未指明具体哪些 bill（未提及 council tax）。
- Actual: flags=[]，overall_risk="low"。
- **根因分析**: Prompt v1.0 的 HIDDEN_COST 触发条件是 "'bills excluded' without specifying which"，但模型没有将 "Rent excludes bills" 识别为等价表达。模型对该短语的解读偏向 "陈述事实" 而非 "隐藏成本风险"。
- **修复方向 (v1.1)**: 在 HIDDEN_COST 定义中增加明确的触发短语列表（"rent excludes bills", "bills not included", "bills excluded"）并补充 few-shot positive example。

**RF3 — listing_006 (DESCRIPTION_MISMATCH)**:
- Output: `DESCRIPTION_MISMATCH (Low)`，evidence "Truly luxury living in the heart of Angel. High-spec finish throughout."
- ✅ 通过

**RF4 — listing_005 (LANDLORD_PRESSURE)**:
- Output: `LANDLORD_PRESSURE (Medium)`，evidence 完整覆盖 "HURRY!...Don't sleep on this!!!"
- 注意: 计划表中 Expected severity 原为 High，但 Prompt 定义 LANDLORD_PRESSURE 为 Medium。实际输出 Medium 与 Prompt 一致，计划表已修正。
- ✅ 通过

**RF5 — listing_008 (Clean)**:
- Output: flags=[], overall_risk="low"。无任何误报。
- ✅ 通过

---

### v1.1 (2026-05-22) — HIDDEN_COST False Negative Fix

**变更点**:
在 `RedFlagDetector.SYSTEM_PROMPT` 的 **HIDDEN_COST_RISK** 定义中，将触发条件从笼统描述改为更明确的短语列表，并增加 few-shot example。

**修改后的 HIDDEN_COST_RISK 段落**:
```
2. HIDDEN_COST_RISK (Medium severity)
   - Triggers: "rent excludes bills" / "bills not included" / "bills excluded" WITHOUT specifying which (gas, electricity, water, council tax); vague service charges; "admin fees" mentioned; council tax not mentioned when rent excludes bills.
   - Do NOT flag if listing explicitly states council tax band, says "all bills included", or lists specific excluded bills (e.g., "water included, gas and electricity excluded").
   - Example (flag): "Rent excludes bills" → HIDDEN_COST_RISK because renter cannot estimate total monthly outlay.
   - Example (do NOT flag): "Water rates included" + other bills not mentioned → normal partial disclosure, do not flag.
```

**Rationale**: 模型在 v1.0 中对 "Rent excludes bills" 的语义敏感度不足。通过显式列出触发短语并提供一个正例，降低模型对该表达的遗漏率，同时保留 negative example 防止对 "Water rates included" 等正常披露的误报。

**v1.1 实际测试结果**:

| Metric | v1.0 | v1.1 |
|--------|------|------|
| SCAM Recall (RF1) | 100% ✅ | 100% ✅ |
| HIDDEN_COST Recall (RF2) | 0% ❌ | 100% ✅ |
| DESCRIPTION Recall (RF3) | 100% ✅ | 0% ⚠️ |
| PRESSURE Recall (RF4) | 100% ✅ | 100% ✅ |
| Clean FP (RF5) | 0 ✅ | 0 ✅ |

**RF2 — listing_004 (HIDDEN_COST)**:
- Output: `HIDDEN_COST_RISK (Medium)`，evidence: "Rent excludes bills"。✅ 修复成功。
- notes 还自我修正了 "'Professional tenants preferred' is a common preference and not a pressure tactic" — 体现 conservative 原则。

**RF3 — listing_006 (DESCRIPTION_MISMATCH)** — **新出现的 False Negative**:
- v1.0 输出过 `DESCRIPTION_MISMATCH (Low)`，v1.1 输出变成了 `HIDDEN_COST_RISK (Medium)`（依据 "Bills not included. Council tax applies."），DESCRIPTION 被遗漏。
- **根因**: 模型在单次分析中倾向于聚焦最强 flag。v1.1 强化了 HIDDEN_COST 的触发条件后，模型判定 "Bills not included + Council tax applies" 为 Medium，同时 notes 中说明 "'luxury' and 'high-spec' ... is common and not flagged as a mismatch"。
- **评估**: 属于可接受的 trade-off。验收标准允许 DESCRIPTION False Negative ≤ 1。从产品经理角度，Medium 的 HIDDEN_COST 比 Low 的 DESCRIPTION_MISMATCH 对用户决策价值更高。

**RF4 — listing_005 (PRESSURE)**:
- 保留了 `LANDLORD_PRESSURE (Medium)` ✅
- **新增**: 同时输出了 `HIDDEN_COST_RISK (Medium)`，evidence 是 `bills_included: false`（来自 JSON 结构化字段，而非 description 文本）。
- **评估**: 严格来说违背了 "Only flag if there is textual evidence in the listing" 规则，但 `bills_included` 本身也是 listing 数据的一部分，且该 listing 确实没有披露 bill 详情。未影响整体风险等级（仍为 medium），不视为严重误报。

**结论**: v1.1 成功修复了 HIDDEN_COST 的零容忍 False Negative，代价是 1 个 DESCRIPTION 的遗漏（在容忍范围内）。当前 Prompt 状态稳定，无需进一步迭代。

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
| ID1 | listing_004 (HIDDEN_COST flagged) | young professional, no pets, move-in 1st July | 邮件正文包含对 council tax 的**明确疑问句**（如 "Could you please confirm the council tax band?" / "What is the monthly council tax?"），不能只是陈述句提及 council tax |
| ID2 | listing_012 (clean, pets allowed) | student, has cat, move-in 1st July | 1) 正文包含 "student" 和 "council tax exemption" 或 "exempt from council tax"；2) 正文包含 "pet" / "cat" 和 "responsible" / "well-trained" 等词；3) 不提及 council tax band 疑问（因为 listing 没有 HIDDEN_COST flag） |
| ID3 | listing_008 (clean) | young professional, no pets | 1) 正文**不包含** council tax 相关疑问；2) 正文**不包含** pet 相关内容；3) tone concise professional，150-200 词；4) 有明确的 viewing availability proposal |

**验收标准细化**:
- "询问 council tax band" = 邮件中出现针对 council tax 的疑问句（以 ? 结尾且包含 "council tax" 关键词）。仅陈述 "I noted the rent excludes bills" 不算通过。
- "提及 council tax exemption" = 邮件中出现 "exempt" / "exemption" + "council tax" 关键词组合。
- "无额外问题" = 邮件中不出现与 listing 已知信息无关的额外询问（如 council tax band, pet policy 等）。

---

### Iteration Log

**[2026-05-22] v1.0 Test Run — OpenAI API (gpt-4o-mini)**

| Metric | Result |
|--------|--------|
| ID1: HIDDEN_COST → council tax question | ✅ Pass |
| ID2: student → exemption mentioned | ✅ Pass (after adding persona hint) |
| ID2: pet → responsible pet owner | ✅ Pass |
| ID3: clean → no council tax question | ✅ Pass (after filtering missing_info from context) |
| ID3: tone concise professional | ✅ Pass |
| All drafts 150-200 words | ✅ Pass |

**ID1 — listing_004 (HIDDEN_COST) + young professional**:
- Output: Draft includes explicit question "could you provide information regarding the council tax band for the property, as well as any additional service charges that may apply."
- ✅ Pass

**ID2 — listing_012 (clean) + student + pets**:
- First attempt: Model mentioned "student" and "pet" but omitted "council tax exemption".
- **Fix**: Added persona hint in `_build_context`: `"(student: mention council tax exemption eligibility)"`.
- Second attempt: "I am a full-time student and may be eligible for council tax exemption, which is an important consideration for me."
- ✅ Pass

**ID3 — listing_008 (clean) + young professional**:
- First attempt: Model asked about council tax despite no red flags. Root cause: `missing_info` from RedFlagDetector contained "Council tax information", which the model treated as a trigger.
- **Fix**: Filtered `missing_info` and `notes` from the context passed to InquiryDrafter. Added explicit rule: "If no red flags are detected, do NOT ask about council tax or service charges."
- Second attempt: Concise standard email with only viewing request. No council tax question.
- ✅ Pass

**RedFlagDetector issue discovered during InquiryDrafter testing**:
- After switching from Deepseek to OpenAI (gpt-4o-mini), `listing_008` and `listing_012` (both clean) were falsely flagged with `HIDDEN_COST_RISK` because the model used the structured field `bills_included: false` as implicit evidence.
- **Fix**: Added `_STRUCTURED_FIELDS_TO_EXCLUDE` in `redflag_detector.py` to filter out `bills_included`, `pets_allowed`, `has_garden`, etc. from the LLM context. This forces the model to rely solely on textual evidence in the title and description.
- Post-fix verification: `listing_003` (SCAM) still flagged correctly; `listing_008` and `listing_012` returned clean.
- ✅ Fixed
