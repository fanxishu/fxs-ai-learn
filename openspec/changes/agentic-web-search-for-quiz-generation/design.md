# Design

## Context

见 `proposal.md` 的动机说明。当前项目后端是 FastAPI + LangChain + DeepSeek，现有 `/quiz/generate` 为同步接口：路由层完成鉴权、输入清洗和敏感词校验后，直接调用 `QuizChainService.generate_quiz()`，再由 `LLMFactory.build_quiz_llm()` 触发 DeepSeek 生成题目并立刻返回结果。当前实现没有真正的联网知识获取，也没有任务态抽象。

现有代码约束包括：
- DeepSeek 仍通过 `langchain-openai` 的 `ChatOpenAI` 走 OpenAI 兼容接口。
- 题目输出目前依赖 `response_format={"type":"json_object"}`，而不是 `with_structured_output()`，因为项目已有经验表明 DeepSeek 对 `json_schema` 支持不稳定。
- 请求响应统一走 `ApiResponse(code/message/data)`，HTTP 恒为 200。
- 当前题目持久化依赖 `quiz_sessions` 表，尚无独立任务表。

根据你指定的 LangChain 官方文档，这次联网能力严格收敛为官方集成：
- `langchain_tavily.TavilySearch`
- `langchain_tavily.TavilyExtract`

同时，官方文档明确了一个关键限制：`include_answer` 与 `include_raw_content` 这类会显著影响返回体大小的参数，**不能在 invocation 时动态切换**。这直接影响工具建模方式。

## Goals / Non-Goals

**Goals:**
- 让 AI 在出题前自主决定是否调用关键词搜索、深度搜索或 URL 提取工具。
- 在不绕开 LangChain 官方 Tavily 工具的前提下，实现“简单知识走摘要、复杂知识走深度、URL 走整页提取”的策略。
- 把同步出题接口升级成异步任务流，降低超时概率并改善前端体验。
- 保留现有鉴权、敏感词过滤、结构化校验与多级兜底能力。

**Non-Goals:**
- 不在本变更中引入 PDF/Word/视频解析。
- 不引入 RAG 私有知识库或向量检索。
- 不要求本次直接上分布式队列系统（如 Celery / Redis）。
- 不改变题目结果的核心 JSON 结构。

## Decisions

### 1. 使用“多实例工具 + Agent 选择”，而不是单实例动态改所有参数

采用以下工具集合提供给 AI：
- `tavily_search_summary`：轻量搜索，固定较小结果数，固定不带原文内容。
- `tavily_search_deep`：深度搜索，固定较大结果数，固定带更丰富内容。
- `tavily_extract_basic`：针对 URL 提取页面内容。

原因：
- 官方文档允许 AI 在调用时动态设置 `search_depth`、`time_range`、`include_domains`、`exclude_domains`、`extract_depth` 等参数。
- 但 `include_raw_content` / `include_answer` 不能在调用时动态改，所以“一个搜索工具靠 AI 运行时切换所有行为”不可行。
- 用两个 `TavilySearch` 实例把“摘要搜索”和“深度搜索”分开，才能既遵守官方集成边界，又保留 AI 的自主选择能力。

备选方案：
- 单个 `TavilySearch` 实例：会卡在不可动态修改的参数上。
- 直接调用 Tavily REST API：你已明确要求这版严格按 LangChain 官方工具收敛，不采用。

### 2. 区分“知识获取 Agent”和“题目生成 Chain”

整体流程拆成两段：
1. **知识获取 Agent**：输入用户主题，绑定 Tavily 工具，自主获取外部知识并输出知识摘要。
2. **题目生成 Chain**：输入 `user_input + knowledge_summary`，继续用当前 DeepSeek 结构化出题链生成题目。

原因：
- 把“找资料”和“产出 JSON 题目”分开后，题目输出仍可保持当前稳定链路，不把 Tool Calling 与结构化 JSON 输出混在同一个环节。
- Agent 输出只需是纯文本知识摘要，稳定性要求远低于结构化题目 JSON。

备选方案：
- 单阶段 Agent 直接搜索并产题：实现更短，但更容易让 Tool Calling 干扰 JSON 输出稳定性，不符合当前项目的稳妥路线。

### 3. 地域适配：实例化 `country` + query 改写 + 域名倾向

LangChain 官方 `TavilySearch` 支持 `country`，但与 `include_raw_content` 一样，**只能在工具实例化时设置，不能在 invocation 时动态改**。Tavily 也没有“城市”参数。

因此地域适配采用：
- 根据用户语义推断地域倾向后，在构建 `TavilySearch` 实例时注入 `country`（如国内 → `china`）。
- Agent 继续改写 query（例如增加“国内”“中国”“北京”“海外”“global”等词），用 query 覆盖城市级意图。
- 通过 `include_domains` / `exclude_domains` 倾向国内或国际来源。
- 当用户直接给 URL 时，以 `extract` 结果为最高优先级。

这样既能兼顾国内外用户，又不突破官方工具对 runtime 参数的限制。

### 4. 出题流程升级为 DB-backed 异步任务 + 轮询

新增独立任务实体，例如 `quiz_generation_tasks`，字段至少包含：
- `task_id`
- `user_id`
- `status`（pending / running / succeeded / failed）
- `user_input`
- `question_count`
- `error_message`
- `result_json`
- `created_at / updated_at / finished_at`

接口行为调整为：
- `POST /quiz/generate`：只负责创建任务并触发后台执行，立即返回 `task_id + status`
- `GET /quiz/tasks/{task_id}`：返回任务状态；成功时附带最终 quiz payload

原因：
- Tavily 检索 + Agent 决策 + DeepSeek 出题组合后，整体耗时显著增加，同步接口体验会恶化。
- 任务表能让前端稳定轮询，也能让后端记录失败原因、支持重试或后续监控。

备选方案：
- 继续同步接口：实现最简单，但用户等待时间长，容易出现网关超时与弱网体验差的问题。
- 上 Celery/Redis：更稳，但对当前 MVP 来说基础设施过重。

### 5. 任务执行采用轻量后台执行模型，先不引入外部队列

MVP 阶段优先采用“任务落库 + 进程内后台执行”的方案，例如在接口层创建任务记录后，用 FastAPI/asyncio 的后台执行机制拉起任务处理。

关键配套：
- 任务真正开始时更新为 `running`
- 完成后写 `result_json` 和 `succeeded`
- 异常时写 `failed + error_message`
- 若联网检索失败但题目仍生成成功，则任务仍记为 `succeeded`
- 后续可增加“超时任务回收 / 卡死任务重置”

原因：
- 先把产品体验和行为契约跑通，再决定是否升级为独立 worker。
- 任务状态持久化在数据库里，即使后续换执行器，前端轮询协议也不需要重写。

### 6. 失败分层：检索失败降级，出题失败才任务失败

失败处理分两层：
- **检索层失败**：记录 warning，`knowledge_summary` 置空，继续原 Prompt 出题。
- **题目生成层失败**：继续沿用当前 `QuizChainService` 的多级兜底；若最终仍不能产出题目，则任务状态记为 `failed`。

这样符合你给出的人工思路：联网搜索是增强能力，不是硬依赖。

## Risks / Trade-offs

- **[任务模型增加数据库复杂度]** → 通过单表最小字段集起步，避免一开始引入队列基础设施。
- **[进程内后台执行在服务重启时可能中断]** → 任务状态持久化，后续可增加 stale task 恢复机制；MVP 先接受该权衡。
- **[Agent 可能过度调用工具，拉长耗时]** → 在 Agent 提示词中约束工具调用次数和优先级，且对结果摘要设置长度上限。
- **[最新知识与深度内容拉高 token 成本]** → 用多实例搜索工具控制返回规模，只把摘要或截断后的上下文注入出题 Prompt。
- **[URL 页面内容质量参差不齐]** → 对抽取结果做长度控制与基础清洗；抽取无效时回退为普通搜索或纯模型出题。

## Migration Plan

1. 先新增任务表、任务模型和任务状态接口，但保留旧出题实现不动。
2. 把当前同步 `/quiz/generate` 改成“创建任务 + 后台执行”。
3. 在后台执行流程中接入知识获取 Agent，再接入原有出题链。
4. 前端改为轮询式交互，并在任务成功后跳转答题页。
5. 验证新链路稳定后，再移除前端对同步直返题目的假设。
