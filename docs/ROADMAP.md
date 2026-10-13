# 项目路线图与状态入口

> 这里仅解释**当前已经可用的能力**以及接下来往哪里发展。具体任务、进展与验收请查看 [GitHub Issues](https://github.com/xurunxin/agent-native-starter/issues)；历史提交和验收记录不再复制成连续的 Phase/D5 日志。

## 目前可使用

- 项目初始化：`python -m agent_starter init/doctor/upgrade`，其中 upgrade 输出供审查的提案，不自动改已有治理。
- Provider：GitHub/Gitea 的只读接口与能力检测；远端写入不支持。
- 协作基础：SQLite 任务租约/栅栏协议、证据审查纯函数和离线评测/经验规则。
- Skills：项目初始化、任务编排、轻量实现、独立审查、复盘、[源码收敛](../skills/repository-consolidation/SKILL.md)和[文档整理](../skills/documentation-curation/SKILL.md)。本仓库尚非无人值守 Agent 运行服务。

## 尚需完成

- [安全治理 Issue #7](https://github.com/xurunxin/agent-native-starter/issues/7)：真实 GitHub 分支保护、独立账号审批与正反门禁验收。
- [审查协议 Issue #4](https://github.com/xurunxin/agent-native-starter/issues/4)：完成平台独立 reviewer 与生效合并门禁的真实验证。
- [Skills 评测 Issue #5](https://github.com/xurunxin/agent-native-starter/issues/5)：扩大真实模型任务的对照实验；当前的公开小样本不足以证明成本下降。
- 长期演进：可信托管写入、Webhook 控制器与恢复、真实 Gitea 适配、稳定交付模式。作为 Issue 执行前不视为现有功能。

## 历史和进一步阅读

[文档入口](README.md) · [工程阶段和测试分层](engineering.md) · [已有代码与平台验收](ISSUE_ACCEPTANCE_2026-10-13.md) · [公开的模型实验](evidence/2026-10-13-public-workflow/README.md)。

工程开发模式与交付成熟度不同：`explore/build/stabilize/ga` 是默认迭代强度，不代表任何自动化权限或已通过验收。GitHub 的 Issue 与提交历史保留此前迭代记录。
