# Proposal

## Why

当前 AI 出题流程同时有两个核心问题：一是题目质量受大模型训练数据时效限制，遇到较新或歧义主题时容易生成错误理解；二是出题链路完全同步，前端需要一直等待 DeepSeek 与联网检索完成，体验不稳定、超时风险高。用户已经明确要求兼容“关键词搜索”和“网址整页提取”，并希望把知识获取升级为 AI 自主选择工具的模式。

## What Changes

- 将出题前知识获取从“固定搜索注入”升级为 **Agentic Web Search**：把 `TavilySearch` 和 `TavilyExtract` 两个 LangChain 官方工具交给 AI，由 AI 自主决定调用哪个工具、调用几次以及如何设置允许动态修改的参数。
- 严格按 LangChain 官方工具能力收敛参数设计：对 `search_depth`、`time_range`、`include_domains`、`exclude_domains`、`extract_depth` 做动态决策；对 `include_raw_content` / `include_answer` 这类不能在调用时动态修改的参数，采用“多实例工具”方案而不是运行时强改参数。
- 支持用户输入网页 URL 时直接提取整页内容；支持用户输入关键词、短语或一段文本时执行联网搜索，并根据复杂度在“摘要搜索”和“深度搜索”之间切换。
- 新增 **异步任务 + 轮询** 出题流程：`/quiz/generate` 不再同步返回完整题目，而是先创建任务并返回任务状态；前端轮询任务结果，完成后再进入答题页面。
- 搜索/提取失败时保留降级策略：记录 warning 日志，跳过搜索上下文，仍允许任务继续走原始 Prompt 出题，避免因联网问题阻断核心链路。
- 保持题目生成结果结构化输出和既有敏感词过滤、兜底逻辑，前端业务目标不变，仅调整获取题目的交互方式。

## Capabilities

### New Capabilities
- `web-search-context`: 出题前通过 LangChain 官方 Tavily 工具进行 Agentic 知识获取，覆盖关键词搜索、URL 内容提取、动态参数选择、失败降级与上下文注入。
- `quiz-generation-tasks`: 将出题流程改为异步任务模型，支持任务创建、状态轮询、成功结果获取与失败状态呈现。

### Modified Capabilities
- `knowledge-base-quiz-generation`: 当后续 `doc_id` 参与出题时，知识库检索与联网搜索都必须在新的异步任务框架和 Agentic 检索策略下协同工作，而不是依赖同步直接返回。

## Impact

- **后端代码**：影响 `backend/app/api/v1/routes/quiz.py`、`backend/app/services/quiz_chain.py`、`backend/app/services/langchain_factory.py`、`backend/app/models/quiz.py`、`backend/app/repositories/quiz_repository.py`；新增搜索 Agent service、任务 repository/model、轮询接口。
- **前端代码**：`frontend` 出题入口改为“创建任务 -> 轮询状态 -> 完成后跳转闯关页”的交互，不再假设 `/quiz/generate` 立即返回题目。
- **依赖**：新增 `langchain-tavily`；是否额外引入任务调度依赖需结合现有 FastAPI 运行方式决定，优先采用最轻量可落地方案。
- **API / 数据库**：新增任务状态接口与任务表/任务字段；`/quiz/generate` 的对外行为从同步结果改为异步任务响应，属于前后端协同调整。
