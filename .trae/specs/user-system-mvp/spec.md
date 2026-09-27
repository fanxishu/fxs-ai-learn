# 智能 AI 闯关学习小程序 - 用户系统 MVP 需求规格

## Overview
- **Summary**: 在既有 MVP 核心链路（输入 → 出题 → 答题 → 报告）基础上，扩展微信用户体系与 MySQL 数据持久化，打通登录、鉴权、落库、个人中心、闯关历史回看 5 个模块。
- **Purpose**: 解决当前 MVP 无用户身份、数据关闭即丢失、首页/我的页全是硬编码占位数据的问题，为后续错题本、复习提醒、排行榜等留存能力打好数据结构基础。
- **Target Users**: 微信小程序端的个体学习者，以及项目运营方（查看和分析用户学习数据）。

## Goals
1. 打通微信静默登录 + JWT 可选鉴权，不影响现有匿名体验。
2. 题库、答题记录、报告 3 类核心数据在用户登录态下自动持久化到 MySQL，匿名态不落库。
3. 首页顶部工具栏显示真实昵称与总经验值，替换硬编码的「小皮」和「602」。
4. 个人中心（Mine 页）展示真实的累计闯关次数、答对题数、平均正确率，并显示登录用户头像与可编辑昵称。
5. 个人中心与首页「已完成关卡」区域显示真实的闯关历史列表，支持点击回看报告详情。
6. 经验值按规则自动累加：每完成一次闯关 +10 XP，每答对一题额外 +2 XP。

## Non-Goals
1. **不做**社交 PK、全服排行榜（P2，需要独立对战机制设计）。
2. **不做**错题本 + 艾宾浩斯复习提醒（P1 但逻辑复杂，后续独立迭代）。
3. **不做**分享海报 Canvas 生成（需要独立绘图层）。
4. **不做** VIP 付费与商业化支付链路（P3）。
5. **不做**多源输入扩展（PDF / URL / 视频解析，与用户系统无关）。
6. **不做**首页「未完成关卡」硬编码卡片的改造（数学/科学闯关仍保持原型占位原样）。
7. **不引入** SQLAlchemy / Alembic 等 ORM，按方案文档 §8 建议使用 aiomysql + 手写 SQL + Repository。
8. **不调用**微信 getUserProfile 拉取用户昵称头像（2022 起已被限制），首次注册统一用「学习者」+ 空头像兜底。

## Background & Context
1. 现有项目技术栈：
   - 前端：Taro 4.x + React 18 + TypeScript + Zustand；TabBar 含首页 / 历史 / 我的三页；request() 封装位于 [frontend/src/services/api.ts](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/frontend/src/services/api.ts)。
   - 后端：FastAPI + Pydantic v2 + LangChain + DeepSeek；统一错误码见 [backend/app/core/exceptions.py](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/app/core/exceptions.py)；ApiResponse 包装统一 HTTP 200（见 [backend/app/models/common.py]）。
   - 数据：当前无数据库，题库与报告完全无状态；前端 quizStore 用 Taro.setStorageSync 本地保存 history（最多 50 条），存在丢失与跨设备不同步问题。
2. 已人工确认的 5 个关键技术选型：
   - ORM：**不引入 ORM**，aiomysql 连接池 + 手写 SQL + Repository 封装。
   - JWT：**自动生成 32 字节随机密钥**写入 backend/.env，.env.example 留占位符。
   - 微信登录：**真实调用 jscode2session + dev fallback mock**（USE_MOCK_WX_LOGIN=true 或调用失败时 code 直接当 openid）。
   - 默认昵称：**统一「学习者」+ 空头像**，不尝试静默拉取微信昵称头像。
   - Taro 构建：**完成后端后执行 pnpm install + pnpm build:weapp** 重新生成 dist/。
3. 文档依据：
   - [用户系统需求分析文档.md](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/docs/用户系统需求分析文档.md) — 4 个功能批次与验收标准。
   - [用户系统方案设计文档.md](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/docs/用户系统方案设计文档.md) — 4 张核心表、5 个接口、鉴权策略。
   - [方案设计文档.md](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/docs/方案设计文档.md) §16.1 错误码区间约定。

## Functional Requirements
按需求文档 4 个批次拆分：

- **FR-1 (批次一 · 基础设施)**：MySQL 连接池与 4 张核心表初始化（users / quiz_sessions / answer_records / reports）。
- **FR-2 (批次一)**：`POST /api/v1/user/login` 微信登录接口。接收 wx.login code → 调 jscode2session 拿 openid → 首次 openid 自动注册 users → 返回 JWT token + 新用户对象。
- **FR-3 (批次一)**：JWT 可选鉴权中间件 + get_current_user_id 依赖。无 token 或 token 过期时 quiz/report 接口不报错但 user_id=None；user/* 接口强制返回 2001/2002。
- **FR-4 (批次一)**：前端 App.tsx 启动自动登录。检查本地 token 是否存在，不存在则 wx.login() → 调登录接口 → 保存 token 与 user 基础信息。
- **FR-5 (批次一)**：request() 统一带 token header，401/2001/2002 时自动清空本地登录态。
- **FR-6 (批次二 · 数据落库)**：改造 `POST /quiz/generate`，若有 token 则将生成的 quiz + questions_json 写入 quiz_sessions 并关联 user_id。
- **FR-7 (批次二)**：改造 `POST /report/generate`，若有 token 则将 answer_records + 统计字段 写入 answer_records、报告完整 JSON 写入 reports、按 XP 规则累加 users.total_xp。
- **FR-8 (批次三 · 用户档案)**：`GET /api/v1/user/profile` 返回 id / nickname / avatar_url / total_xp / quiz_count / correct_count / average_accuracy 7 个字段。
- **FR-9 (批次三)**：`PUT /api/v1/user/profile` 允许用户更新 nickname 与 avatar_url，长度/敏感词校验。
- **FR-10 (批次三)**：Mine 页 UI 改造，从接口拉取真实档案与统计数据，移除硬编码的「学习爱好者」和纯本地 stats。
- **FR-11 (批次三)**：Mine 页支持点击昵称弹出输入框修改昵称，调用 PUT 接口更新。
- **FR-12 (批次三)**：首页顶部工具栏显示真实 nickname 与 total_xp（替换「小皮」和硬编码金币 XP 文案）。
- **FR-13 (批次四 · 历史回看)**：`GET /api/v1/user/quizzes?page=1&page_size=10` 分页返回闯关历史列表，支持按创建时间倒序。
- **FR-14 (批次四)**：`GET /api/v1/user/quizzes/{quiz_id}` 返回单次闯关的 questions + answer_records + report 完整数据。
- **FR-15 (批次四)**：Mine 页底部展示闯关历史列表（标题、正确率、时间），首页已完成关卡区域展示最近 3 条历史，点击跳转报告页回看。
- **FR-16 (批次四)**：报告页兼容「前端刚生成」与「从历史接口拉取」两种数据来源，均能正确渲染。

## Non-Functional Requirements
- **NFR-1 (TDD)**：所有后端新增模块（auth / db / repositories / services / routes）必须 100% 单测覆盖核心分支，运行 `cd backend && pytest -v --cov=app --cov-report=term-missing` 所有用例通过。
- **NFR-2 (兼容匿名)**：quiz/generate 与 report/generate 两个核心接口在无 token、token 无效、token 过期三种情况下，必须返回与改造前完全相同的 body 结构与 code 值，不抛新异常，不中断现有玩家匿名体验。
- **NFR-3 (JSON 稳定性)**：report.generate 返回的 accuracy / mastered_points / three_line_summary / advice / share_quote 字段结构必须与现有 quiz_chain.py 一致，报告页 WXML 不需要再因数据结构变动修改。
- **NFR-4 (安全)**：
  - JWT 密钥长度 >= 256 bit（32 字节）；token 默认有效期 7 天。
  - 用户 PUT 更新 nickname/avatar_url 时，经 content_filter DFA 敏感词过滤，命中返回 3001。
  - user/quizzes/:quiz_id 必须校验 quiz_session.user_id == 当前 user_id，越权访问返回 4001 QUIZ_NOT_FOUND（不泄露存在性）。
- **NFR-5 (UI 严格对齐原型)**：首页和 Mine 页的布局、颜色、间距、组件尺寸严格遵循 `docs/Copilot生成的原型图/` 三个 HTML 原型，不允许自行发挥视觉风格。Mine 页的 3 张统计卡（总闯关 / 正确率 / 已答题数）保持原型中的橙色渐变视觉。
- **NFR-6 (性能)**：MySQL 分页查询历史列表，单页 10 条响应 p95 < 150 ms（本地单测）。
- **NFR-7 (XP 原子性)**：累加 total_xp 必须使用单条 SQL `UPDATE users SET total_xp = total_xp + %s WHERE id = %s` 执行，禁止先读再写，避免并发闯关竞态。

## Constraints
- **Technical**:
  - 后端 Python 3.11+ / FastAPI / Pydantic v2；数据库 MySQL 8.x + aiomysql 异步池；JWT 使用 PyJWT 库；禁止引入 ORM。
  - 前端 Taro 4.x + React 18 + TS；用户系统新增 TS 类型放入 frontend/src/types/（新建 user.ts）。
  - API 响应永远外层 `ApiResponse(code/message/data)` 包、永远 HTTP 200；错误码严格复用 exceptions.py::ErrorCode 的区间（2001 未登录 / 2002 token 过期 / 3001 内容违规 / 4000 参数非法 / 5000 内部错误）。
  - `frontend/project.config.json` 的 miniprogramRoot 已设为 dist/，src 修改必须通过 `pnpm build:weapp` 覆盖 dist 才能生效。
- **Business**:
  - 绝不破坏现有核心链路；匿名用户做完一次「出题→答题→报告」的行为、返回值、UI 交互必须完全等价于改造前。
  - 经验值规则固定：完成闯关 +10，答对一题 +2，不设扣分或扣 XP 机制（错题不扣 XP）。
  - 首次注册默认昵称「学习者」，默认 avatar_url 空字符串；禁止从微信侧拉取任何用户个人信息。
- **Dependencies**:
  - 真实微信登录依赖 AppID=wxc2be9226cb6b2de7 / AppSecret 已写入 backend/.env（见 WECHAT_APPID / WECHAT_APPSECRET）。
  - MySQL 已在本地准备：127.0.0.1:3306 / root / root / 库名 fxs_ai_learn。
  - 前端依赖安装：必须先成功 `cd frontend && pnpm install` 才能 build。

## Assumptions
1. MySQL 服务已运行且 root/root 账号可用，库名 fxs_ai_learn 已创建并设置 `DEFAULT CHARACTER SET utf8mb4`（若未创建，初始化模块自动执行 CREATE DATABASE IF NOT EXISTS）。
2. 小程序开发者工具中，project.config.json 的 appid 已设为 wxc2be9226cb6b2de7，且勾选了「不校验合法域名」以便本地 127.0.0.1:8443 HTTPS 代理联调。
3. Taro build 产生的新 dist 会被微信开发者工具自动热重载；如不生效，提示用户手动点「重新编译」。
4. 方案文档 §5.3 建议 users / quiz_sessions / answer_records / reports 四张表全部使用 BIGINT 主键，项目 ID 生成采用雪花算法或 UUID_SHORT；本次为 MVP 简化，使用 MySQL AUTO_INCREMENT BIGINT。
5. report.generate 现有 quiz_id 字段格式如 `spring-quiz-001` 或 UUID，只要全局唯一即可直接存入 quiz_sessions.quiz_id（VARCHAR 64）。

## Acceptance Criteria

### AC-1: 微信登录与 JWT 全链路
- **Type**: `rule`
- **Given**: 小程序首次启动，本地无 token
- **When**: App 启动 → wx.login() 获取 code → POST /user/login → 返回 token → 保存 token → 发起 quiz/generate（带 Authorization: Bearer <token>）
- **Then**: users 表出现新 openid 行；返回 token 解码后含 user_id 与 exp；quiz/generate 注入请求上下文 user_id 非空
- **Pass Condition**: 本地 pytest test_user_login.py 覆盖：新 openid 注册、重复 openid 复用同 user_id、code 为空抛 4000、jscode2session 失败走 fallback mock 三种情况全部通过
- **Evidence**: `cd backend && pytest tests/test_user_login.py -v` 全绿

### AC-2: 可选鉴权兼容匿名模式
- **Type**: `rule`
- **Given**: 同一 quiz/generate 请求分别以「无 token」「伪造 token」「过期 token」三种 header 发起
- **When**: FastAPI 路由走可选 Depends(get_current_user_id_optional)
- **Then**: 三种情况下 quiz/generate 的 code=0，questions 数组正常返回；user_id=None，不写入 quiz_sessions 表
- **Pass Condition**: 单测 `tests/test_auth_middleware.py` 中 3 种匿名分支 + 强制鉴权接口 2001/2002 返回全部通过
- **Evidence**: pytest 用例 exit 0

### AC-3: 闯关数据落库正确性
- **Type**: `rule`
- **Given**: 登录用户完成一次 5 题闯关（对 3 错 2）
- **When**: 先走 quiz/generate → 前端答题 → report/generate
- **Then**: quiz_sessions 有 quiz_id + user_id 对应记录；answer_records 有 records_json 且 correct_count=3、accuracy=60；reports 有完整 report_json；users.total_xp 增加 10+3×2 = 16
- **Pass Condition**: `tests/test_persistence.py` 断言 4 表行数量、accuracy 数值、XP 累加均正确；并发双写 2 次 XP 合计正确（无竞态丢失）
- **Evidence**: pytest 用例 exit 0

### AC-4: 用户档案与统计口径
- **Type**: `rule`
- **Given**: 同用户完成 2 次闯关：第 1 次 5 题对 3（60%），第 2 次 5 题对 5（100%）
- **When**: GET /user/profile
- **Then**: quiz_count=2；correct_count=8；average_accuracy=ROUND((3+5)/(5+5)*100, 0)=80；total_xp=(10+6)+(10+10)=36
- **Pass Condition**: pytest 断言 4 个统计字段精确值，平均正确率采用「总对题数 / 总题数」口径而非两次平均值的平均
- **Evidence**: pytest 用例 exit 0

### AC-5: 闯关历史分页与越权防护
- **Type**: `rule`
- **Given**: UserA 有 15 条闯关历史，UserB 有 3 条
- **When**: UserA GET /user/quizzes?page=2&page_size=10 → 拿到 5 条倒序；UserB 尝试 GET /user/quizzes/<userA_quiz_id>
- **Then**: UserA 分页 total=15 / page=2 / items 5 条全为自己；UserB 拿别人 quiz_id 返回 4001 QUIZ_NOT_FOUND（不提示越权）
- **Pass Condition**: `tests/test_history_api.py` 全部用例通过（分页边界、越权、空列表、单条详情）
- **Evidence**: pytest 用例 exit 0

### AC-6: 昵称更新敏感词过滤
- **Type**: `rule`
- **Given**: 登录用户 PUT /user/profile { nickname: <脏词> }
- **When**: 经 DFA 过滤命中
- **Then**: 返回 code=3001；DB 中 nickname 未被更新
- **Pass Condition**: `tests/test_content_filter.py` 新增的昵称分支与现有输入过滤同样通过
- **Evidence**: pytest 用例 exit 0

### AC-7: 核心匿名链路 100% 回归
- **Type**: `rule`
- **Given**: 完全不登录，执行完整 quiz → report 流程
- **When**: 与改造前相同 payload 调 quiz/generate + report/generate
- **Then**: 所有 code=0，accuracy、mastered_points 结构完全一致；quiz_sessions / answer_records / reports 三张表不新增行
- **Pass Condition**: 既有 `tests/test_quiz_api.py` / `tests/test_report_api.py` / `tests/test_scoring_service.py` 未修改任何断言，全部通过
- **Evidence**: `cd backend && pytest tests/test_quiz_api.py tests/test_report_api.py tests/test_scoring_service.py -v` 全绿

### AC-8: 自动登录与 Header 注入
- **Type**: `rubric`
- **Dimension**: 前端登录态集成质量
- **Scale**: 1-5
- **Anchors**: 1 = 未接入自动登录或 token 从未注入；3 = App 启动自动登录，但 Mine/首页未展示真实数据；5 = 每次启动自动登录、token 自动注入所有请求、401 自动清理、真实 nickname/XP 正确展示
- **Pass Threshold**: >= 4
- **Evidence**: 微信开发者工具真机调试截图 + Console 连续 5 次请求日志显示 Authorization: Bearer xxx 非空

### AC-9: 首页 & Mine 页 UI 对齐原型
- **Type**: `rubric`
- **Dimension**: UI 还原度与数据真实性
- **Scale**: 1-5
- **Anchors**: 1 = 仍用硬编码数据，改动 < 30%；3 = 数据接了但布局/颜色与原型有明显偏差；5 = 布局、配色、间距、字号与原型截图完全一致，Mine 统计卡橙色渐变、历史列表卡圆角、首页工具栏昵称+XP 位置都正确
- **Pass Threshold**: >= 4
- **Evidence**: 微信开发者工具截图与 `docs/Copilot生成的原型图/02-extended-features.html` 的 Mine 页关键帧对比

### AC-10: 后端代码质量与 TDD 覆盖率
- **Type**: `rubric`
- **Dimension**: 后端代码质量
- **Scale**: 1-5
- **Anchors**: 1 = 没有 Repository 层，SQL 散落在 route；3 = 有 Repository 封装但单测覆盖 < 70%；5 = Repository + Service + Route 分层清晰，所有新增模块 pytest-cov 行覆盖 >= 90%，无 SQL 拼接注入风险
- **Pass Threshold**: >= 4
- **Evidence**: `pytest --cov=app --cov-report=term-missing` 输出快照

## Open Questions
- 所有 5 个开放问题已由用户在 2026-09-26 会话中选择「推荐方案」确认，无剩余开放问题。
