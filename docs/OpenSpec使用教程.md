# OpenSpec 使用教程（TRAE + Windows）

> 适用于「智能 AI 闯关学习」项目。已按 OpenSpec 1.13.2 的 CLI 帮助及实际生成的 TRAE 命令核对。

---

## OpenSpec 是什么？（一句话）

OpenSpec 是一个帮你和 AI **先商量好要做什么，再动手写代码** 的工具。CLI 提供流程和模板，TRAE 中的 AI 按这些指令生成需求文档、设计方案和任务清单，再经人工确认实施。

本项目已完成全局 CLI 安装和项目初始化，日常使用直接从第二步开始，不必重复初始化。

---

## 第一步：安装和初始化

### 1. 安装 OpenSpec（新机器执行）

在 PowerShell 终端执行：

```powershell
node --version
npm.cmd install -g @fission-ai/openspec@1.13.2
openspec.cmd --version
```

Node.js 需要 **>= 20.19.0**。示例固定版本便于复现；以后主动升级时可将版本换成 `@latest`。

### 2. 在项目根目录初始化

```powershell
Set-Location "e:\xiaochengxu\fxs-ai-learn\fxs-ai-learn"
openspec.cmd init --tools trae --language zh-CN --profile core --no-animation
```

这是非交互式初始化：指定 TRAE、中文文档和核心工作流，不需要“一路回车”。不要在 `frontend/` 和 `backend/` 各初始化一遍，根目录的一套规格管理整个项目。

初始化生成：

```text
openspec/
├── specs/          # 正式规格，初始为空
├── changes/        # 进行中的变更，初始为空
└── config.yaml     # spec-driven 工作流和中文产物配置
.trae/
├── commands/       # 6 个 TRAE 聊天命令
└── skills/         # 6 个对应的 OpenSpec 技能
```

原有 `docs/`、`.trae/specs/` 和业务代码保留。初始化**不会自动把旧文档转换成正式规格**，也不会自动开发新功能。

初始化后重启 TRAE，让它刷新命令和技能。正文使用中文，规格模板要求的结构标题以及 `SHALL`、`MUST` 等关键词保留英文。
---

## 第二步：提出一个新功能（核心操作！）

在 TRAE 聊天输入框中输入（不是 PowerShell 终端）：

```text
/opsx-propose 增加用户学习数据统计看板，请先阅读项目现有需求和方案文档，只生成提案，等待我确认再开发
```

**TRAE 使用连字符 `/opsx-propose`，不是 `/opsx:propose`。** 后面可以跟中文需求描述，AI 会派生英文 kebab-case 变更名，例如 `add-learning-dashboard`。

默认工作流下，AI 按依赖顺序生成产物；技术设计是否必需以工作流指令为准：

```text
openspec/changes/add-learning-dashboard/
├── .openspec.yaml
├── proposal.md
├── specs/
│   └── learning-dashboard/spec.md
├── design.md
└── tasks.md
```

`proposal.md` 说明为什么做和改动范围，`specs/` 记录需求增量，`design.md` 说明实现方案，`tasks.md` 是任务清单。检查并确认这些产物后，再单独发起实施命令；提案命令本身不授权改业务代码。

---

## 第三步：让 AI 干活 + 归档

### 3a. 让 AI 按任务清单写代码

```text
/opsx-apply add-learning-dashboard
```

AI 会按照任务清单实施。可以省略名称，但存在多个变更时建议明确指定，避免选错任务。实施前先核对 Git 工作区，不覆盖已有未提交修改。

### 3b. 完成后归档

先完成必要验证和人工验收，再在 TRAE 聊天中执行：

```text
/opsx-archive add-learning-dashboard
```

归档流程检查产物和任务状态，并在需要时处理规格同步。确认同步后，增量规格合并到 `openspec/specs/`，变更目录移入 `openspec/changes/archive/`。不要忽略未完成任务提示直接归档。

归档不等于 Git 提交或 push，两者仍需明确授权。

---

## 完整流程总结

```text
/opsx-propose 需求 → 检查产物并人工确认 → /opsx-apply 变更名 → 验证与验收 → /opsx-archive 变更名
```

当前核心配置还包含 `/opsx-explore`（讨论探索）、`/opsx-sync`（同步规格）和 `/opsx-update`（调整已有变更）。额外的 verify、onboard 等工作流不在本次核心安装范围内。

---

## 实战举例

以下是本项目可以用 OpenSpec 扩展的功能示例：

| 功能 | 命令 |
|------|------|
| 增加排行榜 | `/opsx-propose 增加用户答题排行榜功能` |
| 支持视频输入 | `/opsx-propose 支持用户输入视频链接自动生成题目` |
| 错题本 | `/opsx-propose 增加错题本功能，记录用户答错的题目` |
| 学习提醒 | `/opsx-propose 增加每日学习提醒推送功能` |
| 多人对战 | `/opsx-propose 增加好友PK答题对战模式` |

---

## 常用 CLI 命令速查

以下在项目根目录的 PowerShell 终端执行；示例变更名需在创建提案后替换为实际名称：

```powershell
openspec.cmd list
openspec.cmd list --specs
openspec.cmd show add-learning-dashboard
openspec.cmd status --change add-learning-dashboard
openspec.cmd validate add-learning-dashboard --strict --no-interactive
openspec.cmd validate --all --strict --no-interactive
openspec.cmd doctor
openspec.cmd view
openspec.cmd update
```

`list` 查看进行中的变更；`list --specs` 查看正式规格；`status` 查看产物完成情况；`validate` 检查规格格式；`doctor` 检查 OpenSpec 关系健康；`view` 打开终端交互式看板。

`openspec.cmd update` 只更新项目里的集成指令，**不升级全局 CLI**。升级 CLI 用 `npm.cmd install -g @fission-ai/openspec@latest`，然后执行 `openspec.cmd update` 并重启 TRAE。

注意 `/opsx-update` 是聊天中调整变更的工作流，与终端的 `openspec.cmd update` 不是一回事。
---

## Windows / TRAE 常见问题

### 提示禁止运行 npm.ps1 或 openspec.ps1

使用本文的 `npm.cmd` 和 `openspec.cmd`，无需放宽系统执行策略。

### 安装成功但找不到 openspec 命令

先重开终端。当前机器的安装位置是 `%APPDATA%\npm`，可以直接验证：

```powershell
& "$env:APPDATA\npm\openspec.cmd" --version
```

其他机器使用 `npm.cmd prefix -g` 查询实际全局安装位置。

### TRAE 没有显示斜杠命令

重启 TRAE，确认打开的是项目根目录，并检查 `.trae/commands/opsx-propose.md` 和 `.trae/skills/openspec-propose/SKILL.md` 是否存在。不要为了刷新命令删除现有规格或强制重新初始化。

### 列表为空，校验提示没有可校验项目

初始化后没有业务变更或正式规格，这是正常状态，不代表安装失败，也不代表业务测试已通过。创建第一个提案后再校验它。

### 与现有文档、Git 的关系

- 提案时明确要求 AI 阅读 `docs/` 中的现有需求和方案，发现冲突先确认。
- 项目配置、命令、技能和实际规格可随项目提交，便于协作；密钥不得写入这些文件。
- 本次初始化未迁移旧规格、未创建示例业务变更，也未提交或推送代码。

## 参考

- [OpenSpec 官方 npm 包](https://www.npmjs.com/package/@fission-ai/openspec)
- [OpenSpec 官方仓库](https://github.com/Fission-AI/OpenSpec)
- 本机实际用法：`openspec.cmd init --help`、`openspec.cmd validate --help` 和生成的 `.trae/commands/` 指令。
