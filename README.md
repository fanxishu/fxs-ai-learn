# 智能 AI 闯关学习小程序（MVP）

AI 生成题目 → 用户答题闯关 → AI 生成分析报告的微信小程序 MVP。

## 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 前端 | Taro + React 18 + TypeScript + Webpack5 + Sass(CSS Modules) + Zustand 4.5 | Taro 4.0.9 |
| 后端 | Python + FastAPI + Pydantic v2 + LangChain 1.4 | Python 3.14.7 |
| AI | DeepSeek Chat (`deepseek-chat`)，支持 USE_MOCK_LLM fixture 硬兜底 | base_url: https://api.deepseek.com/v1 |
| 测试 | pytest 9.1.1 + pytest-asyncio 1.4.0 + httpx 0.28 ASGITransport | 61/61 passed |

## 目录结构

```
fxs-ai-learn/
├── backend/                    # FastAPI 后端（独立子目录）
│   ├── .venv/                  # Python 虚拟环境（项目内自建）
│   ├── app/
│   │   ├── core/               # config / logging / exceptions
│   │   ├── models/             # Pydantic v2 schema
│   │   ├── routes/             # /health /quiz /report HTTP 路由
│   │   ├── services/           # scoring_service / langchain_factory / quiz_chain / report_chain
│   │   ├── utils/              # text_cleaner / content_filter
│   │   └── main.py             # FastAPI create_app + 3 exception handler → 永远 HTTP 200 ApiResponse
│   ├── tests/                  # 7 模块 61 条 pytest（TDD 全绿）
│   │   └── fixtures/quiz_fixture_5q.json
│   └── requirements.txt
├── frontend/                   # Taro 4.x 小程序前端（独立子目录）
│   ├── config/                 # dev.ts / prod.ts / index.ts（sass.resource → tokens.scss）
│   ├── src/
│   │   ├── pages/              # 4 路由：home / loading / quiz / report
│   │   ├── components/         # 10 业务组件库（AppButton/AppInput/Chip/CoinBadge/ProgressTrack/RingProgress/QuizOption/ExplainBox/NoteCard/StateBadge）
│   │   ├── api/request.ts      # Taro.request 统一封装 + API.generateQuiz/generateReport
│   │   ├── store/quiz.ts       # Zustand quizStore
│   │   └── styles/tokens.scss  # 8 Design Tokens Copilot 原型
│   ├── package.json            # pnpm + taro 4.0.9 + react 18
│   └── .env.development        # TARO_APP_API_BASE=http://127.0.0.1:8000
├── docs/                       # 需求 / 方案 / 3 份 Copilot 原型 HTML
└── scripts/start-dev.ps1       # 一键并行启动后端 + 前端
```

## 环境要求

- Windows 10/11 PowerShell 5+
- Python 3.14.7 安装路径：`C:\ruanjian\python3\python.exe`（可根据实际情况修改）
- Node.js 18+ + pnpm（小程序包体积敏感，使用 pnpm 严格管理依赖）
- 微信开发者工具（最新稳定版）
- （可选）DeepSeek API Key：若不提供，**默认 USE_MOCK_LLM=true** 读 fixture JSON，全链路可跑通

## 5 步启动

### ① 安装后端依赖 & 创建虚拟环境（仅首次）

```powershell
cd backend
C:\ruanjian\python3\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> 若机器 Python 不在 `C:\ruanjian\python3\`，改成实际路径即可。虚拟环境必须建在 `backend/.venv/`（项目内），避免写入 AppData 受限目录。

### ② 安装前端依赖（仅首次）

```powershell
cd frontend
pnpm install
```

> pnpm 未安装？`npm i -g pnpm` 先装；Taro 4.0.9 锁版本在 package.json `overrides` 中，请勿随意升级。

### ③ 后端自测（必须 61 passed）

```powershell
cd backend
$env:USE_MOCK_LLM="true"
.\.venv\Scripts\python.exe -m pytest tests -v
# 预期输出：============================= 61 passed in 0.20s =============================
```

| 模块 | 数量 | 覆盖 |
|---|---|---|
| test_health | 1 | /health 端点 |
| test_prompt_contract | 19 | Pydantic 模型：judge key 归一化 / 题型分布 / report 三句总结等 |
| test_scoring_service | 9 | ScoringService：空输入 / 去重 / accuracy / 知识点聚合 |
| test_quiz_chain | 8 | QuizChain 5 级兜底 + fixture 分布 + question_count 分桶截断 |
| test_report_chain | 6 | ReportChain：accuracy 60/100/0 三档 / mastered/weak 非空 / advice/share_quote |
| test_quiz_api | 11 | HTTP：happy / 参数校验(4000) / HTML 剥离 / 敏感词(4001) |
| test_report_api | 7 | HTTP：happy / 参数校验(4000) |
| **合计** | **61** | **100% 全绿** |

### ④ 启动后端服务（端口 8000）

```powershell
cd backend
$env:USE_MOCK_LLM="true"
# $env:DEEPSEEK_API_KEY="sk-xxxx"  # 想用真实 AI 时注释上一行，填真实 Key
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

验证：打开 http://127.0.0.1:8000/api/v1/health 应返回 `{"code":0,"message":"ok","data":{"status":"healthy"}}`

### ⑤ 启动前端 + 微信开发者工具预览

```powershell
cd frontend
pnpm dev:weapp
```

然后打开 **微信开发者工具 → 导入项目**：
- 项目目录：`frontend/dist/`（dev:weapp 持续编译产物）
- AppID：选 "测试号" 即可（MVP 阶段不需要正式 AppID）
- 勾选 "不校验合法域名"（本地 127.0.0.1 调试用）

## 一键启动脚本（推荐）

日常联调请优先看：**[docs/本地启动操作手册.md](./docs/本地启动操作手册.md)**。

```powershell
# 在项目根目录
.\scripts\start-dev.ps1
# 或双击 start-dev.bat

# 停止
.\scripts\stop-dev.ps1
```

会自动检查并启动 MySQL（默认 `C:\ruanjian\mysql`），再分别打开后端 / 前端独立窗口：

- 后端：`uvicorn` → http://127.0.0.1:8000
- 前端：`npm run dev:weapp` → 产物 `frontend/dist`（导入微信开发者工具）

## 核心业务闭环

```
用户 (pages/home) 输入学习内容（5-500 字）
        ↓ POST /api/v1/quiz/generate
        ↓ text_cleaner (HTML 剥离/截断) + ContentFilter (DFA 敏感词 4001)
        ↓ QuizGenerateRequest Pydantic (题型分布/字段长度 4000)
        ↓ QuizChainService 5 级兜底：L1 LLM→L2 字段补全→L3 分布修复→L4 v2 Prompt 重试→L5 fixture
        ↓ 返回 QuizGenerateResult（3-5 题，单/多/判 ≥1 各）
前端跳转 pages/loading (ProgressTrack 假进度) → 再跳 pages/quiz
        ↓ 用户逐题作答（单/多选切换逻辑 / 判题 / 提交后锁定 → ExplainBox 展示对错+解析）
        ↓ 最后一题 "查看报告" → POST /api/v1/report/generate
        ↓ ReportGenerateRequest (quiz coerce dict/list/Pydantic)
        ↓ ScoringService：accuracy/分桶/mastery_vs_weak_split(0.8/0.6)
        ↓ ReportChainService L1-L5 兜底 → ReportGenerateResult
        ↓ 跳转 pages/report
前端展示：RingProgress(260 环/变色) + 3×NoteCard(summary idx 1-3) + 掌握/薄弱双列 + AI 建议 + 学习金句 + 再闯一关 / 生成海报(Toast 占位)
```

## 错误码体系（永远 HTTP 200，前端按 `code` Toast）

| 区间 | 含义 | 例 |
|---|---|---|
| 0 | 成功 | `{code:0, message:"ok", data:{...}}` |
| 1xxx | 参数错误 | 1001 user_input 太短 / 1002 question_count 超限 |
| 2xxx | 鉴权 | MVP 暂空（后续登录） |
| 3xxx | 合规 | 3001 输入命中敏感词（ContentFilter 4001 别名） |
| 4xxx | 业务 | 4000 Pydantic 校验失败 / 4001 敏感词拦截（HTTP 路由返回） |
| 5xxx | AI 服务 | 5000 LLM 调用全部失败（已 L5 fixture 兜底，实际不会到前端） |

## UI 风格 Copilot 原型 8 tokens

```scss
--orange:      #ff7a2f;   // 主色
--orange-soft: #fff1e6;
--blue:        #4e9fff;
--green:       #2e9e71;
--red:         #ff6f5d;
--text:        #1f2d37;
--muted:       #6c7b87;
--bg:          #f6f4ef;
// radius: 8(sm) / 12(md) / 16(lg) / 24(xl)
// shadow: sm / md / lg
// space: 8 / 16 / 24 / 32 / 48
```

3 份原型 HTML 见 `docs/Copilot生成的原型图/`：
- `01-core-flow.html`：首页 → 加载 → 答题 → 报告
- `02-extended-flow.html`：扩展交互（判断题图标 10px 已对齐）
- `03-design-system-board.html`：组件设计系统板（10 组件的 UI 规格）

## MVP 边界（Out of Scope）

- 登录 / 账号 / 数据库持久化（下一阶段引入）
- PDF/Word/视频/网页解析（仅纯文本 5-500 字）
- 联网搜索 / RAG / 向量库
- PK / 排行榜 / 裂变海报（「生成海报」仅 Toast 占位）
- 多模态（图片/语音）、支付
- NutUI / Taroify 重型 UI 库（10 组件自行实现，严格按原型）

## 目录结构速查

| 需求点 | 代码位置 |
|---|---|
| 前端 10 组件 | [components/index.ts](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/frontend/src/components/index.ts) |
| Quiz 页面组件化 | [pages/quiz/index.tsx](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/frontend/src/pages/quiz/index.tsx) |
| Report 页面组件化 | [pages/report/index.tsx](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/frontend/src/pages/report/index.tsx) |
| FastAPI App + 统一异常包装 | [main.py](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/app/main.py) |
| Quiz/Report Pydantic 模型 | [models/quiz.py](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/app/models/quiz.py) / [models/report.py](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/app/models/report.py) |
| QuizChain 5 级兜底 | [quiz_chain.py](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/app/services/quiz_chain.py) |
| ReportChain + ScoringService | [report_chain.py](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/app/services/quiz_chain.py#L98-L236) / [scoring_service.py](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/app/services/scoring_service.py) |
| pytest 61 条用例 | [backend/tests/](file:///e:/xiaochengxu/fxs-ai-learn/fxs-ai-learn/backend/tests/) |
