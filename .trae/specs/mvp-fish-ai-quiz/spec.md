# 鱼皮 AI 闯关学习小程序 MVP - Product Requirements Document (spec.md)

## Overview
- **Summary**: 一个微信生态内的 AI 学习闯关小程序 MVP：用户输入一句话/一段知识点 → 后端调用 DeepSeek AI 自动生成 3~5 道单选+多选+判断闯关题（附深度讲解）→ 用户逐题即时答题对错反馈 + 知识讲解 → 通关后 AI 生成本次学习正确率、掌握薄弱点、三句总结与分享金句的复盘报告，形成"输入→出题→答题→报告"的极简学习闭环。
- **Purpose**: 解决现代学习者"信息过载 + 学习动力不足"的双痛点；把任意非结构化输入知识快速转化成结构化、趣味性的问答游戏闯关；主打"万物皆可 AI 闯关"的产品定位。
- **Target Users**: 职场学习者、在校学生、考试备考者、编程技术学习者等需要碎片化时间快速自测知识点 + 游戏化驱动力的用户群体。

## Goals
1. 跑通一句话输入知识点 → AI 生成 3~5 道题（单选/多选/判断）+ 每题深度讲解 的 MVP 核心链路。
2. 用户逐题作答后**即时**展示正确答案、错误深度讲解、XP/金币奖励反馈。
3. 全部题目完成后生成结构化复盘报告（正确率、掌握知识点、薄弱知识点、三句总结、复习建议、分享金句）。
4. AI 生成题目**连续 10 次结构稳定可直接渲染**，至少 80% 输出质量合格。
5. 前后端联调通过：Taro 4.x 小程序端 + FastAPI 后端 + DeepSeek 大模型三层打通，异常与降级完备。
6. 内容合规三层过滤架构 (前端正则→后端 DFA→AI 输出二次扫描) 全部到位，通过微信小程序审核的前置准备。
7. UI 视觉**严格 1:1 对齐 Copilot 原型图**：主色暖橙 #ff7a2f、米色背景、渐变按钮、圆角阴影等色彩系统与组件 token 完全复现。

## Non-Goals (明确不前置、不纳入 MVP 的范围)
按方案设计 §2.3，保留在后续版本，不纳入 MVP 首轮：
1. 微信授权登录、用户注册、账号体系。
2. MySQL 正式库表设计与复杂持久化。
3. 网页抓取、PDF/Word/视频解析、联网搜索扩展。
4. RAG 私有知识库、向量数据库。
5. 社交 PK、全服排行榜、分享裂变深度玩法（仅保留分享金句海报占位按钮）。
6. 生图、语音、数字人等多模态能力。
7. 复杂商业化功能和支付链路。
8. 多端（百度/支付宝/抖音/QQ 小程序）适配。

## Background & Context (已验证的客观事实与前置决策)
### 已通过 AskUserQuestion 2026-09-26 人工确认的决策：
1. **前端目录命名**：现有 `front-page/` 目录**重命名为 `frontend/`**，严格对齐方案文档 §14.2 目录规范；现有代码（7 页 TSX、10 个组件、状态管理、API 封装、已 build:weapp dist/ 编译成功）**全部保留复用，不推翻从零重写**。
2. **UI 主色调/设计系统**：严格对齐 [01-core-flow.html](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/docs/Copilot生成的原型图/01-core-flow.html) + [03-design-system-board.html](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/docs/Copilot生成的原型图/03-design-system-board.html) → 主色 `#ff7a2f`（暖橙），米色背景 `#f6f4ef` / `#fff6ef`，渐变按钮 `linear-gradient(180deg, #ff944f, #ff6f27)`，圆角 `14/16/22/34px`，阴影 `0 10px 20px rgba(255, 122, 47, 0.24)` 等所有色彩/空间/阴影 token**全部按原型 CSS 变量重写**。
3. **DeepSeek 结构化输出方案**：优先走**已本地验证稳定**的 `response_format=json_object + Pydantic v2 model_validate_json() + 手剥 markdown 代码块容错`（保证 Java 设计模式→Java 5 题 KP=单例/SOLID/多态/开闭/策略正确返回），同时**在代码中保留 with_structured_output(PydanticModel) 的注释备份路径**（未来 DeepSeek 支持 json_schema 时一键切换）。
4. **页面收敛策略**：MVP 核心验收只关注 3 页主链路（`pages/index/index` 首页输入、`pages/quiz/index` 闯关答题、`pages/report/index` 复盘报告）；现有扩展页（history/mine/loading/ + TabBar 3 项）**保留但不验收**（留作后续 Phase 5 扩展使用）。

### 已验证的客观技术事实：
1. DeepSeek API Key 真实有效（Node 直连 `https://api.deepseek.com/v1/chat/completions` 返回 HTTP 200）。
2. DeepSeek 官方**当前不支持 `response_format.type: json_schema`**，仅支持 `json_object`；`with_structured_output(PydanticModel)` 会触发 LangChain 自动请求 json_schema → HTTP 400 `This response_format type is unavailable now` → **已复现并根因定位**。
3. 现有前端 build:weapp 已产出 `dist/`（Webpack 7.63s compiled success，0 errors）。
4. 现有后端 .venv 用 Python 3.14 已重建完成；`/api/v1/health` HTTP 200 `use_mock_llm=false`。
5. Taro 4.x 官方脚手架命令已确认为 `npx @tarojs/cli init frontend`（来自 [Taro GETTING-STARTED 官方文档](https://docs.taro.zone/docs/GETTING-STARTED)）。

## Functional Requirements (FR)
- **FR-1 首页输入模块**：首页仅保留干净的大输入框 + 快捷 Chips + "开始闯关" 主按钮；输入校验（空/过短<2字/过长>2000字/敏感词）即时提示。
- **FR-2 前端敏感词快速拦截**：内置约 100 条高频核心敏感词正则列表；点击"开始闯关"时先本地匹配，命中则 Toast 不发请求。
- **FR-3 生成题目 Loading**：点击开始后前端跳转到 loading/page，loading 文案按 10s→20s→30s 阶梯更新，整体超时 50 秒。
- **FR-4 后端 quiz/generate 接口**：`POST /api/v1/quiz/generate` 返回统一响应 `{code, message, data:{quiz_id, title, summary, questions[]}}`；题量默认 5 题（3 单选 / 1 多选 / 1 判断）。
- **FR-5 题型全覆盖**：每道题 `type in {single, multiple, judge}`，单/多/判断题型前端渲染差异（多选可多选、判断 2 个选项等）。
- **FR-6 每题深度讲解**：每道题必须 `explanation` 字段非空，答完后立刻展开，语言风格通俗适合小程序移动端阅读。
- **FR-7 闯关页答题状态机**：按方案文档 §17.4 实现 `INITIALIZING → READY → SELECTING_OPTION → SUBMITTED → READY / FINISHING` 状态流转。
- **FR-8 即时对错反馈 + XP/金币奖励**：选项点击 → 点确认 → 立即绿色高亮正确 / 红色错误项 → 展开讲解 → 答对 +10 XP + 金币动画 / 答错无 XP。
- **FR-9 进度条与题目计数 UI**：顶部展示"第 x/N 题"进度条 + 当前题 XP/金币累积状态。
- **FR-10 答题记录本地存储**：每道题 `answer_record{question_id, selected_answers[], is_correct, duration_ms}` 实时写入本地 Zustand + `Taro.setStorage`。
- **FR-11 报告页整体流程**：最后一题点击"查看报告" → 先渲染本地统计（正确率、对/错数、XP 金币）→ 非阻塞异步调 `POST /api/v1/report/generate` → 返回 AI 总结后合并渲染。
- **FR-12 复盘报告结构**：`accuracy, mastered_points[], weak_points[], three_line_summary[], advice[], share_quote` 全部字段完整展示。
- **FR-13 分享海报占位**：报告页底部"生成分享海报"按钮（MVP 不做 Canvas 拼接真实图，Toast 提示"功能即将上线"）。
- **FR-14 后端三层内容安全过滤链**：
  1. 前端：输入正则拦截。
  2. 后端 quiz/generate：DFA 敏感词树 `app/utils/content_filter.py` 对 `user_input` 过滤。
  3. 后端输出：对返回的 title/summary/stem/explanation/options.text 所有字段 DFA 二次扫描 + 外链/拒答模式正则兜底。
- **FR-15 统一错误码与降级机制**：错误码区间（1xxx 参数 / 2xxx 鉴权 / 3xxx 内容安全 / 4xxx 业务 / 5xxx AI 服务）；AI 调用失败 5 级兜底（空校验→Pydantic 校验→题量字段→重试1次保守Prompt→fixture 兜底或错误返回）。

## Non-Functional Requirements (NFR)
- **NFR-1 出题性能**：`POST /api/v1/quiz/generate` 端到端 **90 分位 ≤ 45 秒**（含 DeepSeek 调用 + 重试）。
- **NFR-2 出题稳定性**：连续调用 10 次同一主题（如"Java 设计模式"）→ **结构可渲染率 ≥ 90%**，至少 80% 题不跑题、讲解可读性达标。
- **NFR-3 内容安全**：连续输入 5 条典型违规关键词 → **100% 命中 3 层过滤链**，无脏数据返回前端。
- **NFR-4 UI 原型保真度**：截图对比 01-core-flow.html 原型与小程序真机截图 → **核心页面（首页/闯关页/报告页）UI 还原度 ≥ 0.9**（色彩、字体、间距、圆角、按钮渐变匹配）。
- **NFR-5 后端 TDD 覆盖率**：后端工具层 (text_cleaner / content_filter / scoring_service) 单元测试覆盖率 ≥ 85%；Prompt 契约测试 ≥ 5 次连续结构稳定；API 集成测试覆盖 quiz/report 成功/失败/参数校验/内容安全 4 类场景。
- **NFR-6 前端工程约束**：CSS Modules 全部 `@use '@/styles/variables.scss' as *;` 头部；组件导入走 `@/components` 别名；小程序单包体积 ≤ 2MB（MVP 无分包）。
- **NFR-7 异常与空态**：断网、超时、输入违规、AI 返回脏数据等 8 种异常场景**前端不白屏**，均有友好 Toast/错误面板。
- **NFR-8 代码分层方向**：后端严格遵循 `api → service → llm/prompts → models` 单向依赖，禁止反向依赖。

## Constraints
- **技术栈硬约束**：
  - 前端：`Taro 4.x + React 18 + TypeScript + webpack5 + CSS Modules(scss) + Zustand`。
  - 后端：`Python 3.11+ / FastAPI / Pydantic v2 / LangChain + langchain-openai / pytest`。
  - 大模型：`DeepSeek Chat deepseek-chat`，OpenAI 兼容格式 `base_url=https://api.deepseek.com`。
  - 构建命令：前端 `build:weapp = taro build --type weapp` 必须产出 `frontend/dist/`。
- **微信小程序硬约束**：
  - 单包 ≤ 2MB；MVP 禁止重型 UI 库（NutUI/Taroify 不引入，全部自定义轻量组件）。
  - `project.config.json` 必须 `urlCheck=false` 开发态、`miniprogramRoot="dist/"`。
  - 禁止通配符选择器、部分伪类；所有页面走 CSS Modules。
- **MVP 边界硬约束**：方案文档 §2.3 非目标列表内的功能**禁止在本轮开发中实现**。
- **UI 硬约束**：Copilot 原型图 3 份 HTML 是 UI 唯一真值；任何组件的色彩/尺寸/间距不得随意发挥。
- **已确认决策硬约束**：目录名 `frontend/`、DeepSeek JSON 双层兜底、暖橙主色这三项**必须按 AskUserQuestion 用户最终答案执行**。

## Assumptions
1. 用户在本地开发环境运行：后端 8000 端口、前端 HTTPS 反代 8443 端口（小程序/沙箱 HTTPS 页面打 HTTP 后端的 Mixed Content 拦截问题已通过自签反代方案解决）。
2. DeepSeek API Key 已正确写入 `backend/.env` 且账户额度充足。
3. MVP 阶段无数据库，答题记录/题库存储走前端 `Taro.setStorage` + 后端无状态 JSON 响应。
4. 用户验收时：微信开发者工具打开 `frontend/` 根目录（miniprogramRoot 自动指向 dist/），并勾选"不校验合法域名"。
5. 后端 Python `.venv` 已重建并安装 `requirements.txt`，无 DLL/EPERM 跨盘错误。

## Acceptance Criteria (AC)
所有验收标准类型仅能是 `rule`（可观测二元通过条件）或 `rubric`（评分维度）。

### AC-1 端到端一句话出题闭环 (Type: rule)
- **Given**: 本地后端 8000 / HTTPS 反代 8443 启动正常、DeepSeek Key 有效
- **When**: 小程序首页输入"Java 设计模式 单例 观察者 工厂 SOLID 策略" → 点"开始闯关"
- **Then**: 45 秒内进入闯关页，共展示 5 题；题目内容为 Java 设计模式（至少包含单例/SOLID/多态/开闭/策略 5 个知识点 KP）；每题题干+选项非空；讲解文字通俗易懂。
- **Pass Condition**: HTTP 不返回 fallback Python fixture；5 道题 knowledge_point 标签全部命中 Java 设计模式相关关键词。
- **Evidence**: Network 面板 POST /api/v1/quiz/generate data.questions[].knowledge_point 字段截图 + 前端题目截图。

### AC-2 答题即时反馈机制 (Type: rule)
- **Given**: 已进入闯关页、第 1 题为单选题
- **When**: 选错误选项 A → 点确认答案 → 展开讲解 → 点下一题
- **Then**: 错误项红框、正确项绿框；讲解面板展开文字非空；correctCount 不 +1；currentIndex 1→2；进度条更新。
- **Pass Condition**: DOM 类名/样式命中"error"红色和"correct"绿色；Zustand store correctCount 不变。
- **Evidence**: 前端控制台 quizStore state + 屏幕截图。

### AC-3 多选题判断逻辑 (Type: rule)
- **Given**: 某道多选题正确答案为 ["A","C"]
- **When**: 用户选择 ["A","B"]（部分正确但不全）→ 点确认
- **Then**: 判定 is_correct = false；正确答案 A、C 高亮绿；错误 B 高亮红；不获得 XP。
- **Pass Condition**: answer_record.is_correct 为 false。
- **Evidence**: console answer_records[q3].is_correct value.

### AC-4 复盘报告正确率与字段完整性 (Type: rule)
- **Given**: 5 道题答题结束 3 对 2 错
- **When**: 报告页调 /report/generate
- **Then**: 页面显示 accuracy = 60；mastered_points / weak_points 均非空数组；three_line_summary 3 条字符串；share_quote 一句中文金句非空。
- **Pass Condition**: 以上所有字段存在，类型匹配方案文档 §10.4 Report JSON Schema。
- **Evidence**: report 接口响应 + 报告页渲染截图。

### AC-5 5 级 AI 失败兜底链路 (Type: rule)
- **Given**: 注入一个无效的 DEEPSEEK_API_KEY 触发全链路失败
- **When**: 调 /quiz/generate
- **Then**: 返回 code=5003（DEEPSEEK_RETRY_EXHAUSTED）或返回 fixture 兜底 fixture JSON（结构合法但不直接白屏）；前端 Toast "AI 出题失败，换个主题试试？" + "重新生成"按钮。
- **Pass Condition**: 前端不白屏；错误码/消息符合 §16.1 错误码规范。
- **Evidence**: 接口响应 body.code === 5003 或 fixture quiz_id=quiz_fixture_xxx。

### AC-6 三层内容安全过滤链 (Type: rule)
- **Given**: 输入内容含典型敏感词（政治/色情/暴力核心词 1 条）
- **When**: 点开始生成
- **Then**: ① 前端立刻 Toast 不发请求 OR（若绕过前端）② 后端 POST /quiz/generate 返回 code=3001 INPUT_CONTENT_VIOLATION；③ 后端若 DeepSeek 仍返回违规文本，输出 DFA 二次扫描命中返回 5003。
- **Pass Condition**: 所有层至少 1 层拦截成功；前端页面不展示违规内容。
- **Evidence**: 3 层分别跑单元测试（见 tasks Task 9）+ 手工测试截图。

### AC-7 页面路由命名规范 (Type: rule)
- **Given**: 开发完成
- **When**: `ls frontend/src/pages`
- **Then**: 存在 `index/index.tsx` / `quiz/index.tsx` / `report/index.tsx` 3 个主 MVP 页面；`frontend/src/app.config.ts` pages 数组包含此 3 项。
- **Pass Condition**: 目录名与方案文档 §18.1 完全一致（首页 = pages/index/index，不是 home/）
- **Evidence**: `tree frontend/src/pages` 命令输出。

### AC-8 前端目录重命名 (Type: rule)
- **Given**: 根目录结构
- **When**: `ls e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn`
- **Then**: 存在 `frontend/` 目录；不再有 `front-page/` 根目录（所有原 front-page/ 的内容移动到 frontend/，Git history 保留通过 rename 操作追踪）。
- **Pass Condition**: `frontend/package.json` 存在；原 `front-page/` 不存在。
- **Evidence**: 根目录 LS 输出 + `frontend/package.json` 文件存在。

### AC-9 UI 原型色彩/渐变保真度 (Type: rubric)
- **Dimension**: 首页 / 闯关页 / 报告页 3 张真机截图与原型 01-core-flow.html 的色彩、渐变、圆角、阴影、字体层级一致性
- **Scale**: 1-5
- **Anchors**: 1 = 完全不匹配（主色仍是蓝色、按钮无渐变）；3 = 大部分颜色正确但圆角/阴影细节有出入；5 = 按钮 linear-gradient(180deg, #ff944f, #ff6f27) 完全一致；米色背景 #f6f4ef；橙色卡片边框 #ecdccc 完全对齐；CoinBadge 暖橙渐变 100% 匹配。
- **Pass Threshold**: ≥ 4
- **Evidence**: 截图 diff 对比表 + 原型 CSS 变量值 vs 前端 theme.scss 变量表对照。

### AC-10 DeepSeek JSON 双层兜底实现 (Type: rule)
- **Given**: backend/app/services/langchain_factory.py 文件
- **When**: grep 代码
- **Then**: ① 主链 `.bind(response_format={"type":"json_object"}) + model_validate_json()` 存在并执行；② with_structured_output(QuizGenerateResult) 完整逻辑在注释中保留（未来可切换）；③ model_validate_json 前有"剥 markdown 代码块"容错（剥离 ```json 包裹）。
- **Pass Condition**: 上述 3 个代码块均可 grep 定位到。
- **Evidence**: langchain_factory.py L52-119（Quiz）+ L170-245（Report）代码片段 + 注释备份段。

### AC-11 后端 TDD 测试全绿 (Type: rule)
- **Given**: backend/ .venv 激活
- **When**: `pytest -v tests/`
- **Then**: 至少 15 个测试用例（含 health / quiz_api / report_api / scoring / content_filter DFA / text_cleaner / prompt_contract 5 次）全部 pass，0 fail。
- **Pass Condition**: pytest exit code 0；用例数 ≥ 15；passed = 100%。
- **Evidence**: pytest 终端输出截图。

### AC-12 build:weapp dist/ 产物合规 (Type: rule)
- **Given**: frontend/ 目录
- **When**: `npm run build:weapp` 或等价 taro 构建
- **Then**: `frontend/dist/pages/index/index.js`、`dist/pages/quiz/index.js`、`dist/pages/report/index.js` 3 个主 MVP 页面存在；dist 目录总大小（不计 .map） ≤ 1.8MB。
- **Pass Condition**: 3 个文件全部存在且大小 > 0；总大小 ≤ 1.8MB。
- **Evidence**: dist/ 大小统计命令输出 + file existing check。

### AC-13 Prompt 契约测试 5 次结构稳定 (Type: rule)
- **Given**: tests/test_prompt_contract.py 存在
- **When**: pytest -v tests/test_prompt_contract.py
- **Then**: 连续 5 次独立 quiz_chain invoke → 5 次 result questions 数量 ∈ [3,5]；每题 id/type/stem/options/answer/explanation/kp/difficulty 9 字段全非空；answer.keys 均是子集 options.keys。
- **Pass Condition**: 5 × 9 字段全部非空，类型断言全绿。
- **Evidence**: pytest 该文件 PASS 输出。

### AC-14 错误码标准化 (Type: rule)
- **Given**: 方案文档 §16.1 ErrorCode 枚举 (1001-5003)
- **When**: grep backend/core/exceptions.py + frontend/src/types/common.ts
- **Then**: 后端 BusinessException.code / 前端 ErrorCode 对象 7 个以上错误码（SUCCESS/PARAM/PARAM_INVALID/INPUT_TOO_SHORT/INPUT_TOO_LONG/INPUT_VIOLATION/OUTPUT_VIOLATION/QUIZ_NOT_FOUND/ANSWER_INVALID/DEEPSEEK_TIMEOUT/DEEPSEEK_FORMAT_ERROR/DEEPSEEK_RETRY_EXHAUSTED/INTERNAL）完全一致，数值无冲突。
- **Pass Condition**: 前后端同名字段数值 100% 一致；无 typo/数值错位。
- **Evidence**: 两端文件 grep 结果对比表。

## Open Questions (待澄清项)
- [x] **Q-1 现有代码复用 vs 从零重搭？** → 【已澄清 2026-09-26 AskUserQuestion】复用+重命名，不推翻。
- [x] **Q-2 UI 主色调（原型图暖橙 vs 现有字节蓝）？** → 【已澄清】严格暖橙 #ff7a2f + 米色背景，所有色彩 token 重写。
- [x] **Q-3 DeepSeek 结构化输出方案？** → 【已澄清】优先 json_object + model_validate_json；with_structured_output 注释备份未来切换。
- [x] **Q-4 MVP 页面范围（3 页核心 vs 现有 7 页 + TabBar）？** → 【按方案文档收敛】验收只关注 index/quiz/report 3 页；其余 4 页保留不验收。
