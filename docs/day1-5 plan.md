# Plan: London Rental Copilot — Day 1-5 执行计划

## Context
用户希望系统性地完成所有前期准备文档后再进入代码开发。前期准备包括**已有文档的查漏补缺**（PRD、README）和**新增核心文档**（Prompt设计、产品决策、技术规格）。所有文档必须直接服务于"向招聘官证明 AI 产品思维"这一核心目标。

## 调整原则
1. **Portfolio-first**: 每份文档都要回答招聘官的面试问题
2. **Solo dev, short cycle**: 不写多人协作流程
3. **聚焦核心价值**: Prompt 工程能力 > 产品决策思维 > 可运行 Demo
4. **真实 > 完美**: 真实的 2 次 Prompt 迭代 > 编造的 5 次完美迭代

---

## 完整前期文档清单（共5份）

### 1. PRD.md — 查漏补缺（已有，需完善）
**目标**: 消除功能定义上的模糊地带，确保每个 Feature 的核心逻辑清晰。

**待完善项**：
- Success Metrics 具体化（用哪 30 条 listing 测试？）
- Out of Scope 补充生产路径
- Data Strategy 补充采集覆盖策略

### 2. README.md — 亮眼包装（已有，需打磨）
**目标**: 招聘官 3 分钟扫完就能判断"这个人值得面试"。

**待完善项**：
- 项目标题上方补充 hook
- Demo GIF 占位明确录制场景
- What I Learned 补充具体数字
- 底部加招聘导向 CTA

### 3. PRODUCT_DECISIONS.md — 快速产出，面试弹药（新增）
**目标**: PRD 承诺了 "can explain 3 product trade-offs"，面试必追问。

**内容**（每个决策 150-200 字）：
1. 静态数据集 vs. 实时爬取
2. Streamlit vs. Next.js
3. GPT-4o-mini vs. GPT-4o / Claude 3.5 Sonnet
4. 不做合同审查/图片分析

### 4. PROMPT_DESIGN.md — 核心能力证明（新增，最重要）
**目标**: 这是 AI Product 面试的必考题。

**内容范围**（2-3 页）：
- 每个 Agent 的完整 System Prompt
- 每个 Agent 至少 1 个 few-shot example
- Iteration Log（边开发边填充）
- Known Limitations

### 5. TECH_SPEC.md — 技术规格（新增）
**目标**: 让任何开发者（或招聘官）在 5 分钟内理解系统如何运转。

**内容范围**（2 页）：
- System Architecture（Mermaid 图 + 解释）
- Agent Handoff Protocol（I/O schema 表格）
- Key Implementation Details
- Running the App（3-5 行命令）

---

## 明确不做的事

| 不做 | 理由 |
|------|------|
| **DEVELOPMENT.md**（代码规范/Git 流程） | 单人项目，代码注释够用；没有 PR，没有多人协作 |
| **TESTING.md**（独立测试文档） | 现在只有 13 条数据且未标注，写测试规范是空谈；Gold Standard 的使用说明直接放在 PROMPT_DESIGN.md |
| **DEPLOYMENT.md** | Streamlit Cloud 部署只需 3 步，README 一句话足够 |
| **DATA_SCHEMA.md**（独立文档） | PRD 的 Data Strategy 已定义 schema；`sample_listings.json` 文件顶部加注释说明即可 |
| **COMPETITIVE_ANALYSIS.md**（独立文档） | 作为 PRODUCT_DECISIONS.md 的第一个案例背景，不需要单独成文 |
| **详细的异常处理规范** | 这是实现细节，边写代码边在注释里加，不需要提前在 PRD 定义 |

---

## Day 1: 打地基（文档周）

### 上午
- **快速确认 PRD 现状**（15 分钟）
  - 检查 4 个 Feature 的 Acceptance Criteria 是否足够
  - Success Metrics 是否可衡量
  - Out of Scope 是否明确
  
- **写 PRODUCT_DECISIONS.md**（1.5 小时）
  - 3 个核心决策 × 200 字
  - 格式：Context → Options → Decision → Rationale → Consequences
  
- **写 TECH_SPEC.md**（1 小时）
  - Data Flow 图
  - Agent I/O schema（参考 PRD）
  - Running the App

### 下午
- **搭建代码骨架**
  - 创建目录结构：`app/agents/`, `app/utils/`, `data/`
  - 写 `.env.example`, `requirements.txt`
  - 在 `sample_listings.json` 顶部加 schema 注释
  
- **第一次 git commit**: `"chore: initial project structure"`

### 晚上（可选）
- 写 RequirementParser 的函数签名和类型注解
- 这样 Day 2 可以直接开始写 Prompt

### 验收标准
- [ ] PRODUCT_DECISIONS.md 有 3 个决策，每个有清晰的 rationale
- [ ] TECH_SPEC.md 有完整的 Agent I/O schema
- [ ] 代码骨架可运行（`streamlit run app/main.py` 不报错）

---

## Day 2: RequirementParser + Python Filter

### 任务 1：起草 System Prompt（Prompt 先行）

**修改文件**: `docs/PROMPT_DESIGN.md`

**具体动作**:
1. 创建文档框架
2. 写 RequirementParser v1.0 的 System Prompt（300-500 字）
   - 角色定义
   - 输出格式要求（参考 TECH_SPEC 的 Output schema）
   - 边界处理："If budget not mentioned, set to null"
   - **不要写死伦敦知识**（不列举地铁站、borough 特征）
3. 定义 3 个测试 case 的 Expected Output

**验收标准**:
- [ ] System Prompt 完整，可直接复制到代码
- [ ] 有 3 个测试 case 的 Input 和 Expected 定义
- [ ] Prompt 中没有硬编码的伦敦地理知识

---

### 任务 2：实现 Parser 代码

**修改文件**: `app/agents/requirement_parser.py`

**具体动作**:
1. 从 PROMPT_DESIGN.md 复制 v1.0 System Prompt（硬编码字符串）
2. 实现 OpenAI API 调用：
```python
   model="gpt-4o-mini",
   response_format={"type": "json_object"},
   temperature=0.2
```
3. 最小化错误处理（try-except，显示友好错误）
4. 用 3 个测试 case 跑一遍

**验收标准**:
- [ ] 3 个测试 case 至少 2 个通过
- [ ] 失败的 case 已记录到 PROMPT_DESIGN.md
- [ ] API key 缺失时不崩溃

---

### 任务 3：实现 Python Filter

**修改文件**: `app/main.py`

**具体动作**:
1. 在 Streamlit UI 中调用 Parser
2. 实现 `filter_listings(constraints, listings)` 函数：
   - Budget: `price_pcm <= budget`
   - Beds: 精确匹配（不支持 "2+"）
   - Pets: `pets_allowed == true`
   - Garden: `has_garden == true`
3. 展示 matched + excluded 结果

**验收标准**:
- [ ] 输入 "2 bed under £1,800" → 只显示符合条件的 listings
- [ ] 无匹配时显示友好提示

---

### 任务 4：记录迭代

**具体动作**:
1. 如果发现问题，修改 Prompt 为 v1.1
2. 记录迭代日志到 PROMPT_DESIGN.md

---

### 任务 5：交叉验证

**具体动作**:
1. 运行 `streamlit run app/main.py`
2. 走一遍完整 flow
3. git commit: `"feat: add RequirementParser v1.0 + Python Filter"`

---

### TECH_SPEC 同步修改
**由于 MVP 不做区域推荐**，在 TECH_SPEC.md §1 Parser Output schema 中：
```json
{
  ...
  "suggested_zones": [],  // Always empty in v1.0
  ...
}
```

### 不做的事
- ❌ 不在 Parser 里写死伦敦知识
- ❌ 不做区域推荐功能（v1.1 再做）
- ❌ 不支持 "2+ bed" 模糊查询（MVP 只做精确匹配）
- ❌ 不写复杂的错误处理（retry, exponential backoff）
- ❌ 不开始写 RedFlagDetector

### 预计耗时: 4 小时

---

## Day 3: RedFlagDetector

### Context
Day 2 已完成 RequirementParser + Python Filter。Day 3 目标是实现 RedFlagDetector（Critic Agent），这是招聘官面试时最关注的 Agent，因为它直接体现 **Prompt Engineering 的精度控制能力和产品安全意识**。

---

### 任务 1：准备测试数据 + 起草 System Prompt

**修改文件**: 
- `data/sample_listings.json`（可能需要补充）
- `docs/PROMPT_DESIGN.md`

**具体动作**:

#### Step 1: 确认测试集覆盖度
1. 扫描现有 `sample_listings.json` 的 listings
2. 标注每条的预期 flag 类型（建立 Ground Truth）
3. 检查是否覆盖 4 种 flag 类型 + 1 个 clean
4. 如果缺失，手动编辑或新增 listing 补充

#### Step 2: 定义测试 case
创建测试 case 表格：

| Listing ID | Expected Flags | Rationale |
|------------|----------------|-----------|
| listing_003 | SCAM_RISK (High) | "landlord abroad, deposit via Western Union" |
| listing_004 | HIDDEN_COST_RISK (Medium) | No mention of council tax |
| listing_006 | DESCRIPTION_MISMATCH (Low) | "luxury" but < 400 sq ft |
| listing_005 | LANDLORD_PRESSURE (Medium) | "URGENT, act fast" |
| listing_008 | None (clean) | Professional, all fees disclosed |

#### Step 3: 写 v1.0 System Prompt
核心设计原则：
- **Conservative flagging**: 宁可漏报也不乱报高风险
- **Evidence-based**: 每个 flag 必须引用原文
- **4-category taxonomy**: SCAM_RISK, HIDDEN_COST_RISK, DESCRIPTION_MISMATCH, LANDLORD_PRESSURE
- **Severity scoring**: Low / Medium / High

**Prompt 结构建议**:
You are a red flag detector for London rental listings.
Categories:

SCAM_RISK: Pre-viewing deposits, landlord abroad, Western Union
HIDDEN_COST_RISK: Missing council tax, vague charges
DESCRIPTION_MISMATCH: "Spacious" but <350 sq ft
LANDLORD_PRESSURE: All-caps urgency, "act fast"

Severity:

High: Strong evidence, multiple red flags
Medium: Single clear red flag
Low: Borderline/subjective

IMPORTANT - Negative examples (do NOT flag):

"Viewing recommended" (NOT pressure unless + urgency)
"Council tax not included in rent" (disclosure, NOT hidden)
"Available from June 1st" (NOT urgency)

**验收标准**:
- [ ] 测试 case 表格有 5 条，覆盖 4 种 flag + 1 clean
- [ ] System Prompt 包含 4 个 category 定义
- [ ] System Prompt 包含至少 3 个 negative examples

---

### 任务 2：实现 RedFlagDetector 代码

**修改文件**: `app/agents/redflag_detector.py`

**具体动作**:
1. 接入 OpenAI API（不是 Deepseek！）
2. 硬编码 System Prompt
3. 配置：
```python
   model="gpt-4o-mini",
   response_format={"type": "json_object"},
   temperature=0.1  # 比 Parser 更低
```
4. 错误处理：返回 `{"overall_risk": "unknown", "flags": []}`

**验收标准**:
- [ ] 代码可运行，输出符合 TECH_SPEC schema
- [ ] API key 缺失时不崩溃

---

### 任务 3：连接 Streamlit UI

**修改文件**: `app/main.py`

**具体动作**:
1. 在 `tab_flags` 中调用 RedFlagDetector
2. 展示 `overall_risk`（用颜色/emoji：🟢 Low / 🟡 Medium / 🔴 High）
3. 逐个展示 flags（category + severity + evidence + explanation）
4. Clean listing 显示绿色："✅ No red flags detected"
5. SCAM_RISK (High) 时加醒目警告 banner

**验收标准**:
- [ ] UI 能展示完整分析结果
- [ ] Risk 等级有清晰视觉区分

---

### 任务 4：测试 + 记录迭代

**具体动作**:

#### Step 1: 批量测试
1. 用 5 个测试 listings 逐个跑 Detector
2. 记录 Actual Output 到 PROMPT_DESIGN.md

#### Step 2: 检查 False Positive（误报）
- **严格标准**: High-severity 误报 = 0
- **宽松标准**: 允许 Low-severity 误报
- 如果 High-severity 误报：分析触发短语 → 添加 negative example → v1.1

#### Step 3: 检查 False Negative（漏报）
- 对比 Actual vs Expected
- **容忍度**:
  - SCAM_RISK / HIDDEN_COST_RISK 的 FN = 0（零容忍）
  - DESCRIPTION_MISMATCH / LANDLORD_PRESSURE 的 FN ≤ 1（可接受）

#### Step 4: 迭代
- 如果有问题，修改 Prompt 为 v1.1
- 记录迭代日志

**验收标准**:
- [ ] 5 个测试 case 完成，Actual Output 记录到文档
- [ ] High-severity FP = 0
- [ ] SCAM_RISK / HIDDEN_COST_RISK 的 Recall = 100%
- [ ] 如果修改了 Prompt，有完整的 v1.1 记录

---

### 不做的事
- ❌ 不处理图片分析
- ❌ 不做自动屏蔽
- ❌ 不写历史趋势分析
- ❌ 不开始 CostCalculator / ComparisonGenerator
- ❌ 不优化 UI 样式

### 预计耗时: 3.75 小时

---

## Day 4: CostCalculator + InquiryDrafter

### 上午：CostCalculator（Python 纯函数）

**修改文件**: `app/utils/cost_calculator.py`

**具体动作**:
1. 实现确定性计算函数：
```python
   def calculate_true_cost(listing, commute_target):
       rent = listing["price_pcm"]
       
       # Council Tax
       if listing.get("council_tax_band"):
           # 使用精确 band
       else:
           # Band C-D 中点估算
       
       # Commute
       # postcode → borough → zone → travelcard cost
       
       # Utilities
       # 1-bed: £120, 2-bed: £160
       
       return {
           "rent": rent,
           "council_tax": ...,
           "commute": ...,
           "utilities": ...,
           "true_cost": total
       }
```

2. 在 Streamlit UI 展示对比结果

**验收标准**:
- [ ] 手动计算 3 个 listing，与函数输出对比，误差 < £10
- [ ] UI 显示 true cost breakdown

---

### 下午：InquiryDrafter（LLM Agent）

**修改文件**: 
- `docs/PROMPT_DESIGN.md`
- `app/agents/inquiry_drafter.py`

**具体动作**:

#### Step 1: 写 System Prompt
1. 在 PROMPT_DESIGN.md 起草 v1.0 Prompt
2. 核心要求：
   - Tone: Professional yet warm
   - Adaptive logic: 
     - If HIDDEN_COST_RISK → 询问 council tax
     - If persona == "student" → 提 council tax exemption
     - If has_pets → 提前说明 responsible ownership
3. 定义 3 个测试 case

#### Step 2: 实现代码
1. 硬编码 System Prompt
2. 配置：
```python
   model="gpt-4o-mini",
   temperature=0.3  # 略高于 Detector，允许自然变化
```
3. 输入：listing + red_flags + user_profile
4. 输出：email 草稿（string）

#### Step 3: 测试 + 迭代
1. 用 3 个 case 测试 tone 是否合适
2. 检查是否 too formal / too casual
3. 如有问题，修改 Prompt → v1.1

**验收标准**:
- [ ] 3 个测试邮件 tone 合适（professional + warm）
- [ ] Adaptive logic 生效（red flag → 询问 council tax）

---

### git commit
- `"feat: add CostCalculator"`
- `"feat: add InquiryDrafter v1.0"`

### 预计耗时: 4 小时

---

## Day 5: 整合 + 打磨

### 上午：End-to-End 整合

**修改文件**: `app/main.py`

**具体动作**:
1. 在 Streamlit 整合所有 4 个 Tab：
   - Tab 1: Search (Parser + Filter)
   - Tab 2: Red Flags (Detector)
   - Tab 3: Cost Compare (Calculator)
   - Tab 4: Email Draft (Drafter)

2. 走一遍完整 flow：
   - 输入需求 → 看推荐 → 查 red flag → 算成本 → 生成邮件

3. 修复发现的 bug

**验收标准**:
- [ ] 完整 flow 可运行
- [ ] 5 个代表性 query 全部测试通过

---

### 下午：打磨 README

**修改文件**: `README.md`

**具体动作**:
1. 补充 hook：
```markdown
   > 从伦敦租房的血泪史里长出来的 AI 产品实验
```

2. 更新 What I Learned（加具体数字）：
```markdown
   - **Prompt engineering for structured output**: 通过 3 次迭代，将 RedFlagDetector 
     的 precision 从 78% 提升到 92%，同时保持 SCAM_RISK 的 recall = 100%
```

3. 补充 Demo GIF 场景说明（如果还没录制）

4. 底部加 CTA：
```markdown
   正在寻找伦敦的 AI Product 实习机会。如果你也在做 AI 产品或有建议，
   欢迎通过 [LinkedIn/Email] 交流。
```

---

### 交叉检查

**检查清单**:
- [ ] PRD 中的 Feature 描述 = 代码实际实现
- [ ] TECH_SPEC 的 I/O schema = 代码中的 JSON
- [ ] PROMPT_DESIGN 的 Prompt = 代码中的硬编码字符串
- [ ] PRODUCT_DECISIONS 的技术选型 = README 的 Tech Stack
- [ ] 所有文档引用一致（如 TECH_SPEC 说 "Band C-D fallback" = PRD 也这么说）

---

### git commit
- `"docs: polish README for demo"`
- `"chore: final cross-check before v1.0"`

### 预计耗时: 4 小时

---

## 验收标准总结

### 文档完整性
- [ ] 5 份核心文档齐全（PRD, PRODUCT_DECISIONS, TECH_SPEC, PROMPT_DESIGN, README）
- [ ] PROMPT_DESIGN.md 包含 4 个 Agent 的完整 Prompt + 测试记录
- [ ] 每个 Agent 至少有 1 次真实的 Prompt 迭代记录

### 代码可运行性
- [ ] `streamlit run app/main.py` 不报错
- [ ] 4 个 Tab 全部可用
- [ ] 至少 5 个测试 query 跑通

### 产品质量
- [ ] RedFlagDetector: High-severity FP = 0, SCAM Recall = 100%
- [ ] CostCalculator: 手动验证误差 < £10
- [ ] InquiryDrafter: Tone 合适（professional + warm）

### 招聘就绪度
- [ ] README 在 3 分钟内能让招聘官理解核心价值
- [ ] PRODUCT_DECISIONS 能支撑 5 分钟的面试对话
- [ ] PROMPT_DESIGN 能展示真实的迭代过程（不是编的）

---

## 补充说明

### 为什么允许 Low-severity 误报？
这是产品决策：
- 用户看到 "LANDLORD_PRESSURE (Low)" 不会恐慌
- 避免为了 FP=0 而让 Prompt 过于脆弱
- Known False Positives 章节记录所有误报，为 v1.1 优化留空间

### 为什么不做区域推荐？
- 需要实时房价数据，但 MVP 用静态数据
- 推荐逻辑复杂（地铁线路、通勤时间、区域特征），会让 Prompt 膨胀
- Parser + Filter 已经证明了 AI + Python 配合，区域推荐是锦上添花

### 为什么 Day 4-5 时间估算更保守？
- Day 2-3 已建立 Prompt 设计 → 代码实现 → 测试迭代的节奏
- Day 4-5 是整合和打磨，容易遇到意外 bug
- 留有 buffer 时间应对未知问题

---

*This plan is a living document. Adjust execution order if blockers arise, but keep the 5-day minimum scope fixed.*