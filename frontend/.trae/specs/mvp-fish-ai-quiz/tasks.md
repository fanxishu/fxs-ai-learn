# 《智能 AI 闯关学习小程序》MVP 实现任务清单 (tasks.md)

**关联规格**：`spec.md` / 开放问题 OQ-1~OQ-4 待用户确认后才能进入 Implement 阶段。

---

## 阶段一：项目脚手架与环境（依赖 AC-01 / AC-11）

### Task 1：后端 FastAPI 脚手架建立 + 健康检查
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-09, AC-11
- **产出目录**: `backend/`（对齐方案设计 §6.1 目录结构）
- **实施步骤**:
  1. 创建 `backend/app/api/v1/routes/health.py` + `quiz.py` + `report.py` 路由文件（空实现，health 先通）
  2. 创建 `backend/app/core/{config.py,logging.py,exceptions.py,security.py}`：config 使用 `pydantic-settings` 读取 `.env`，暴露 `DEEPSEEK_API_KEY`、`USE_MOCK_LLM`、`PROJECT_NAME` 等
  3. 创建 `backend/app/main.py`：FastAPI 实例 + CORS（前端 8080 / 微信开发者工具） + include_router v1
  4. 创建 `backend/requirements.txt`（fastapi uvicorn pydantic-settings langchain langchain-openai pytest pytest-asyncio httpx python-dotenv）
  5. 创建 `backend/tests/conftest.py` + `test_health.py` + `pytest.ini`
- **本地测试要求 (TR)**:
  - TR-1.1 (rule): `cd backend && python -m pytest tests/test_health.py -v` → 1 passed
  - TR-1.2 (rule): `uvicorn app.main:app --reload` 启动后 `curl http://127.0.0.1:8000/api/v1/health` HTTP 200 且 `status == "ok"`

### Task 2：前端 Taro 4.x 脚手架建立
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-01, AC-12
- **产出目录**: `frontend/`（项目子目录，不污染 docs/.trae）
- **实施步骤**:
  1. 在项目根执行 `taro init frontend` → 选项：React / TypeScript / Sass / Webpack5 / npm 或 pnpm（按 OQ-1）/ 默认模板 / 状态管理：Zustand（手装，等脚手架完成后 pnpm add zustand）
  2. 创建 4 个页面骨架：`src/pages/home/index.tsx`、`src/pages/quiz/index.tsx`、`src/pages/report/index.tsx`、`src/pages/loading/index.tsx` + 对应的 `.config.ts` + `.module.scss`
  3. 修改 `src/app.config.ts` → pages 顺序 `pages/home/index` 第一；window 默认主题色 `#ff7a2f`
  4. 新增 `src/styles/tokens.scss`：Copilot 原型 8 项 CSS Variables (orange/blue/green/red/text/muted/bg/radius) + font-stack
  5. 新增 `src/api/request.ts`：统一 `Taro.request` 封装，base_url 取 `process.env.TARO_APP_API_BASE`（dev 默认 http://127.0.0.1:8000），超时 35000，错误统一 Toast
  6. `.env.development` + `.env.production`（TARO_APP_API_BASE 区分）
- **本地测试要求 (TR)**:
  - TR-2.1 (rule): `cd frontend && pnpm dev:weapp` 或 `npm run dev:weapp` 编译无 error；微信开发者工具导入 `dist/` 无报错
  - TR-2.2 (rule): 小程序切换 4 个路由（home / loading / quiz / report）都能正常显示"页面工作中…"占位，不白屏
  - TR-2.3 (rule): `src/styles/tokens.scss` 变量能在 home page 上成功渲染一个橙色按钮且颜色值严格等于 `#ff7a2f`

---

## 阶段二：后端核心（出题 / 评分 / 报告 —— **TDD 先行**，依赖 AC-04/05/07/09）

### Task 3：数据模型 Pydantic 建立 + 合约测试
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-04, AC-07, AC-09
- **产出文件**: `backend/app/models/quiz.py`、`backend/app/models/report.py`、`backend/app/models/common.py`
- **实施步骤**:
  1. `common.py`: `ErrorResponse` + `ApiResponse[T]` 统一响应包装（`code: int, message: str, data: T`）
  2. `quiz.py`: `QuizOption(key,text)` / `Question(id, type: Literal["single","multiple","judge"], stem, options, answer:list[str], explanation, knowledge_point, difficulty:Literal["easy","medium","hard"])` / `QuizGenerateRequest(user_input, question_count=5, difficulty="mixed")` / `QuizGenerateResult(quiz_id, title, summary, questions:list[Question])` + 字段 validator：判断题 option 必须是 2 项 ["正确","错误"]；多选题 answer len≥2；单选 len==1
  3. `report.py`: `AnswerRecord(question_id, user_answer, is_correct, time_spent_ms, timestamp)` / `ReportGenerateRequest(quiz_id, quiz, answer_records)` / `ScoreSummary(correct_count, wrong_count, total, accuracy, mastery_by_kp:dict[str,float])` / `ReportGenerateResult(accuracy, mastered_points, weak_points, three_line_summary:list[str] len==3, advice:list[str], share_quote)`
  4. 编写合约测试 `backend/tests/test_prompt_contract.py`：断言 Question 结构 JSON schema；断言 Report 三句总结长度 == 3；断言正确率 range 0-100
- **本地测试要求 (TR)**:
  - TR-3.1 (rule): `pytest tests/test_prompt_contract.py -v` → 至少 6 passed

### Task 4：Scoring Service（纯算法，不需要 LLM，**最适合 TDD 先写**）
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-07
- **产出文件**: `backend/app/services/scoring_service.py` + `backend/tests/test_scoring_service.py`
- **算法**:
  - `calc_score_summary(quiz: QuizGenerateResult, records: list[AnswerRecord]) -> ScoreSummary`
  - 按 `knowledge_point` 聚合：某知识点下答对题数 / 总题数 = mastery
- **TDD 顺序**：先写 8 条测试用例（全对/全错/知识点错/空记录/缺题/只有判断题/多选题判对/多选题漏选）全部 fail → 实现 scoring_service → 全部 pass
- **本地测试要求 (TR)**:
  - TR-4.1 (rule): `pytest tests/test_scoring_service.py -v` → 8/8 全部通过

### Task 5：LangChain Factory + Quiz Chain（带 mock 测试）
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-04, AC-05
- **产出文件**: `backend/app/llm/langchain_factory.py`、`backend/app/llm/quiz_chain.py`、`backend/app/llm/output_schemas.py`、`backend/app/prompts/quiz_prompt.py`
- **实施步骤**:
  1. `output_schemas.py`: Pydantic 对应 Task 3 QuizGenerateResult 的 `with_structured_output()` 目标类
  2. `langchain_factory.py`: 如果 `USE_MOCK_LLM=true` → 返回 MockLLM（读取 fixture JSON）；否则返回 `ChatOpenAI(model=deepseek-chat, base_url=https://api.deepseek.com, api_key=config.DEEPSEEK_API_KEY, temperature=0.4, max_retries=2, timeout=30)`
  3. `quiz_prompt.py`: 版本化 prompt v1（对齐方案设计 §8.3），`ChatPromptTemplate.from_messages([system, user])`；v2 为保守 fallback prompt（降低难度 + 更严格 JSON 指令）
  4. `quiz_chain.py`: `def generate_quiz(req: QuizGenerateRequest, use_fallback=False)` 返回 `QuizGenerateResult`；异常分支按五级兜底：空响应 → PydanticException → 字段缺 → use_fallback 重试一次 → raise QuizGenerateError(5001)
  5. fixture JSON: `backend/tests/fixtures/quiz_rag_example.json`（3 单 1 多 1 判断共 5 题）
- **本地测试要求 (TR)**:
  - TR-5.1 (rule): `USE_MOCK_LLM=true pytest tests/test_quiz_chain.py -v` → 至少 5 passed（含 4 个异常分支模拟）
  - TR-5.2 (rule): mock 返回多选题 answer 只给 1 项时 → 三级校验触发 QuizGenerateError

### Task 6：Report Chain（带 mock 测试）
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-07
- **产出文件**: `backend/app/llm/report_chain.py`、`backend/app/prompts/report_prompt.py`、`backend/tests/fixtures/report_rag_example.json`
- **实施步骤**:
  1. `report_prompt.py`：对齐方案设计 §8.6，输入 {topic} {quiz_json} {answer_records} {score_summary}，输出 7 字段 Pydantic
  2. `report_chain.py`：同 quiz_chain，支持 Mock 模式
  3. `report_service.py`：组合 `scoring_service` + `report_chain`
- **本地测试要求 (TR)**:
  - TR-6.1 (rule): `USE_MOCK_LLM=true pytest tests/test_report_chain.py -v` → at least 4 passed
  - TR-6.2 (rule): three_line_summary 长度必须是 3，advice 非空，share_quote 15-40 字

### Task 7：Quiz API + Report API（路由层 + HTTP 测试）
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-04, AC-07, AC-11
- **产出文件**: `backend/app/api/v1/routes/quiz.py`、`report.py`；`backend/tests/test_quiz_api.py`、`test_report_api.py`
- **实施步骤**:
  1. Quiz POST /api/v1/quiz/generate → 长度敏感词校验 → service → ApiResponse[QuizGenerateResult]
  2. Report POST /api/v1/report/generate → scoring → AI report → ApiResponse[ReportGenerateResult]
  3. 敏感词 MVP：100 词黑名单 `backend/app/utils/content_filter.py` + 测试
  4. `text_cleaner.py`：清洗用户输入空白、超长、HTML
- **本地测试要求 (TR)**:
  - TR-7.1 (rule): `USE_MOCK_LLM=true pytest tests/test_quiz_api.py tests/test_report_api.py -v` → ≥ 15 passed（含入参校验、敏感词、长度、返回结构、错误码 5001）

---

## 阶段三：前端 4 个页面 + 组件库（依赖 AC-02/03/06/08/10）

### Task 8：Design Tokens 组件库（对齐 Copilot 03-design-system-board）
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-02, AC-10, AC-12
- **产出文件**: `frontend/src/components/` 下 10 个组件
- **组件清单（每个含 tsx + scss module）**：
  1. `AppButton`（4 变体：primary / soft / ghost / danger，最小 44px）
  2. `AppInput`（text / textarea 86px 高两种）
  3. `StateBadge`（info/good/bad 三色提示条）
  4. `Chip` / `Token`（胶囊 chip）
  5. `CoinBadge`（金币胶囊 + SVG）
  6. `ProgressTrack`（8px 圆角渐变进度条 + meta 文案）
  7. `RingProgress`（88px 掌握度饼图，用 conic-gradient 或 Taro Canvas）
  8. `QuizOption`（单选/多选/判断样式，正确态 green 勾 SVG / 错误态红叉）
  9. `ExplainBox`（解析框）
  10. `NoteCard`（报告卡片）
- **本地测试要求 (TR)**:
  - TR-8.1 (rule): Storybook 可选，或者在 home page 放一个临时 `TokensPreview` 区块能看到 10 组件全部渲染正确
  - TR-8.2 (rubric 0-5 ≥ 4): 与 03-design-system-board 的视觉还原度评分截图对比 ≥ 4

### Task 9：首页 Home Page（输入 + 校验 + 跳 Loading）
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-01, AC-03
- **产出文件**: `frontend/src/pages/home/index.tsx` + `.config.ts` + `.module.scss` + `stores/home.ts`（可选 Zustand）
- **实施步骤**：严格按 Copilot 01-core-flow.html 屏幕 1：
  - 顶部 toolbar：你好，小皮（占位名） + 金币胶囊
  - 标题「今天想闯哪一关？」
  - label「输入你想学的内容」+ 吉祥物 mini-mascot + textarea 3 行 placeholder
  - 「开始生成题目」primary 按钮居中
  - 底部固定 tabbar（3 tab 占位）
- **本地测试要求 (TR)**:
  - TR-9.1 (rule): 输入 < 5 字 → 按钮 disabled + Toast 轻提示「内容太短～」
  - TR-9.2 (rule): 输入 > 500 → 截断 + Toast「内容过长，已自动截断到 500 字」
  - TR-9.3 (rule): 输入合法 → 按钮点击后 `Taro.navigateTo({ url: '/pages/loading/index?text=xxx' })`

### Task 10：Loading 页 + quiz 生成接口对接
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-04
- **产出文件**: `frontend/src/pages/loading/index.tsx` + `.scss` + `src/api/quizApi.ts`（封装 quiz/generate）
- **实施步骤**：4 步智能进度（`01 收集中… → 02 整理知识 → 03 生成题目 → 04 准备好啦`），与后端 30s 超时联调
- **本地测试要求 (TR)**:
  - TR-10.1 (rule): `USE_MOCK_LLM=true` 后端运行时，提交一句「RAG 和传统搜索」5s 内收到 5 题并跳 quiz 页
  - TR-10.2 (rule): 后端返回 5001 时 → loading 页显示「生成失败，返回重试」按钮可回到 home

### Task 11：闯关 Quiz Page（状态机：未答 → 已答 → 下一题）
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-06
- **产出文件**: `frontend/src/pages/quiz/index.tsx` + `.scss` + `stores/quiz.ts`（Zustand：questions / currentIdx / records / isSubmitted[]）
- **实施步骤**：Copilot 01-core-flow 屏幕 2 还原：
  - 顶部「关闭 ×」+ `第 12 / 20 题`+ Coin
  - ProgressTrack + meta 文案「第 3 关 / 共 5 关 · 答对 8 题」
  - 题干 h2
  - QuizOption 列表（判断 2 项、单选 4、多选 + 一个确认提交按钮）
  - 提交后 500ms：ResultTip + ExplainBox + 「上一题 / 继续 →」按钮
  - 最后一题，`继续 →` 文案改成 `查看报告 →` 跳 report
- **本地测试要求 (TR)**:
  - TR-11.1 (rule): 5 题做完，records.length == 5，全部 is_correct 字段正确
  - TR-11.2 (rule): 上一题按钮回跳后选项不可再次点击（只读态）
  - TR-11.3 (rule): 进度条宽度比例 `(i+1)/total` 精确到 1%

### Task 12：报告 Report Page
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-08, AC-10
- **产出文件**: `frontend/src/pages/report/index.tsx` + `.scss` + `src/api/reportApi.ts`
- **实施步骤**: Copilot 01-core-flow 屏幕 3：
  - 顶部 toolbar 「RAG 入门」 + `+20 XP`
  - 标题「你这局学得很稳」+ 副标题
  - 2 枚 Chip「掌握度 +1」「错题 -2」
  - NoteCard：88px RingProgress（accuracy 映射颜色） + 文字点评 + 条形掌握度
  - NoteCard：最该补的 N 点（weak_points 映射）
  - 3 句总结 NoteCard + 建议
  - 分享金句卡片 + 「生成海报」按钮 Toast 占位（OQ-4 决定是否做 canvas 版）
  - 「再闯一关」回到 home
- **本地测试要求 (TR)**:
  - TR-12.1 (rule): ring 百分比 = accuracy 精确显示，conic-gradient 角度一致
  - TR-12.2 (rule): three_line_summary 3 句全部渲染，无字段缺失报错

---

## 阶段四：全链路联调 + 文档收尾（依赖 AC 全部）

### Task 13：前后端联调脚本 + 根 README 更新
- **Status**: pending
- **Priority**: medium
- **父 AC 覆盖**: AC-11, AC-12
- **产出文件**: `README.md`（补充后端启动、前端启动、env 配置）；`scripts/start-dev.ps1`（一键启动后端 8000 + 前端 dev:weapp）
- **本地测试要求 (TR)**:
  - TR-13.1 (rule): 新人 clone → 按 README 5 步能跑通「输入 → 答题 → 报告」全流程
  - TR-13.2 (rule): `USE_MOCK_LLM=true` 不需要任何 key 即可全流程通过

### Task 14：最终验证 & 回归测试打包
- **Status**: pending
- **Priority**: high
- **父 AC 覆盖**: AC-09, AC-10
- **实施步骤**：
  1. 执行 `cd backend && USE_MOCK_LLM=true pytest -v` 截图证据 → 0 失败
  2. 前端 dev:weapp 截图 3 张：home / quiz（已答题）/ report，对比 Copilot 原型给 AC-10 评分
  3. 记录每个 AC 完成的证据位置
- **本地测试要求 (TR)**:
  - TR-14.1 (rule): 后端 pytest 总用例数 ≥ 40，通过率 100%
  - TR-14.2 (rubric 0-5 ≥ 4): 3 页 UI 还原度最终评分 ≥ 4

---

## 任务依赖图（串行 / 并行建议）

```
Task1(back-scaff) ─┐
                    ├─→ Task3(models) ─→ Task4(scoring TDD) ─→ Task7(api) ─┐
Task2(front-scaff) ─┤                                                         ├─→ Task13/14
                    └─→ Task8(组件库) ─→ Task9(home) ─→ 10(loading) ─→ 11(quiz) ─→ 12(report) ─┘

Task5(quiz-chain) / Task6(report-chain) 可在 Task3 后与 Task4 并行。
```

**总任务数**: 14 个 Task（约 50+ TR），预计分 4 天完成。**等待你确认 OQ-1~4 + 批准 spec.md & tasks.md 后，我立刻从 Task 1 开始 Implement。**
