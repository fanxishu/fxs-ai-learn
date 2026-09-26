# 鱼皮 AI 闯关学习小程序 - 用户系统 MVP 实施计划

---

## Task 1: 后端依赖安装 + 配置扩展（env/config/requirements）
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: None
- **Description**:
  - 在 backend/requirements.txt 中新增：`aiomysql`、`PyJWT`、`cryptography` 3 个依赖。
  - 升级 backend/.env：新增 JWT_SECRET_KEY（用 `python -c "import secrets;print(secrets.token_urlsafe(32))"` 生成随机值）、JWT_ALGORITHM=HS256、JWT_EXPIRE_DAYS=7、USE_MOCK_WX_LOGIN=false 4 个字段。
  - backend/.env.example 同步加相同字段的占位符。
  - 更新 backend/app/core/config.py：
    - 增加 DB_DRIVER / DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME / DB_CHARSET 读取与 property `database_url` 自动合成 `mysql+aiomysql://user:pass@host:port/db?charset=utf8mb4`。
    - 增加 JWT_* 与 WECHAT_* 字段读取。
- **Acceptance Criteria Addressed**: AC-1, AC-7, NFR-1, NFR-4
- **Test Requirements**:
  - `rule` TR-1.1: `from app.core.config import settings; assert settings.database_url.startswith("mysql+aiomysql://")` pytest 通过
  - `rule` TR-1.2: 生成的 JWT_SECRET_KEY 长度 >= 43 字符（32字节 urlsafe），.env.example 对应为 `your_jwt_secret_here`
- **Notes**: 这是后续所有 DB/JWT 模块的前置依赖，必须第一个完成并安装 `pip install -r requirements.txt`

---

## Task 2: DB 模块（连接池 + 4 张表初始化 SQL）
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 1
- **Description**:
  - 新建 backend/app/core/db.py：
    - `create_db_pool()` 创建 aiomysql.Pool，lifespan 中 init，app shutdown 时 close。
    - `create_tables_if_not_exists()` 执行建表 SQL，保证幂等（CREATE TABLE IF NOT EXISTS）。
    - 4 张表按方案文档 §5.3：
      - users（id bigint PK auto_increment / openid varchar(64) UNIQUE / nickname varchar(100) / avatar_url varchar(500) / total_xp int DEFAULT 0 / created_at DATETIME / updated_at DATETIME）
      - quiz_sessions（id bigint PK / quiz_id varchar(64) UNIQUE / user_id bigint INDEX / title / summary / user_input TEXT / questions_json JSON / created_at）
      - answer_records（id bigint PK / quiz_id varchar(64) UNIQUE / user_id bigint INDEX / records_json JSON / total_questions int / correct_count int / accuracy DECIMAL(5,2) / created_at）
      - reports（id bigint PK / quiz_id varchar(64) UNIQUE / user_id bigint INDEX / report_json JSON / created_at）
    - 所有表 utf8mb4 + InnoDB。
  - 在 main.py lifespan 中先 `await create_db_pool()` → `await create_tables_if_not_exists()` → setup_logging。
- **Acceptance Criteria Addressed**: FR-1, NFR-6
- **Test Requirements**:
  - `rule` TR-2.1: pytest fixture 连接真实 MySQL → SHOW TABLES 后断言 4 张表名出现（users/quiz_sessions/answer_records/reports）
  - `rule` TR-2.2: 插入再查询 users (openid='test_openid_001') → 断言 user_id 生成自增正确
  - `rubric` TR-2.3: SQL 注入安全性；scale 1-5；1=直接 f-string 拼 value；3=参数化但表名未固定；5=100% %s 参数化值、表名常量、无动态拼接；threshold >= 4
- **Notes**: 单测使用 pytest 独立库 fxs_ai_test，避免污染正式库数据（测试后 DROP TABLE IF EXISTS ...）

---

## Task 3: JWT 鉴权模块（create/parse/2 个依赖）
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 1
- **Description**:
  - 新建 backend/app/core/auth.py：
    - `create_access_token(user_id: int, openid: str) -> str`，payload = `sub: str(user_id)`, `openid`, `exp: now + JWT_EXPIRE_DAYS days`，PyJWT encode HS256。
    - `parse_token(token: str) -> dict | None`：捕获 ExpiredSignature / DecodeError，分别返回 `expired` / `invalid` / payload dict。
    - Depends `get_current_user_id_required`：读 Authorization: Bearer xxx → parse → 抛 2001 或 2002。
    - Depends `get_current_user_id_optional`：同上但不抛异常，返回 `int | None`（quiz / report 两个接口用）。
  - 在 backend/tests/ 新建 test_auth.py，覆盖：新 token 解析、过期 token、伪造 token、空 header、Bearer 无空格 5 种情况。
- **Acceptance Criteria Addressed**: FR-3, AC-2, NFR-4
- **Test Requirements**:
  - `rule` TR-3.1: token 生成后 1 秒内解析 sub / openid / exp 正确
  - `rule` TR-3.2: expired case 抛 2002，invalid case 抛 2001（required 依赖），optional 依赖均返回 None
  - `rule` TR-3.3: `JWT_ALGORITHM=HS256` 且未显式传算法时 decode 仍限定 algorithms=["HS256"]（防 alg:none 攻击）
- **Notes**: 算法白名单，避免 PyJWT CVE 漏洞

---

## Task 4: Repository 层封装（4 个 Repository 类）
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 2
- **Description**:
  - 新建 backend/app/repositories/ 目录：
    - `user_repository.py`: `get_by_openid(openid)`、`create_user(openid, nickname, avatar_url)`、`get_by_id(user_id)`、`update_profile(user_id, nickname, avatar_url)`、`add_xp(user_id, xp_delta)`（单条 UPDATE ... SET total_xp = total_xp + %s WHERE id=%s 保证原子）、`get_profile_stats(user_id)` 联合查 quiz_sessions/answer_records 聚合 quiz_count/correct_count/average_accuracy。
    - `quiz_repository.py`: `save_session(quiz_id, user_id, title, summary, user_input, questions_json)`、`get_session_by_quiz_id(quiz_id, user_id)`。
    - `record_repository.py`: `save_records(quiz_id, user_id, records_json, total_questions, correct_count, accuracy)`、`list_by_user_id_paged(user_id, page, page_size)`、`count_by_user_id(user_id)`。
    - `report_repository.py`: `save_report(quiz_id, user_id, report_json)`、`get_report_by_quiz_id(quiz_id, user_id)`。
  - 全部 100% aiomysql `%s` 参数化执行，Repository 方法接受 pool 作为参数，便于单测 fixture 注入。
  - 新建 test_repositories.py，4 个 Repository 覆盖增、查、分页、原子 XP 累加 2 次无竞态 用例。
- **Acceptance Criteria Addressed**: FR-6, FR-7, FR-8, FR-9, FR-13, FR-14, AC-3, AC-4, NFR-7
- **Test Requirements**:
  - `rule` TR-4.1: add_xp 连续并发 2 次，SELECT FOR UPDATE-like 方式或直接 UPDATE 累加，结果 = 初始 + delta1 + delta2
  - `rule` TR-4.2: get_session_by_quiz_id(别人的 quiz_id, my_user_id) → 返回 None（越权底层已过滤）
  - `rubric` TR-4.3: Repository 代码分层清晰度；scale 1-5；1=全部一个大文件；3=分文件但 Repository 与 Service 混用；5=4 个文件独立、每个方法单一职责、无重复 SQL；threshold >= 4
- **Notes**: profile_stats 聚合 SQL 三表 join（user_id 过滤）+ 子查询算平均正确率口径：correct_count 总和 / total_questions 总和 * 100，四舍五入取整

---

## Task 5: 微信登录 + User Service + user 路由
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 3, Task 4
- **Description**:
  - 新建 backend/app/services/user_service.py：
    - `wx_login(code: str) -> tuple[str, User]`：
      1. 若 settings.USE_MOCK_WX_LOGIN=true → mock 模式：openid = `mock_` + code。
      2. 否则用 httpx.AsyncClient GET https://api.weixin.qq.com/sns/jscode2session?appid=...&secret=...&js_code=code&grant_type=authorization_code。
      3. 若微信返回 errcode 非 0 → fallback mock（openid = `fallback_` + code[:16]），打 warning 日志，**不抛异常**（保证 dev 模式稳定）。
      4. user_repo.get_by_openid(openid) 不存在则 create_user，默认 nickname=「学习者」，avatar_url=''，total_xp=0。
      5. create_access_token(user.id, openid)，返回 (token, user)。
    - `get_profile(user_id)` → 组装 {id, nickname, avatar_url, total_xp, quiz_count, correct_count, average_accuracy}。
    - `update_profile(user_id, nickname, avatar_url)` → 先 DFA 过 content_filter，命中抛 InputContentViolationError(3001)，否则更新 DB。
  - 新建 backend/app/api/v1/routes/user.py，5 个接口（方案文档 §5.5）：
    - POST /user/login（公开，无需鉴权）→ ok_response({token, user})。
    - GET /user/profile（required）→ ok_response(profile)。
    - PUT /user/profile（required）→ 参数校验 nickname 1..20 字符，ok_response({updated: true})。
    - GET /user/quizzes?page&page_size（required）→ 分页 items + total + page + page_size。
    - GET /user/quizzes/{quiz_id}（required）→ 组合 questions_json + records_json + report_json 返回；不存在/越权抛 4001。
  - 在 backend/app/api/v1/routes/__init__.py（api_router）include_router user.router。
  - 新建 backend/tests/test_user_api.py + test_user_login_service.py，覆盖所有接口、fallback mock、nickname 脏词、分页越权 8 个用例。
- **Acceptance Criteria Addressed**: FR-2, FR-8, FR-9, FR-13, FR-14, AC-1, AC-4, AC-5, AC-6
- **Test Requirements**:
  - `rule` TR-5.1: 新 code 登录 → token 可解析；第二次同 code 登录 → 同一 user_id（不重复创建）
  - `rule` TR-5.2: nickname=敏感词 → 3001；nickname=空或 >20 → 4000
  - `rule` TR-5.3: GET /user/quizzes/{quiz_id of other} → 4001，错误文案为「题库不存在或已过期」不泄露越权
  - `rule` TR-5.4: USE_MOCK_WX_LOGIN=true 情况下，同 code 返回的 openid 一致
- **Notes**: 微信 HTTP 请求 timeout 设 5s，任何异常都走 fallback，保证开发体验稳定

---

## Task 6: 改造 quiz/generate 与 report/generate 接口接入落库
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 3, Task 4, Task 5
- **Description**:
  - 改造 [backend/app/api/v1/routes/quiz.py](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/app/api/v1/routes/quiz.py) 的 generate_quiz：
    - 入参数不变；新增 Depends(get_current_user_id_optional) → user_id: int | None。
    - 调用链成功后拿到 QuizGenerateResult；**若 user_id 非空** → quiz_repo.save_session(quiz_id=result.quiz_id, user_id=user_id, title=result.title, summary=result.summary, user_input=raw.user_input, questions_json=questions 完整 JSON)。
    - 返回结构完全不变，确保 FR-7 匿名模式零差异。
  - 改造 [backend/app/api/v1/routes/report.py](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/app/api/v1/routes/report.py) 的 generate_report：
    - 新增 optional user_id。
    - 计算统计：total_questions=len(req.questions)，correct_count=sum(r.is_correct for r in req.answer_records)，accuracy=round(correct_count/total_questions*100, 2) if total else 0。
    - **若 user_id 非空** 三件事：
      1. record_repo.save_records(req.quiz_id, user_id, records_json=answer_records.dump(), total_questions, correct_count, accuracy)
      2. report_repo.save_report(req.quiz_id, user_id, report_json=report_result.dump())
      3. xp = 10 + 2*correct_count → user_repo.add_xp(user_id, xp)（原子 UPDATE）
    - 返回 ReportGenerateResult 结构完全不变，不把 XP 或落库信息暴露给前端。
  - 新建 backend/tests/test_persistence.py，覆盖：有登录态 3 表行数 + XP 正确；无登录态 3 表零新增；两次并发闯关 report XP 累加正确。
- **Acceptance Criteria Addressed**: FR-6, FR-7, AC-3, AC-7, NFR-2, NFR-3, NFR-7
- **Test Requirements**:
  - `rule` TR-6.1: 匿名调用 quiz/generate + report/generate → quiz_sessions.count()==0 / answer_records.count()==0 / reports.count()==0
  - `rule` TR-6.2: 登录态 5 题（对 3）→ total_xp = 老值 + 16；answer_records.accuracy=60.00
  - `rule` TR-6.3: report 返回的 accuracy / mastered_points / advice / share_quote 字段 JSON key 名与改造前字节级一致
  - `rule` TR-6.4: 既有 test_quiz_api.py, test_report_api.py, test_scoring_service.py 全部 100% 通过，无需修改断言
- **Notes**: 这是最容易破坏核心链路的一步，TR-6.4 是硬指标，任何老用例失败都必须先修复再推进

---

## Task 7: 后端全量 TDD 验证 + pytest-cov 报告
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 1-6
- **Description**:
  - 在沙箱虚拟环境中 `cd backend && pip install -r requirements.txt` 一次确保新依赖可装。
  - 执行完整 `cd backend && pytest tests/ -v --cov=app --cov-report=term-missing --tb=short` 所有用例。
  - 保证所有新增 + 原有用例 100% 通过；新增模块 auth / db / repositories / services.user_service / routes.user 的 coverage >= 90%。
  - 任一用例失败必须修复并重跑，直到 0 failures。
- **Acceptance Criteria Addressed**: NFR-1, AC-1 through AC-7
- **Test Requirements**:
  - `rule` TR-7.1: `pytest` exit code = 0
  - `rubric` TR-7.2: 新增模块覆盖度；scale 1-5；1=<50%；3=70%-89%；5=>=90%；threshold >= 4
- **Notes**: 后端任务完成的 Exit Gate，只有 TR-7.1 通过才能进入前端开发

---

## Task 8: 前端类型扩展 + 自动登录 + request token 注入
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 7
- **Description**:
  - 新建 frontend/src/types/user.ts：
    - `LoginRequest { code: string }`、`LoginResponse { token: string; user: UserProfile }`
    - `UserProfile { id: number; nickname: string; avatar_url: string; total_xp: number; quiz_count?: number; correct_count?: number; average_accuracy?: number }`
    - `HistoryListResponse { items: QuizHistoryItem[]; total: number; page: number; page_size: number }`
    - `QuizHistoryItem { quiz_id: string; title: string; accuracy: number; question_count: number; created_at: string }`
    - `QuizDetailResponse { quiz_session: {...}; questions: Question[]; answer_records: AnswerRecord[]; report: ReportGenerateResult }`
  - 改造 frontend/src/services/api.ts 的 `request()`：
    - header 中若存在 Taro.getStorageSync('auth_token') 则注入 `{ Authorization: 'Bearer ' + token }`。
    - response body 中 code === 2001 or 2002 时 Taro.removeStorageSync('auth_token') + remove user_profile，再 Toast 提示重新登录。
  - 改造 frontend/src/app.tsx useDidShow（或首次启动 useEffect）自动登录：
    - 若无 `auth_token` 则 `Taro.login()` → 拿 code → 调 API.userLogin(code) → 存 auth_token + user_profile。
    - 有 token 则跳过（避免重复登录）。
    - 登录接口失败（code!=0）→ 仅 warning 日志 + 不阻断匿名体验。
  - 扩展 API 对象：`userLogin / getUserProfile / updateUserProfile / listHistory / getHistoryDetail` 5 个函数。
  - 新建 frontend/src/store/user.ts（zustand）：
    - `user: UserProfile | null`、`token: string | null`、`setLoginResult`、`clearLogin`、`refreshProfile`、`isLoggedIn`。
- **Acceptance Criteria Addressed**: FR-4, FR-5, AC-8
- **Test Requirements**:
  - `rubric` TR-8.1: 登录态集成质量（对应 AC-8）；阈值 >= 4，实机截图验证
  - `rule` TR-8.2: request() 注入 header 后 Taro.request 实际 headers.Authorization 检查（调试期 console 确认）
- **Notes**: 前端开发第一块，打通所有后续页面的数据基础

---

## Task 9: 首页改造（昵称 / XP / 已完成关卡真实数据）
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 8
- **Description**:
  - 改造 [frontend/src/pages/index/index.tsx](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/frontend/src/pages/index/index.tsx)：
    - 顶部品牌右侧 CoinBadge 替换为：从 userStore 读 `total_xp`，显示 `XP {total_xp || 0}`；若未登录显示「登录同步进度」。
    - 欢迎语区（hero 开头问候 + 昵称）：从 userStore 读 nickname，缺省用「同学」；登录态优先展示后端真实昵称，否则本地。
    - 已完成关卡区（当前从 quizStore.history 本地取 3 条）：有登录态时从 API.listHistory(page=1,page_size=3) 拉取 items 展示；无登录态回退本地 history。UI 与原型完全一致。
    - useDidShow 触发 refreshProfile + reload history。
  - SCSS 颜色、字号、间距按原型，不做视觉改动。
- **Acceptance Criteria Addressed**: FR-12, FR-15, AC-9
- **Test Requirements**:
  - `rubric` TR-9.1: UI 对齐度（对应 AC-9 首页部分）；阈值 >= 4
  - `rule` TR-9.2: 有登录态做完新闯关 → 回到首页 total_xp 已自动增加（需二次刷新或 useDidShow）

---

## Task 10: Mine 页改造（真实档案 + 可编辑昵称 + 统计 + 历史列表）
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 8
- **Description**:
  - 改造 [frontend/src/pages/mine/index.tsx](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/frontend/src/pages/mine/index.tsx)：
    - 头部 profile 块：
      - Avatar：若 user.avatar_url 非空用 Taro.Image 展示，否则展示默认鱼 🐟 emoji 圆块。
      - Nickname：可点击，点后 Taro.showModal 带 editable=true 输入框改昵称，调用 API.updateUserProfile，成功后 userStore.setNickname。
      - Subtitle：`累计闯关 {quiz_count} 次 · 平均正确率 {acc}%`，从 profile 接口取值。
    - 统计卡 3 张（总闯关次数 / 平均正确率 / 已答题数）：全部用接口字段，不要从本地 quizStore.history 累计。
    - 菜单卡 3 项保留原样（敬请期待 toast）。
    - 菜单卡下方新增「闯关历史」卡：
      - 标题「闯关历史」+ 右上角「查看全部 →」（暂跳 history tab 页）。
      - 列表项：title（题目标题）、副标「{acc}% 正确 · {questions}题 · {created_at}」，点击 → 调 API.getHistoryDetail → 存 quizStore session/records/report → navigateTo /pages/report/index。
      - 空态：`还没有闯关记录，去首页开始第一次学习吧 🏃`。
  - useDidShow：自动调用 refreshProfile + listHistory(page=1,page_size=20)。
- **Acceptance Criteria Addressed**: FR-10, FR-11, FR-15, AC-9
- **Test Requirements**:
  - `rubric` TR-10.1: UI 对齐度（对应 AC-9 Mine 页部分）；阈值 >= 4
  - `rule` TR-10.2: nickname 修改弹窗输入脏词 → 接口返回 3001 → Toast 文案正确、DB 未变
  - `rule` TR-10.3: 历史列表项点击 → 成功跳 report 页显示完整报告不报错

---

## Task 11: 前端 report 页兼容历史详情来源
- **Status**: `pending`
- **Priority**: `medium`
- **Depends On**: Task 10
- **Description**:
  - 检查 [frontend/src/pages/report/index.tsx](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/frontend/src/pages/report/index.tsx) 的 onLoad / 初始化逻辑。
  - 新支持来源：如果是从 Mine 页历史项点击进入，直接用 quizStore 已预存的 questions / answer_records / report 渲染；不走 report/generate。
  - 保证 displayRecords 合成与分享金句、建议块在两种来源下都正常工作，不要出现 undefined。
- **Acceptance Criteria Addressed**: FR-16, AC-9
- **Test Requirements**:
  - `rule` TR-11.1: 历史详情无 report（极端情况）时，答题回顾块仍能显示题目+答案+正确率，AI 建议块显示占位「AI 总结未保留」
  - `rubric` TR-11.2: 两种来源 UI 一致性；scale 1-5；1=完全不同；3=关键字段对但样式偏差；5=视觉 100% 一致；threshold >= 4

---

## Task 12: 前端 Taro build 构建与集成验证
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 9, 10, 11
- **Description**:
  - `cd frontend && pnpm install`（若 node_modules 已存在则跳过，耗时较长）。
  - 设置 `TARO_HOME=frontend/.taro-home` 规避沙箱权限。
  - `pnpm build:weapp`，若 SCSS 变量缺失或构建失败，按报错逐项修复（参考上次 theme.scss 变量修复）。
  - 构建完成后对 dist 目录执行脚本（如有必要）去 BOM（UTF-8 无 BOM），避免微信 SyntaxError `unexpected ﻿ at pos 1`。
  - 最后验证 dist/app.json / pages/**.js 是否存在 ，无 BOM。
- **Acceptance Criteria Addressed**: NFR-5, AC-8, AC-9
- **Test Requirements**:
  - `rule` TR-12.1: build exit code 0，dist/pages 下 index / quiz / report / mine / history 5 个页面都有 index.js / index.wxml / index.wxss
  - `rule` TR-12.2: dist 下所有 JSON / WXML / JS 文件首字节不是 U+FEFF（用 node 脚本验证）
- **Notes**: 沙箱 npm 构建失败时按错误拆分短命令重试，超时则分步（先 pnpm install，再独立 build）

---

## Task 13: git 提交与 push（最终交付）
- **Status**: `pending`
- **Priority**: `high`
- **Depends On**: Task 7, Task 12
- **Description**:
  - `git status` 检查未提交文件，确保 backend/.env 不被列入，任何 __*.js 临时脚本通过 .gitignore 忽略。
  - 分两次 commit：
    - Commit 1 feat(backend): 用户系统 MVP 后端（login/jwt/mysql/repository/4 表/改造 quiz&report 落库 + TDD 100%）。
    - Commit 2 feat(frontend): 用户系统 MVP 前端（自动登录/token 注入/昵称 XP/ 个人中心改造 + 历史回看 + dist 更新）。
  - `git -c http.proxy= -c https.proxy= push origin main`，返回 exit 0 成功。
  - 最后告知用户：commit hash、可在 GitHub 对比的 diff 范围，以及后续微信开发者工具验证步骤。
- **Acceptance Criteria Addressed**: 全量交付物
- **Test Requirements**:
  - `rule` TR-13.1: push exit code 0，git log --oneline -5 显示两次新 commit
  - `rule` TR-13.2: `git show HEAD --stat | grep ".env$" 2>/dev/null` 空（.env 未提交）

---
