# 鱼皮 AI 闯关学习小程序 MVP - 开发任务拆分 (tasks.md)

---

## Task 1: 前端目录重命名 frontend/ → frontend/（保留 Git 历史）

- **Status**: pending
- **Priority**: HIGH
- **Depends On**: (无，基础层第一个任务)
- **Description**: 使用 `git mv` 将根目录下的 `frontend/` 完整重命名为 `frontend/`，确保 Git history 可追踪；同步更新**所有**跨目录路径引用：
  1. 根目录 `README.md` 中所有 `cd frontend` 路径；
  2. `.gitignore` 中若有显式 `frontend/node_modules` 条目；
  3. 根目录脚本（如 `__https_proxy.js`、`__run_npm*.js`、`__build_weapp*.js` 等）中的 `frontend/` 硬编码路径；
  4. `frontend/project.config.json` 的 `projectname`、`miniprogramRoot` 相对路径（保持 dist/ 不变）；
  5. 规格文档 `.trae/specs/mvp-fish-ai-quiz/spec.md` 中的路径引用（如果有）；
  6. `.env` / `.pai` / `.taro-home` 目录随重命名一起迁移。
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - **Rule**: 在 `e:\xiaochengxu\fxs-ai-learn\fxs-ai-learn\` 下执行 `ls`，输出包含 `frontend/` 且**不包含** `frontend/`；`frontend/package.json` 存在且文件大小 > 0；`git log --oneline -1` 显示 rename 操作追踪。

---

## Task 2: 路由规范化 pages/home/ → pages/index/（按方案 §18.1）

- **Status**: pending
- **Priority**: HIGH
- **Depends On**: Task 1
- **Description**:
  1. `git mv frontend/src/pages/home frontend/src/pages/index`（把 home 目录整体改名 index，保留 3 件套 tsx/config/module.scss）；
  2. 如果 `frontend/src/pages/index/` 已有占位空目录，先删除再移动；
  3. 同步更新 `frontend/src/app.config.ts` 的 `pages` 数组，首项改为 `pages/index/index`（顺序必须 index > quiz > report 靠前）；
  4. 全局 grep 代码中所有 `from '@/pages/home/` 或 `import .../home/index` 的反向引用，逐一改为 `@/pages/index/`；
  5. 检查 store / api / router.navigateTo 中 `url: '/pages/home/xxx'` 的跳转路径，改为 `/pages/index/xxx`。
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - **Rule**: `ls frontend/src/pages/` 输出包含 `index/ quiz/ report/`；`cat frontend/src/app.config.ts | head -n 20` 中 `pages[0] === 'pages/index/index'`；build:weapp 后 `dist/pages/index/index.js` 文件存在。

---

## Task 3: 暖橙米色设计系统全量替换（theme + variables + 10 组件 + 7 页面 + TabBar）

- **Status**: pending
- **Priority**: HIGH
- **Depends On**: Task 2
- **Description**: 严格对齐 `docs/Copilot生成的原型图/01-core-flow.html` + `03-design-system-board.html` 的 CSS 变量，100% 覆盖所有旧蓝色（#165DFF）体系：
  1. **`frontend/src/styles/theme.scss`**：重写全部 SCSS 变量：
     - `$color-primary: #ff7a2f`（暖橙主色）
     - `$color-bg-page: #f6f4ef`（米色背景）
     - `$color-card-bg: #fff6ef` / `$color-card-border: #ecdccc`
     - `$color-primary-gradient: linear-gradient(180deg, #ff944f, #ff6f27)`
     - `$color-primary-shadow: 0 10px 20px rgba(255, 122, 47, 0.24)`
     - 圆角半径：`$radius-sm:14px / $radius-md:16px / $radius-lg:22px / $radius-xl:34px`
     - CoinBadge 渐变 / Chip 选中色 / StateBadge 橙/绿/红（分别 `#ff7a2f` / `#38b987` / `#ff6f5d`）
  2. **`frontend/src/styles/variables.scss`**：同步与 theme.scss 保持一致（若有重复声明以 theme 为准），确保所有 `@use '@/styles/variables.scss' as *` 的页面/组件取到新值。
  3. **10 个组件 module.scss**（AppButton/AppInput/Chip/CoinBadge/ExplainBox/NoteCard/ProgressTrack/QuizOption/RingProgress/StateBadge）：
     - `AppButton.module.scss` 主按钮 `.primary`：`background: linear-gradient(180deg, #ff944f, #ff6f27)` + `box-shadow: 0 10px 20px rgba(255,122,47,.24)` + `inset 0 1px 0 rgba(255,255,255,.22)`；`min-height: 46px`；`border-radius: 14px`；
     - CoinBadge：橙渐变填充；
     - QuizOption 选中/正确/错误三色：选中 `border-color:#ff7a2f`，正确绿 `#38b987`，错误红 `#ff6f5d`；
     - ProgressTrack 进度条填充色 `linear-gradient(90deg,#ff944f,#ff6f27)`。
  4. **7 个页面 module.scss**（index/quiz/report/history/mine/loading/旧占位 index）：
     - 根 `.page` 背景统一 `#f6f4ef`；
     - 首页 index 模块卡片 `background: #fff6ef; border:1px solid #ecdccc; border-radius:22px;`；
     - 闯关页顶部进度容器、报告页 RingProgress 外环色全部暖橙。
  5. **`frontend/src/app.config.ts` TabBar**：`selectedColor: "#ff7a2f"`；`backgroundColor: "#ffffff"`；`borderStyle: "white"`。
  6. **TabBar 6 个图标 PNG/SVG**（若 `assets/tabbar/` 下有旧蓝色图标）：用颜色重染为暖橙（未选中灰色 #999，选中 #ff7a2f），或替换为新 PNG（微信小程序仅支持 PNG，不支持 SVG 作为 tabBar icon）。
- **Acceptance Criteria Addressed**: AC-9（rubric ≥ 4 阈值）
- **Test Requirements**:
  - **Rubric**: 首页/闯关页/报告页 3 张截图对比原型 01-core-flow.html；维度：渐变按钮（主色线性180deg）/米色背景 / 橙边卡片 / CoinBadge 渐变 四项；每项 1~5 分，Pass Threshold ≥ 4 / 5。
  - **Rule**: `grep -r "165DFF" frontend/src/ --include="*.scss" --include="*.ts" --include="*.tsx"` 输出 0 条（旧蓝色残留为 0）。

---

## Task 4: 后端 DeepSeek 双层兜底代码加固 + 注释备份段补齐

- **Status**: pending
- **Priority**: HIGH
- **Depends On**: (独立后端任务，与前端 Task2/3 可并行，实际串行化简化) Task 1
- **Description**: 编辑 `backend/app/services/langchain_factory.py` 的 Quiz 和 Report 两条链：
  1. 抽取手剥 markdown 代码块容错函数 `_strip_json_fence(raw: str) -> str` 到文件顶部，逻辑：若 `raw.startswith("```json")` 或含 ` ``` ` 包裹，则剥离首尾 fence，仅保留 JSON 本体字符串；
  2. Quiz 链（L52-119 区域）：主链确保 `llm.bind(response_format={"type":"json_object"})` + system prompt 内嵌 `QuizGenerateResult.model_json_schema()` 花括号双重转义 `{{ }}` + 返回前 `_strip_json_fence` + `QuizGenerateResult.model_validate_json()`；紧接着在下方追加 8~15 行 `# with_structured_output 备份链：` 注释块，完整写出 `llm.with_structured_output(QuizGenerateResult).invoke(...)` 的可切换代码（当前不执行，仅注释，未来 DeepSeek 支持 json_schema 时注释掉主链、取消注释备份链即可切换）；
  3. Report 链（L170-245 区域）：同 Quiz 链，补 `ReportGenerateResult` 的 `with_structured_output` 注释备份完整代码块；确保 `per_knowledge_mastery` 兼容 `dict` / `Pydantic` 两种解析结果；
  4. 给 `_strip_json_fence` 写 **1 个独立单元测试**（在 `test_langchain_fence.py` 或并入 `test_text_cleaner.py`）：输入 `raw = "```json\n{\"a\":1}\n```"`，输出等于 `{"a":1}`（字符串）；输入纯 JSON 返回原样。
- **Acceptance Criteria Addressed**: AC-10
- **Test Requirements**:
  - **Rule**: 三条件全部满足：(a) `grep -n "response_format.*json_object" backend/app/services/langchain_factory.py` 返回 ≥ 2 行（Quiz + Report 各 1）；(b) `grep -n "with_structured_output.*备份" backend/app/services/langchain_factory.py` 返回 ≥ 2 行注释备份标识；(c) `grep -n "_strip_json_fence" backend/app/services/langchain_factory.py` 返回 ≥ 1 行定义 + Quiz/Report 至少各 1 行调用。

---

## Task 5: 后端 TDD 测试补齐（≥ 15 cases 全绿 + 工具层覆盖率 ≥ 85%）

- **Status**: pending
- **Priority**: HIGH
- **Depends On**: Task 4
- **Description**: 基于 `backend/tests/` 现有 9 文件，新增/补齐如下测试文件与用例：
  1. **新建 `test_content_filter.py`**（DFA 单测，≥ 5 用例）：
     - `test_dfa_detect_political_keyword`、`test_dfa_detect_porn_keyword`、`test_dfa_detect_violence_keyword`（三条核心违规词命中）；
     - `test_dfa_pass_clean_text`（正常文本不命中）；
     - `test_dfa_mixed_case_insensitive`（大小写/全半角混合场景）。
  2. **新建 `test_text_cleaner.py`**（≥ 4 用例，如不存在）：
     - 测试 `clean_user_input` 去前后空白、去不可见字符；
     - 测试 Task 4 中 `_strip_json_fence` 两个场景（有 fence vs 无 fence）。
  3. **新建 `test_error_codes.py`**（≥ 3 用例）：
     - `test_param_missing_returns_1001`、`test_input_too_long_returns_1003`、`test_input_violation_returns_3001`：调 quiz/generate 对应参数触发 BusinessException，断言响应 `body.code` 数值完全匹配方案 §16.1。
  4. **现有 `test_prompt_contract.py` 强化**：确保有 5 次独立连续 invoke（不是循环用同一结果），断言 questions 长度 ∈[3,5]、每题 9 字段非空（对应 AC-13）。
  5. **现有 `test_report_chain.py` / `test_quiz_api.py` 补参数校验**：输入空字符串 / 长度 1 字符 / 含违规词 三种场景，断言 code ≠ 0。
  6. 最后**执行 pytest**，最终结果：用例总数 ≥ 15，0 fail；工具层 coverage ≥ 85%。
- **Acceptance Criteria Addressed**: AC-11
- **Test Requirements**:
  - **Rule**: `cd backend && .venv\Scripts\activate && pytest -v tests/ --tb=short` 退出码 0，终端最后一行 `passed = N`，N ≥ 15；若运行 coverage 命令（可选）则 `coverage report` 中 `content_filter.py` / `text_cleaner.py` / `scoring_service.py` 行覆盖率均 ≥ 85%。

---

## Task 6: 错误码标准化两端对齐（13 种数值 100% 一致）

- **Status**: pending
- **Priority**: MEDIUM
- **Depends On**: Task 5（后端先定义为基准，前端跟）
- **Description**:
  1. **后端 `backend/core/exceptions.py`**：补完整 `ErrorCode` 类/枚举，严格按方案 §16.1：
     ```
     SUCCESS = 0
     PARAM_MISSING = 1001
     PARAM_INVALID = 1002
     INPUT_TOO_LONG = 1003
     INPUT_TOO_SHORT = 1004
     UNAUTHORIZED = 2001
     FORBIDDEN = 2002
     INPUT_CONTENT_VIOLATION = 3001
     OUTPUT_CONTENT_VIOLATION = 3002
     QUIZ_NOT_FOUND = 4001
     ANSWER_INVALID = 4002
     DEEPSEEK_TIMEOUT = 5001
     DEEPSEEK_FORMAT_ERROR = 5002
     DEEPSEEK_RETRY_EXHAUSTED = 5003
     INTERNAL_ERROR = 5000
     ```
  2. `BusinessException` 类确保持有 code + message 两字段，`app.py` 全局 exception handler 返回 `ApiResponse(code=e.code, message=e.message, data=None)` HTTP 200。
  3. **前端 `frontend/src/types/common.ts`**：创建或补全 `ErrorCode` 对象/枚举，上述所有字段**数值与后端逐字相等**；
  4. 前端 `frontend/src/services/api.ts` 错误处理分支 Toast 文案按错误码映射：3001→"输入内容违规，换个主题试试"、5003→"AI 出题失败，请重试"。
- **Acceptance Criteria Addressed**: AC-14
- **Test Requirements**:
  - **Rule**: 生成对比表：后端 `ErrorCode.__dict__`（或枚举值）vs 前端 `console.log(ErrorCode)`，两对象所有同名字段**数值严格相等**（字段数 ≥ 13），且无 typo（如把 RETRY_EXHAUSTED 写成 RETRY_EXHAUSTED 这种拼写错误 0 容忍）。

---

## Task 7: 三层内容安全过滤链（前端正则 + 后端 DFA + AI 输出二次扫描）

- **Status**: pending
- **Priority**: MEDIUM
- **Depends On**: Task 6
- **Description**:
  1. **前端正则拦截层**（`frontend/src/services/` 新建 `contentFilter.ts`）：内置约 100 条中文核心敏感词正则（政治/色情/暴力/毒品/赌博五类，取行业高频词表）；导出 `checkInputViolation(input: string): {hit: boolean; word?: string}`；首页 `pages/index/index.tsx` 的 `onSubmitStartQuiz` 调用此函数，命中 → Toast "输入内容包含违规词，请修改后重试"，不发请求。
  2. **后端 DFA 输入过滤层**（`backend/app/utils/content_filter.py`）：补 `DFASensitiveWordFilter` 类（基于 DFA 前缀树），构造函数加载同样 100 条词表；导出 `filter_input(text: str) -> FilterResult {hit, hit_word, cleaned_text}`；`quiz_service.generate_quiz()` 入口第一行调用，若 hit → 抛 BusinessException(3001)。
  3. **后端输出二次扫描层**：`quiz_service.generate_quiz()` 拿到 LLM 返回的 QuizGenerateResult 后，对 `title`、`summary`、每个 question 的 `stem`、`options[].text`、`explanation` 全部字段 ① DFA 过滤扫描；② 正则扫描外链（`http://` / `https://` 域名非白名单）、拒答模式（"作为 AI 我无法回答" / "我不能回答关于" 等字符串）；任一命中 → 抛 BusinessException(5003)，不向前端吐脏数据。
  4. 对应 Task 5 的 `test_content_filter.py` 加 ≥ 2 用例：`test_output_violation_returns_5003`（输入 LLM mock 含违规文本）、`test_external_link_scan_returns_5003`。
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - **Rule**: 手工测试流程：首页输入一条 100% 命中敏感词表的字符串 → 前端 Toast（第 1 层拦截）；绕过前端（curl -X POST）直接打 quiz/generate → 返回 code=3001（第 2 层）；mock LLM 返回外链文本 → quiz/generate 返回 code=5003（第 3 层）；三层任一拦截成功即 Pass。

---

## Task 8: 前端报告页分享海报占位 + 首页快捷 Chips 6 主题示例

- **Status**: pending
- **Priority**: MEDIUM
- **Depends On**: Task 3（UI 组件样式基础就绪）
- **Description**:
  1. **报告页 `pages/report/index.tsx`**：底部新增"生成分享海报"按钮（样式同 AppButton.secondary，圆角 14px 橙色描边）；onClick 不做 Canvas，仅 `Taro.showToast({title: "功能即将上线，敬请期待", icon: "none"})`（对应 FR-13）。
  2. **首页 `pages/index/index.tsx` 快捷 Chips 区**：在大输入框下方横向滚动 Chip 组（6 个 Chip）：「Java 设计模式」、「RAG 检索入门」、「HTTP vs HTTPS」、「React Hooks 详解」、「Python 列表推导」、「JS 闭包作用域」；Chip 点击 → 把 Chip 文本塞入输入框并 focus 输入框（降低用户输入成本，对齐原型首页 01-core-flow.html 快捷主题 chips 视觉）。
- **Acceptance Criteria Addressed**: FR-13（报告占位）、FR-1（首页 Chips）
- **Test Requirements**:
  - **Rule**: 报告页点击海报按钮，Taro.showToast 被触发（可在 Taro 预览 H5 控制台 Taro 拦截器查看）；首页点击 6 个 Chip 任意一个，输入框 value 变成对应字符串且输入框获得焦点。

---

## Task 9: Prompt 契约测试 5 次连续结构稳定（强化 AC-13）

- **Status**: pending
- **Priority**: MEDIUM
- **Depends On**: Task 4（双层兜底代码就绪）+ Task 5
- **Description**: 强化 `backend/tests/test_prompt_contract.py`：
  1. 测试函数使用 `@pytest.mark.parametrize("run_id", [1,2,3,4,5])` 跑 **5 次真实独立的 DeepSeek 调用**（不是 for-loop 检查同一份 result，每次都是新的网络请求）；
  2. 每次断言：`result.questions` 长度 ∈ [3, 5]；每道题 `id / type / stem / options / answer / explanation / knowledge_point / difficulty` 共 8+ 字段全部非空字符串/数组；`type` ∈ {single, multiple, judge}；`answer` 列表每个元素都是 `options` 对应 key 的子集；
  3. 允许最多 1 次失败（网络抖动）自动重试一次 pytest-flake 风格，但最终 5 次全部断言通过才算 Pass。
- **Acceptance Criteria Addressed**: AC-13
- **Test Requirements**:
  - **Rule**: `cd backend && .venv\Scripts\activate && pytest -v tests/test_prompt_contract.py` 输出 `5 passed`。

---

## Task 10: 前端 quizMock 兜底错误码 + api.ts Toast 文案规范对齐

- **Status**: pending
- **Priority**: MEDIUM
- **Depends On**: Task 6（ErrorCode 基准已就绪）
- **Description**:
  1. 检查 `frontend/src/data/quizMock.ts` 的 fallback 逻辑：当 API 失败 / 超时 / code !== 0 时，fixture 兜底路径返回的错误模拟码必须使用 Task 6 中的 `ErrorCode` 常量（而非魔法数字 5003 字面量）；
  2. 检查 `frontend/src/services/api.ts` 的 try/catch 分支：
     - `err.response.data.code === 3001` → Toast 使用 ErrorCode.INPUT_CONTENT_VIOLATION 分支文案；
     - `5001 / 5002 / 5003` → Toast 统一显示「AI 开小差了，请重试」+ 保留返回按钮；
     - 断网 / Network Error → Toast「网络连接失败，请检查网络」；
  3. 若 `frontend/src/pages/loading/index.tsx` 有错误面板（失败页），确保失败页按钮「重新生成」+「返回首页」两个按钮都存在且可点击（不白屏）。
- **Acceptance Criteria Addressed**: FR-15、AC-5
- **Test Requirements**:
  - **Rule**: 代码 grep：`frontend/src/data/quizMock.ts` 中无 `5003` 字面量（走 ErrorCode.DEEPSEEK_RETRY_EXHAUSTED）；`api.ts` 中 switch 分支覆盖 `3001/5001/5002/5003/network` 5 种 Toast 文案。

---

## Task 11: frontend/ 目录下 build:weapp 重新构建 + dist/ 产物合规检查

- **Status**: pending
- **Priority**: HIGH
- **Depends On**: Task 1 ~ Task 10（前后端代码变更完成）
- **Description**: 在 `frontend/` 目录（重命名后）执行构建：
  1. 若 `frontend/node_modules` 不存在则先安装（因 Skill init-template 未 npm install，例外手动补）：`set TARO_HOME=frontend\.taro-home && cd frontend && npm install --legacy-peer-deps`；如 ajv 包 postinstall 再次被过滤 → 复用历史修复方案：`npm pack ajv@8.20.0` + tar 解压覆盖 `node_modules/ajv/dist/`；
  2. 环境变量传入 TARO_HOME（避免 EPERM 写 C:\Users\.taro4.0）；
  3. 执行 `npm run build:weapp`（等价 `taro build --type weapp`）；
  4. 构建成功后：
     - 检查 `frontend/dist/pages/index/index.js`、`frontend/dist/pages/quiz/index.js`、`frontend/dist/pages/report/index.js` 三个主页面文件存在且文件大小 > 0；
     - 统计 `frontend/dist/` 总大小（排除 *.map），断言 ≤ 1.8MB（为后续功能预留 200KB 空间到 2MB 上限）；
     - 检查 `frontend/dist/app.json` pages 数组首项是 `pages/index/index`（和 Task 2 对应）。
- **Acceptance Criteria Addressed**: AC-12
- **Test Requirements**:
  - **Rule**: 三条件全满足：(a) 构建退出码 0（Webpack compiled successfully）；(b) `ls frontend/dist/pages/` 下 index/ quiz/ report/ 三个目录均有 `index.js`；(c) PowerShell 统计 `Get-ChildItem frontend/dist -Recurse -Exclude *.map | Measure-Object -Property Length -Sum` Sum ≤ 1,887,436 Bytes（≈1.8MB）。

---

## Task 12: 端到端冒烟 1 - Java 设计模式 5 题不 fallback fixture

- **Status**: pending
- **Priority**: HIGH
- **Depends On**: Task 11（前端构建就绪）+ Task 4 + Task 5 + Task 9（后端链通过契约）
- **Description**: 启动完整三进程（FastAPI 8000、HTTPS 反代 8443、Taro 预览服务或 H5），走完整链路：
  1. 后端 8000：`cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000`（或等价启动方式），访问 `/api/v1/health` → HTTP 200 `use_mock_llm=false`；
  2. HTTPS 反代 8443：启动 `__https_proxy.js`（指向 8000）；
  3. 前端 `.env` → `TARO_APP_API_BASE=https://127.0.0.1:8443`；
  4. 首页输入完整字符串："Java 设计模式 单例模式 观察者模式 工厂模式 SOLID 原则 策略模式 多态 开闭原则" → 点「开始闯关」；
  5. 45 秒内进入 quiz 页观察：共 5 题；逐一查看每题 `knowledge_point` 标签（可通过 Network data 或前端 console 打印），必须全部是 Java 设计模式相关关键词（单例/SOLID/多态/开闭/策略/观察者/工厂）；
  6. 断言**不触发 Python 5 题 fixture 兜底**（quiz_id 不等于 fixture 中的 quiz_fixture_5q 前缀，且 Network 响应 `data.title` 不出现 Python 关键词）。
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - **Rule**: Network 面板 `POST /api/v1/quiz/generate` 响应 `body.data.questions[0..4].knowledge_point` 5 条值拼接字符串，正则匹配 `单例|SOLID|多态|开闭|策略|观察者|工厂` ≥ 5 次；且 `body.data.title` 不含 `Python` 关键词。

---

## Task 13: 端到端冒烟 2 - 3 对 2 错 → 报告 60% 正确率 + 字段齐全

- **Status**: pending
- **Priority**: HIGH
- **Depends On**: Task 12（题库生成通过）
- **Description**: 承接 Task 12 的 5 道题，手动模拟答题：
  1. 第 1 题单选 → 故意点错项（错误讲解非空）→ 确认 → 下一题；
  2. 第 2 题单选 → 点正确项 → 确认 → XP 动画（正确数 +1）；
  3. 第 3 题多选（正确答案 A+C）→ 选 A+B（漏选 C、多了 B）→ 确认 → is_correct=false；
  4. 第 4 题判断 → 选正确；
  5. 第 5 题单选 → 选正确（最终 3 对 2 错，accuracy = 3/5 = 60）；
  6. 点「查看报告」→ 等待 report/generate 接口 200；
  7. 断言报告页 UI 渲染出：
     - accuracy 环形进度 `60%`；
     - mastered_points ≥ 1 条，weak_points ≥ 1 条；
     - three_line_summary.length === 3（三条字符串）；
     - advice.length ≥ 1；
     - share_quote 是一句中文金句（≥ 5 字）。
- **Acceptance Criteria Addressed**: AC-4、AC-2、AC-3
- **Test Requirements**:
  - **Rule**: report/generate 响应 JSON 字段 `accuracy === 60`；`mastered_points instanceof Array && mastered_points.length > 0`；`weak_points.length > 0`；`three_line_summary.length === 3`；`share_quote.trim().length >= 5`；同时 answer_records[0].is_correct === false，answer_records[2].is_correct === false（多选错）。

---

## Task 14: 错误注入 - 无效 API Key 触发 5003 前端不白屏

- **Status**: pending
- **Priority**: MEDIUM
- **Depends On**: Task 12
- **Description**:
  1. 临时把 `backend/.env` 中 `DEEPSEEK_API_KEY=` 改为 40 位无效随机字符串（如 `sk-invalid-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）；
  2. 重启后端；
  3. 前端首页输入任意合法主题（如「HTTP 协议基础」）→ 点「开始闯关」；
  4. 观察：
     - 不白屏、不 JS 报错导致页面卡死；
     - 最终跳转到失败页 或 Toast 提示，包含按钮「重新生成」+「返回首页」；
     - 接口响应 `body.code === 5003` 或 fixture 兜底 JSON（结构合法），二者满足其一即 Pass。
  5. 还原 `backend/.env` 为真实有效 Key。
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - **Rule**: 错误注入后，前端无 uncaught Error 抛到 console.error；最终 UI 至少存在 1 个可交互按钮（返回首页 或 重新生成），点击能正常跳转不卡死。

---

## Task 15: 答题即时反馈 UI 细节验收（红/绿高亮 + XP 动画 + 讲解非空）

- **Status**: pending
- **Priority**: MEDIUM
- **Depends On**: Task 12（quiz 页可达）
- **Description**: 针对 AC-2、AC-3 的 UI 细节手工或单测验收：
  1. **单选题错题流（AC-2）**：第 1 题选错 → 确认 → 正确选项绿框、错误选项红框；讲解面板展开文字长度 ≥ 10 字；correctCount 不变；currentIndex 点下一题后 +1；
  2. **多选题漏选判错（AC-3）**：正确答案 A+C，用户选 A+B → 确认 → A 绿、C 绿、B 红；answer_record.is_correct === false；XP 数字 **不 +10**；
  3. 进度条视觉：从 1/5→2/5→…→5/5 颜色为暖橙渐变；
- **Acceptance Criteria Addressed**: AC-2、AC-3
- **Test Requirements**:
  - **Rule**: 三条件全满足：(a) 错题 DOM 元素类名含 error 的边框 style 等于红色（#ff6f5d）；正确项含 correct 的边框 style 等于绿色（#38b987）；(b) answer_records[q2].is_correct === false；(c) 讲解面板 explanation 文字长度 ≥ 10 中文字符。

---

## Task 16: 保留页（history/mine/loading + TabBar 三项）可点不报错

- **Status**: pending
- **Priority**: LOW
- **Depends On**: Task 11（构建通过）
- **Description**: MVP 不验收内容但保持可点击：
  1. TabBar 点「历史」和「我的」→ 正常进入对应 pages/history/index、pages/mine/index，无 JS 报错、无空白死页；
  2. 首页（index）点开始 → 进入 loading 页（pages/loading/index）→ loading 文案 10s→20s→30s 自动更新；
  3. 返回不报错；
- **Acceptance Criteria Addressed**: NFR-7（不白屏）
- **Test Requirements**:
  - **Rule**: 手动点击 TabBar 3 项 3 次来回切换，console.error 出现 0 条未捕获异常；3 页均非空白（至少有文字标题或占位 Logo 可见）。

---

## Task 17: Review Phase - 独立审阅生成 review.md + 14 AC 覆盖率表

- **Status**: pending
- **Priority**: HIGH
- **Depends On**: Task 1 ~ Task 16（所有任务 done）
- **Description**: 作为独立 Reviewer（fresh eyes）：
  1. 新建 `.trae/specs/mvp-fish-ai-quiz/review.md`，结构：
     - **Task Execution Summary**：Task 1~16 逐一打勾 done + 备注；
     - **AC Coverage Matrix**：14 条 AC × Task 映射表，每条 AC 标注 Pass/Fail + 证据文件路径；
     - **Evidence Screenshots/Logs**：附 pytest 输出文本片段、dist 大小命令输出、Java 5 题 Network 响应片段；
     - **Final Verdict**：MVP 是否 PASS（14 AC 全部 Pass 才算 Pass，否则 Fail 并列出 reopen 项）；
  2. 若有任意 AC Fail → 创建 reopen 新 Task 18/19/... 回到 Implement Phase 修复；否则 Review Phase 结束。
- **Acceptance Criteria Addressed**: 所有 AC-1 ~ AC-14 最终复核
- **Test Requirements**:
  - **Rule**: review.md 中 AC Coverage Matrix，14 条 AC 全部为 Pass（或 Fail 项均有对应 reopen Task 且已完成后再次 Review 标记 Pass）。

---
