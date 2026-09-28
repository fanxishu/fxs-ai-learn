# Tasks

## 1. 依赖与配置

- [x] 1.1 在 `backend/requirements.txt` 中新增 `langchain-tavily`，并验证 `pip install -r backend/requirements.txt` 成功
- [x] 1.2 在 `backend/app/core/config.py` 与 `backend/.env.example` 中补齐 `ENABLE_WEB_SEARCH`、任务超时、任务轮询相关配置，并验证配置对象可正确读取默认值

## 2. 出题任务模型与后端接口

- [x] 2.1 新增出题任务数据模型与 repository（含任务状态、错误信息、结果 JSON），并通过 repository 单测验证任务可创建、更新、按用户查询
- [x] 2.2 改造 `POST /api/v1/quiz/generate` 为“创建任务即返回”，并通过接口测试验证返回 `task_id + status` 而不是同步 quiz 结果
- [x] 2.3 新增任务状态查询接口（如 `GET /api/v1/quiz/tasks/{task_id}`），并通过接口测试验证 running / succeeded / failed 三种状态返回正确
- [x] 2.4 加入任务归属校验，并通过接口测试验证用户无法查询他人的任务

## 3. Agentic Web Search 知识获取

- [x] 3.1 新增知识获取 service 与专用 prompt，绑定 `TavilySearch` / `TavilyExtract` 工具，并通过单测验证关键词输入与 URL 输入都会进入对应检索路径
- [x] 3.2 采用多实例搜索工具方案（摘要搜索 / 深度搜索），并通过单测验证复杂主题不会错误地依赖运行时切换 `include_raw_content`
- [x] 3.3 实现 query 改写与域名倾向策略，并通过单测验证地域语义输入会影响检索 query 或 include/exclude domains
- [x] 3.4 实现检索失败降级与上下文长度裁剪，并通过单测验证超时、空结果、异常时仍返回空上下文而非抛错

## 4. 出题链路集成

- [x] 4.1 将知识获取 Agent 接入题目生成链路，并通过集成测试验证 `user_input + knowledge_summary` 会共同进入出题 Prompt
- [x] 4.2 保持现有敏感词过滤、JSON 校验和五级兜底逻辑不回退，并通过回归测试验证无搜索上下文时仍能正常生成题目
- [x] 4.3 在任务执行器中串联“检索 → 出题 → 持久化 quiz session → 写回任务结果”，并通过集成测试验证成功任务最终可拿到 quiz payload
- [x] 4.4 为任务失败路径补充错误写回，并通过集成测试验证最终失败会落为 `failed` 状态并带可展示错误信息

## 5. 前端轮询与联调

- [x] 5.1 改造前端生成题目交互为“创建任务后进入轮询”，并验证生成中界面不会阻塞主线程或提前跳转
- [x] 5.2 在轮询成功后再进入闯关答题页，并验证题目结果与现有答题页数据结构兼容
- [x] 5.3 在轮询失败或超时后展示可重试提示，并验证用户可重新发起生成而不会卡死在 loading 状态
- [x] 5.4 完成端到端联调，验证关键词新知识、URL 输入、搜索失败降级三类场景都能跑通
