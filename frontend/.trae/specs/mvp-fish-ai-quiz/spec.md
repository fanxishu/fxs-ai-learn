# 《智能 AI 闯关学习小程序》MVP 需求规格说明书 (spec.md)

## 1. 背景 / 问题陈述

产品目标：构建一个**"把任意输入知识点迅速转成闯关问答"**的 AI 学习工具，通过一句话输入 → AI 生成题库 → 逐题即时讲解 → 复盘报告分享 的极简闭环，解决"学习枯燥 + 知识不成体系 + 无法立刻检验学习效果"三大痛点。

### 用户画像

- 单人独立开发者（你）：负责产品、代码、设计、AI Prompt 全链路
- 使用场景：通勤、碎片时间的单人闯关学习；MVP 期无账号系统，微信小程序纯本地会话 + 后端无状态接口

### 非目标（Out of Scope — MVP 明确不做）

1. ❌ 微信登录 / 用户账号 / 数据库持久化（MVP 后再做）
2. ❌ PDF/Word/网页/视频/多格式解析（仅一句话输入）
3. ❌ 联网搜索、RAG 私有知识库、向量数据库
4. ❌ 社交 PK、排行榜、好友邀请裂变
5. ❌ 多模态（图片/语音/数字人）
6. ❌ 支付链路、商业化 VIP
7. ❌ 重型 UI 库（NutUI/Taroify 首版不引，自定义轻量组件）

---

## 2. 功能需求（Functional Requirements）

### FR-01 首页输入模块（P0）

用户在小程序主页输入一个想学的知识主题或一句话 → 点击"开始生成题目"。

- 输入组件：Taro `<Textarea>`，最小高度 72px，placeholder 示例文案对齐 Copilot 原型
- 输入长度约束：**5 ≤ 字数 ≤ 500**（≤ 5 时按钮禁用并给轻提示；>500 截断并提示）
- 空值与仅空白：按钮禁用
- 按钮：主 CTA 橙 `linear-gradient(180deg, #ff944f, #ff6f27)`，最小 46px 高，全宽最大 220px 居中
- 点击按钮 → 先本地校验 → 调用后端 `POST /api/v1/quiz/generate` → 进入 Loading / 闯关页状态

参考 UI：[01-core-flow.html](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/docs/Copilot%E7%94%9F%E6%88%90%E7%9A%84%E5%8E%9F%E5%9E%8B%E5%9B%BE/01-core-flow.html) 屏幕 1

---

### FR-02 AI 生成题库（P0）

后端接收用户输入文本 → 敏感词 + 长度校验 → 调用 DeepSeek（通过 LangChain + `with_structured_output()`）→ 输出结构化题库。

- 输入：`user_input: string`，`question_count: int = 5`，`difficulty: "easy"|"medium"|"hard"|"mixed" = "mixed"`
- 题量控制：**3-5 题**（MVP 默认 5 题：单选 3 + 多选 1 + 判断 1，对齐方案设计 §8.2）
- 题型枚举：`single | multiple | judge`
- 返回字段对齐方案设计 §8.3：`quiz_id` / `title` / `summary` / `questions[]`（含 `id, type, stem, options[{key,text}], answer[], explanation, knowledge_point, difficulty`）
- **五级兜底**（对齐方案设计 §7.4）：空响应检查 → 结构化输出映射 → 字段完整性校验 → 自动重试 1-2 次（切换保守 Prompt v2）→ 仍失败返回"生成失败，请重试"的标准化错误响应
- 敏感词：MVP 先做最小版 100 词黑名单（政治色情暴力）

---

### FR-03 闯关答题 + 即时讲解（P0）

前端渲染题库，用户逐题作答，答题后立刻展示正确答案 + 详细讲解。

- 页面路由：`pages/quiz/index`（单页承载全流程：答题中 / 已提交 / 下一题状态机）
- UI 元素对齐 Copilot 原型屏幕 2：
  - 顶部状态栏：`第 X/Y 题`、金币、返回「X」关闭按钮
  - 进度条 `.quiz-progress .track`：8px 高圆角轨道 + 线性渐变填充
  - 题干 `.quiz-title`：24-30px 粗体
  - 选项 `.option`：52px 高、16px 圆角、橙米色背景
  - 选中后正确态 `.option.right`（绿 `#2e9e71` + check SVG）/ 错误态（红）
  - 即时结果条 `.result-tip`：答对 +10 金币 + 解析 `.explain-box`
  - 底部按钮组 `.next`：「上一题」灰白 + 「继续 →」橙米
- 本地比对答案，记录答题行为到 zustand store / 页面 state：
  - `question_id`、`user_answer`、`is_correct`、`time_spent_ms`、`timestamp`
- 进度条随已答数推进；支持返回上一题（只读不可改）

参考 UI：[01-core-flow.html](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/docs/Copilot%E7%94%9F%E6%88%90%E7%9A%84%E5%8E%9F%E5%9E%8B%E5%9B%BE/01-core-flow.html) 屏幕 2

---

### FR-04 复盘报告生成 + 展示（P0）

用户答完全部题目 → 前端提交 `quiz_id + answer_records[]` → 后端生成本地统计 + AI 结构化复盘 → 前端渲染报告。

- 后端统计模块：正确率百分、答对/答错数、按知识点聚合掌握度
- AI 报告链（对齐方案设计 §8.6）字段：
  - `accuracy`(0-100 int) / `mastered_points[]` / `weak_points[]` / `three_line_summary[3]` / `advice[1-3]` / `share_quote`(1句分享金句)
- 前端渲染对齐 Copilot 原型屏幕 3：
  - 橙渐变顶部 + 2 个胶囊 chip「掌握度 +1」「错题 -2」
  - `conic-gradient` 环形掌握度进度饼图（88px） + 8px 条形掌握度
  - 「最该补的 2 点」卡片
  - 底部：3 句总结、下一步建议、金句
- 分享按钮：MVP 先到「生成海报占位」（Canvas 拼接能力可在第二轮补）

参考 UI：[01-core-flow.html](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/docs/Copilot%E7%94%9F%E6%88%90%E7%9A%84%E5%8E%9F%E5%9E%8B%E5%9B%BE/01-core-flow.html) 屏幕 3

---

### FR-05 全局 UI 设计令牌对齐（P0）

严格采用 Copilot 原型 **03-design-system-board.html** 的 Design Tokens，不使用 Claude 原型的阿衰红黄配色：

| 令牌 | 值 | 用途 |
|---|---|---|
| `--orange` | `#ff7a2f` | 主色 / 主按钮 / 进度 / CTA |
| `--orange-soft` | `#fff1e6` | 辅助软底 / 激活 Tab |
| `--blue` | `#4e9fff` | 信息 / 次级路径 |
| `--green` | `#2e9e71` | 答对 / 正向 |
| `--red` | `#ff6f5d` | 答错 / 风险 |
| `--text` | `#1f2d37` | 主文字 |
| `--muted` | `#6c7b87` | 次文字 |
| `--bg` | `#f6f4ef` | 全局底（暖米白） |
| `--radius-lg` | `22px` / `--radius-xl` `34px` | 圆角 |
| 字体 | `Noto Sans SC + Plus Jakarta Sans` | 字体（Google Fonts + 小程序回退系统默认） |
| 触控区 | min-height/width ≥ 44px | 对齐 UX 军规 Priority 2 |

参考 UI：[03-design-system-board.html](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/docs/Copilot%E7%94%9F%E6%88%90%E7%9A%84%E5%8E%9F%E5%9E%8B%E5%9B%BE/03-design-system-board.html)

---

## 3. 非功能需求（Non-Functional Requirements）

### NFR-01 技术栈约束（硬约束）

| 层 | 选型 | 版本建议 |
|---|---|---|
| 前端框架 | Taro 4.x + React 18 + TypeScript | `@tarojs/taro ^4.0`，`react ^18.2`，`typescript ^5` |
| 前端构建 | Webpack 5 + Sass（CSS Modules） | 对齐方案设计 §3.10 |
| 前端状态 | Zustand `^4.4`（轻量） | 不引入 Redux/MobX |
| 前端请求 | 基于 `Taro.request` 统一封装 `src/api/request.ts` | 超时 35s，base_url 通过 env 切换 |
| 后端 Web | FastAPI + Python 3.11+ | Uvicorn 启动 |
| 后端校验 | Pydantic v2 | 100% 入参出参类型化 |
| AI 编排 | LangChain + langchain-openai | ChatPromptTemplate + `with_structured_output(Pydantic)` |
| AI 模型 | DeepSeek `deepseek-chat` | base_url = https://api.deepseek.com，走环境变量 `DEEPSEEK_API_KEY` |
| 测试 | 后端 pytest + 前端单测 vitest（可选项：小程序端 e2e 不强制） | TDD：后端必须先写测试后写实现 |

### NFR-02 可靠性 / 稳定性

- API 响应：**生成题目接口 p95 ≤ 30s**；超时或失败返回标准错误码 `AI_GENERATE_FAILED = 5001`
- 题目返回的 JSON 结构**必须 100% 通过 Pydantic v2 校验**，任何字段缺失/类型错误都不会漏到前端
- 小程序前端：网络失败 → `Taro.showToast` + 重试按钮；不会白屏

### NFR-03 可访问性 / 可用性

- 关键按钮 `min-height ≥ 44px`（ux Priority 2）
- 颜色对比度：主文字 `#1f2d37` on `#fff` 对比度 ≥ 4.5:1
- `prefers-reduced-motion` 时关闭 canvas 动画（对齐 Copilot 原型）
- 移动端 safe-area：Tab Bar 页 `padding-bottom: calc(env(safe-area-inset-bottom) + 84px)`

### NFR-04 工程化与 TDD

- 后端：**先写 pytest 用例再写代码**；核心模块（quiz_service / scoring_service / quiz_chain / report_chain）测试覆盖率 ≥ 75%
- 所有测试必须能本地运行（不需要真实 DeepSeek Key：给 quiz_chain 打 mock 返回 fixture）
- 目录结构严格对齐方案设计 §6.1（`backend/app/` 六分层 + `backend/tests/`）

---

## 4. 约束 / 依赖 / 假设

### 硬性假设
1. 用户机器已安装 Python 3.11+、Node.js ≥ 18、pnpm 或 npm
2. 已具备有效 `DEEPSEEK_API_KEY`（写入 `backend/.env`）；若无，可用 Mock 模式跑通全链路
3. 微信小程序 AppID（已获取或可用测试号）
4. MVP 数据**不持久化到 MySQL/Postgres**：只存本地内存 + 会话级别
5. MVP 无用户系统，`quiz_id` 由后端 `uuid4()` 生成，前端保存后传回来生成报告

### 外部依赖
- DeepSeek API（主）：`https://api.deepseek.com/v1`
- Taro 4.x 官方脚手架（React + TS 默认模板）
- FastAPI / Uvicorn / Pydantic-settings / python-dotenv
- pytest / pytest-asyncio / httpx（ASGI 测后端）

---

## 5. 开放问题（Open Questions）

> ⚠️ **需要用户人工确认才能 Implement，在你回复前我先暂停**

1. **OQ-1 前端包管理器**：`pnpm`（推荐） / `npm` / `yarn`？
2. **OQ-2 前端初始化策略**：直接在项目根目录 `taro init frontend` 建子目录，还是把整个 `fxs-ai-learn` 项目根重新改造为 monorepo（backend/ + frontend/ 并列）？我推荐前者（最小侵入，不影响 docs/.trae 目录）
3. **OQ-3 DEEPSEEK_API_KEY 缺失时的 Mock 策略**：我在 AI 链里加一个 `USE_MOCK_LLM=true` env 开关，自动返回固定 fixture 题库和报告，让你本地**无 Key 也能全链路跑通**——同意吗？
4. **OQ-4 海报分享占位**：MVP 报告页的「生成海报」按钮，我做成：①点击弹出 Toast："分享海报功能即将上线"（占位）还是 ②实现一个简化版静态 Canvas 拼接？

---

## 6. 验收标准（Acceptance Criteria）

> ⚠️ **每项 AC 必须在 Implement 阶段完成并提供证据，在 Review 阶段独立复核。**

| ID | 类型 | 描述 | 通过判定 |
|---|---|---|---|
| AC-01 | rule | **前端脚手架建立 + 3 个路由页**：`pages/home/index`(首页输入)、`pages/quiz/index`(闯关)、`pages/report/index`(报告)、`pages/loading/index`(生成中) 可 `npm run dev:weapp` 编译通过 | 微信开发者工具打开 dist/ 无报错；4 个路由 URL 可切换 |
| AC-02 | rule | **全局 Design Tokens 生效**：`--orange: #ff7a2f` 等 8 项令牌映射到 CSS/SCSS 变量；主按钮 `.btn-primary`、软按钮、输入框、卡片、进度条、饼图、chip 标签组件样式与 03-design-system-board.html 视觉对齐偏差 ≤ 5% | 截图对比 6 个组件像素 diff 不超限 |
| AC-03 | rule | **首页输入交互**：输入字数 5-500 → 按钮启用；<5 或 >500 → 提示；空提交无法触发；提交中按钮 loading 态禁用 | 自动化用例覆盖 4 条边界 |
| AC-04 | rule | **后端 `POST /api/v1/quiz/generate`** 接口 OpenAPI 文档存在；返回字段 `quiz_id/title/summary/questions[type/single/multiple/judge]` 全部满足 Pydantic 校验；3-5 题、单选≥2、多选≥1、判断≥1 | pytest 10+ 条用例全绿 |
| AC-05 | rule | **AI 出题链五级兜底**在 pytest 全部模拟通过：空响应/格式错/字段缺/重试1次/终极降级错误码 5001 | Mock 测试覆盖全部 5 分支 |
| AC-06 | rule | **闯关答题**：单题作答后 500ms 内显示正确/错误 + 讲解；答题记录本地数组完整；支持切上一题只读；进度条比例正确 | 人工走查 + 单测 |
| AC-07 | rule | **后端 `POST /api/v1/report/generate`**：正确率计算正确；答题记录映射到掌握点/薄弱点；AI 报告链输出 7 字段全部非空 | pytest 覆盖率 ≥ 80% |
| AC-08 | rule | **报告页渲染**：环形掌握度饼图 + 条形条正确映射正确率；胶囊 chip、最该补的 2 点、三句总结、金句全部非空且来自后端 | 走查 2 组不同答题结果报告 |
| AC-09 | rule | **后端全部 pytest 通过**，至少包含 quiz_api、report_api、prompt_contract 3 个文件；`pytest -v` 0 失败；并能在 `USE_MOCK_LLM=true` 环境无网络全通过 | CI 级别证据 |
| AC-10 | rubric(0-5, ≥4 通过) | **UI 还原度**：Copilot 原型 3 个关键屏幕 vs Taro 小程序 3 页的视觉还原度评分。5=像素级，4=细节一致无偏差，3=布局对小色错，2=结构差很多，0=完全不对 | 截图评分 ≥ 4 星 |
| AC-11 | rule | **接口健康检查** `GET /api/v1/health` 返回 `{"status":"ok","version":"1.0.0"}`，HTTP 200，前后端联调启动脚本在 README | 手动 curl 通过 |
| AC-12 | rubric(0-5, ≥4 通过) | **代码组织质量**：后端分层（api/core/models/services/prompts/llm/utils）职责清晰；前端分层（pages/components/stores/api/utils/styles）无跨层直接 import；文件名符合规范 | 代码评审评分 ≥ 4 |

