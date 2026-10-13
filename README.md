# Agent-Native Project Starter

可复用的 **Agent 主导软件工程基础模板与 Skills**，面向 GitHub 和 Gitea，采用 Issue 驱动、独立 worktree 开发、Draft PR、验证证据、受控合并与经验回流的工作方式。

> **项目状态：Bootstrap / Early Preview。** 这是可用的规则与静态模板，**不是**已经实现自动任务领取、跨平台 API 适配、受控合并和无人值守发布的运行时服务。任何文档规则都不能替代服务器端分支保护。

## 主要内容

- `skills/`：项目初始化、任务编排、实现、独立审查、复盘五项独立 Skills。
- `template/`：用于新项目的 AGENTS.md、工程规范、GitHub/Gitea PR/Issue 模板、策略配置和轻量 CI 检查。
- `AGENTS.md`、`agent-project.yaml`：维护**本仓库**的 Agent 规则和风险策略，和 `template/` 内的生成模板相互独立。
- `RESEARCH.md`：来源项目和证据边界；`docs/ROADMAP.md`：迭代路线图。
- `scripts/validate_templates.py`：验证发布包中模板与 Skills 的基本完整性。

## 开始使用

也可使用无覆盖 CLI：`python -m agent_starter init /path/to/project`；
`doctor` 检查缺口，`upgrade` 在新分支生成不包含已有文件正文的 SHA-256 变更提案。详见 [初始化器](docs/subsystems/bootstrap.md)。

1. 复制 `template/` 中的文件到目标项目根目录（保留隐藏的 `.github`、`.gitea` 目录）。
2. 编辑目标仓库的 `agent-project.yaml`，填写项目名称、GitHub/Gitea 地址、技术栈和真实验证命令。
3. 让 Agent 阅读 `skills/project-bootstrap/SKILL.md` 并核对项目实际代码；禁止直接覆盖已有配置。
4. 在代码托管平台**手动或通过可信管理员工具**设置分支保护、必需检查和审查要求，核实生效。
5. 用一个低风险任务先走通 Issue → 独立 worktree → 测试 → Draft PR → 审查 → 授权合并。

本仓库的本地完整性检查：

```bash
python3 scripts/policy_check.py
python3 scripts/validate_templates.py
python3 template/scripts/policy_check.py
```

## Skills

| Skill | 作用 |
|---|---|
| [`project-bootstrap`](skills/project-bootstrap/SKILL.md) | 项目识别、基线初始化、CI/文档/规则生成 |
| [`issue-orchestrator`](skills/issue-orchestrator/SKILL.md) | Roadmap、依赖、领取租约、接管和失败预算 |
| [`implementation`](skills/implementation/SKILL.md) | 独立 worktree、范围控制、回归反证、PR 证据 |
| [`review-and-merge`](skills/review-and-merge/SKILL.md) | 独立审查、提交版本匹配、权限门禁 |
| [`learning-loop`](skills/learning-loop/SKILL.md) | 事故复盘、规则晋升、指令评测 |

## 平台支持与权限

当前运行时：`agent_starter/provider.py` 提供 Python 3.12+、无第三方依赖的 GitHub/Gitea
只读 API 适配和能力探测，详见 [Provider 契约](docs/subsystems/provider.md)。
写操作显式返回 `not_implemented`；不提供自动合并或平台保护策略写入。

- **GitHub**：提供 Issues/PR/Actions 的规则骨架；服务端 Rulesets/Branch Protection **需要单独启用**。
- **Gitea**：提供模板目录；Gitea Actions、Webhook、Projects、分支保护的实际功能须按服务器版本确认。
- **安全默认值**：`auto_merge: false`、`auto_release: false`、独立 worktree、独立审查。安全策略、凭证、生产发布、破坏性迁移需可信人工批准。
- **租约调度库**：SQLite 原子领取、代次隔离、幂等事件/意图和人工阻塞，详见 [调度契约](docs/subsystems/scheduler.md)。需要可信控制器调用。
- **审查协议校验**：版本绑定、独立逻辑身份、检查来源、人工审批与服务器证据缺失时拒绝，详见 [审查协议](docs/subsystems/review.md)。该纯函数不认证身份、不执行合并。
- **暂未实现**：常驻租约/Webhook 服务、Provider 写入、自动 issue 同步、可信身份/审查证据存储、实际发布控制面。

## 维护和协作

查看 [`CONTRIBUTING.md`](CONTRIBUTING.md)、[`SECURITY.md`](SECURITY.md)、[`docs/ROADMAP.md`](docs/ROADMAP.md) 及 [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md)。首批 Roadmap Issues 已创建；后续任务请使用 Issue 模板并明确验收标准。提交请附 Issue、变更行为、真实执行的检查与未检查项。优先通过 Draft PR 贡献，不用提交数衡量质量。

## 参考与授权

案例链接及证据强度参见 [`RESEARCH.md`](RESEARCH.md)。**本项目的原创代码和文档采用 [MIT License](LICENSE)**，版权所有 © 2026 xurunxin。引用的第三方项目与资料仍遵循各自许可，详见 [`RESEARCH.md`](RESEARCH.md)。
