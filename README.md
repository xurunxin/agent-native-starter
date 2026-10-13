# Agent-Native Starter

**让 AI Agent 持续推进软件开发，同时保持代码、验证和文档简洁可维护。**

Agent-Native Starter 是面向**新项目初始化**和**既有项目渐进改造**的一套工程约定、可安装 Skills、无覆盖初始化工具与 GitHub/Gitea 协作模板。它的目标不是让 Agent 产生更多测试、兼容层或过程报告，而是帮助 Agent 在明确的任务与授权范围内，选择合适的工程强度、交付可用功能，并为下一次接手留下清晰的上下文。

> **当前状态：Early Preview。** 已提供可使用的初始化 CLI、七项 Skills 和部分协作基础库；**不是**已部署的无人值守 Agent 调度平台。仓库规则不能代替真实的分支保护、独立审批与发布授权。

## 适合什么场景

- **从零创建项目**：建立简洁的 Agent 入口、工程约定、经验维护规则和按需协作模板。
- **改造已有项目**：保留源码、现有 `AGENTS.md`、CI 与许可证，以预览、冲突提示和可审查提案逐步接入。
- **长期迭代与收敛**：避免 `src.v1.ts` / `src.v2.ts` 之类的平行实现、重复 Helper、过量验证及混乱文档，让 Agent 换会话后仍能快速找到权威入口。

## 让 Agent 开始使用

把下面这段任务交给你的编码 Agent，或直接阅读 [project-bootstrap Skill](skills/project-bootstrap/SKILL.md)：

> 请参考 [Agent-Native Starter](https://github.com/xurunxin/agent-native-starter) 的 `skills/project-bootstrap/SKILL.md`，先判断我的目标是新项目初始化还是已有项目改造。核对 Starter 的实际版本和目标仓库，保留现有代码、约定、CI 和许可证；先给出非写入预览与冲突，再在授权范围内执行。采用轻量模式，让 Agent 根据实际使用者与变更风险决定验证强度，不生成不必要的兼容源码、测试或过程文档。

使用 Codex 的项目级 Skill 时，参见 [Skill 安装与调用](docs/USING_CODEX_SKILL.md)。

### 命令行快速开始

需要 **Python 3.12+**。以下命令在 Starter 仓库根目录运行，目标路径指向要接入的项目：

```bash
git clone https://github.com/xurunxin/agent-native-starter.git
cd agent-native-starter

# 预览，不创建文件；将 github 换成 gitea 或 none 以适配目标
python -m agent_starter init /path/to/project --platform github --dry-run

# 确认改动后再接入（默认 lean）
python -m agent_starter init /path/to/project --platform github

# 检查已选择的文件、配置与 Agent 指引是否就位
python -m agent_starter doctor /path/to/project
```

默认 `lean` 只接入核心规则、Skills 与当前平台的必要模板；需要额外模板时显式使用 `--profile full`。选择清单记录在目标工程的 `.agent-starter/adoption.json`，因此 `doctor` 会区分“应该安装却缺失”和“有意排除”。`doctor` 未执行的检查会明确显示 `NOT_RUN`，**不等于失败或通过**。

初始化不会覆盖已有文件。若目标项目的 `AGENTS.md` 已存在且未接入 Skill 路由，应人工或通过受审 PR 合并简短的入口说明，而不是用 Starter 替换原约定。后续可使用 `python -m agent_starter upgrade /path/to/project` 生成独立分支上的审查提案；工具不会直接合并或发布。详见 [初始化器行为说明](docs/subsystems/bootstrap.md)。

## 工作方式：按阶段开发，按风险验证

目标工程通过 `AGENTS.md` 指向需要的 Skills，并在 `agent-project.yaml` 中使用 `development.stage: auto`。Agent 按当次任务的实际证据选择工作模式：

| 模式 | 默认做法 |
| --- | --- |
| **Explore** 探索 | 快速验证可丢弃的想法，不提前搭建通用框架 |
| **Build** 构建 | 优先修改唯一权威实现，运行最小有效的定向检查 |
| **Stabilize** 稳定化 | 收敛重复代码与临时兼容层，扩大关键回归验证 |
| **GA** 正式维护 | 维护已发布契约与迁移路径，按影响范围验证并遵守交付门禁 |

**开发阶段不是安全级别。** 凭证、权限、用户数据、破坏性迁移和发布操作在任何阶段都必须遵守相应安全约束。开发中不反复计算无必要的 Hash、不为预想中的未来版本复制源码；合并与发布仍使用可信 CI、审查及平台侧保护。

### 经验与文档如何留下来

日常任务结束**不要求写一份经验总结**。真实故障和复现过程优先保存在对应 Issue/PR；可重复的经验再精简写入目标项目的 `LESSONS.md`。遇到里程碑交接或活动经验过多时，调用 `learning-loop` 去重、晋升或归档，而不是累计永久规则。详见 [经验维护协议](docs/EXPERIENCE_POLICY.md)。

`README.md` 只描述**当前可用能力和使用方法**；使用说明、接口参考、设计原理、ADR、计划与历史证据各有归属。Roadmap 和待办以 [GitHub Issues](https://github.com/xurunxin/agent-native-starter/issues) 为准，不把内部阶段代号或开发流水复制到用户文档。详见 [文档规范](docs/DOCUMENTATION_POLICY.md)。

## Skills

Skills 位于 [`skills/`](skills/)；初始化后安装在目标项目的 `.agents/skills/`，由 `AGENTS.md` 按任务类型引导使用，**不需要每次全部加载**。

| Skill | 用途 |
| --- | --- |
| [`project-bootstrap`](skills/project-bootstrap/SKILL.md) | 新项目初始化、既有项目非破坏性接入 |
| [`implementation`](skills/implementation/SKILL.md) | 按阶段和风险完成最小可验证功能 |
| [`issue-orchestrator`](skills/issue-orchestrator/SKILL.md) | 任务依赖、领取租约与受控交接规则 |
| [`review-and-merge`](skills/review-and-merge/SKILL.md) | 独立审查、版本证据与合并门禁约定 |
| [`learning-loop`](skills/learning-loop/SKILL.md) | 经验记录、压缩、晋升与过期复核 |
| [`repository-consolidation`](skills/repository-consolidation/SKILL.md) | 清理重复实现与不再需要的兼容层 |
| [`documentation-curation`](skills/documentation-curation/SKILL.md) | 整理 README、指南、技术参考、计划和历史文档 |

## 当前能力与边界

| 已提供 | 尚未提供或必须由平台承担 |
| --- | --- |
| `init / doctor / upgrade`：非覆盖接入、选用清单、诊断和升级提案 | 自动改写既有治理文件、自动安装或管理服务器策略 |
| GitHub/Gitea **只读** Provider 与能力探测 | Provider 远端写入和真实跨平台自动化管理 |
| SQLite 任务租约、恢复证据、审查校验与离线评测的基础库 | 常驻 Webhook/调度控制器、可信身份系统、端到端自治开发服务 |
| Issue/PR 模板、分阶段工程指引与文档治理规则 | 自动批准 PR、自动合并、生产发布及分支保护的代管 |

这些基础库需要由可信控制器集成，不应把“接口和规则已经存在”理解为“托管平台的自动化执行已经上线”。

## 文档与参与

从 [文档导航](docs/README.md) 查找当前设计和操作入口；[工程规范](docs/engineering.md)、[子系统参考](docs/subsystems/README.md) 和 [研究来源](RESEARCH.md) 分别介绍协作原则、实际实现与参考案例。需求和缺陷请使用 [Issues](https://github.com/xurunxin/agent-native-starter/issues)；贡献前阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题参见 [SECURITY.md](SECURITY.md)。

本项目原创代码与文档采用 [MIT License](LICENSE)。