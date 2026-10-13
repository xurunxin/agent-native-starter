# Agent-Native Project Starter

**复制给 Agent 的一句话：**
> 请先阅读 https://github.com/xurunxin/agent-native-starter/blob/571b5ea618257f55e3f698766c03b1180c2e20cf/skills/project-bootstrap/SKILL.md，判断我的目标是新项目初始化还是既有项目渐进 agent-native 改造，尊重现有代码、规则、CI、许可证和我的目标，先给计划，再在我授权的范围内执行。

安装源：[`skills/project-bootstrap/`](skills/project-bootstrap/)；[项目级使用与安装指引](docs/USING_CODEX_SKILL.md)。

可复用的 **Agent 主导软件工程基础模板与 Skills**，面向 GitHub 和 Gitea，采用 Issue 驱动、独立 worktree 开发、Draft PR、验证证据、受控合并与经验回流的工作方式。

> **项目状态：Bootstrap / Early Preview。** 提供规则、模板和显式边界的运行时库；尚不是完整的常驻 Agent 控制服务。任何文档规则都不能替代服务器端分支保护。当前实现与未验收范围见下方子系统说明。

## 主要内容

- `skills/`：项目初始化、任务编排、轻量实现、审查、复盘、代码收敛和文档整理七项按需使用的 Skills。
- `template/`：用于新项目的 AGENTS.md、工程规范、GitHub/Gitea PR/Issue 模板、策略配置和轻量 CI 检查。
- `AGENTS.md`、`agent-project.yaml`：维护**本仓库**的 Agent 规则和风险策略，和 `template/` 内的生成模板相互独立。
- `RESEARCH.md`：来源项目和证据边界；`docs/ROADMAP.md`：迭代路线图。
- `scripts/validate_templates.py`：验证发布包中模板与 Skills 的基本完整性。

## 开始使用

**迭代原则：** 默认 `build` 模式只做最小有效验证，优先原位修改，禁止凭空复制 `src.v1.ts/src.v2.ts` 等平行版本。项目风险和交付成熟度独立分级；进入稳定化或 GA 合并时按影响面升级验证，不降低权限与分支安全要求。详见 [工程阶段与验证规则](docs/engineering.md) 和 [文档索引](docs/README.md)。


也可使用无覆盖 CLI：`python -m agent_starter init /path/to/project`；
`doctor` 检查缺口，`upgrade` 在新分支生成不包含已有文件正文的 SHA-256 变更提案。详见 [初始化器](docs/subsystems/bootstrap.md)。

1. 从 starter checkout 运行 `python -m agent_starter init /path/to/project --dry-run` 预览；获准后运行 `init`，保留隐藏目录且不覆盖已有文件。
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
| [`repository-consolidation`](skills/repository-consolidation/SKILL.md) | 旧版代码/重复 Helper 收敛、兼容退出 |
| [`documentation-curation`](skills/documentation-curation/SKILL.md) | README、计划、指南、参考与历史分流 |

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

任务样本、基线比较与经验晋升约定见 [评测文档](docs/subsystems/evaluation.md)。
运行时全套检查：`python -m unittest discover -s tests -v`。

查看 [`CONTRIBUTING.md`](CONTRIBUTING.md)、[`SECURITY.md`](SECURITY.md)、[`docs/ROADMAP.md`](docs/ROADMAP.md) 及 [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md)。首批 Roadmap Issues 已创建；后续任务请使用 Issue 模板并明确验收标准。提交请附 Issue、变更行为、真实执行的检查与未检查项。优先通过 Draft PR 贡献，不用提交数衡量质量。

## 参考与授权

文档分类及命名见 [文档规范](docs/DOCUMENTATION_POLICY.md)，项目计划通过 [GitHub Issues](https://github.com/xurunxin/agent-native-starter/issues) 维护，而非写在 README 中。


案例链接及证据强度参见 [`RESEARCH.md`](RESEARCH.md)。**本项目的原创代码和文档采用 [MIT License](LICENSE)**，版权所有 © 2026 xurunxin。引用的第三方项目与资料仍遵循各自许可，详见 [`RESEARCH.md`](RESEARCH.md)。
