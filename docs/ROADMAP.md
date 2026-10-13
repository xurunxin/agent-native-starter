# Agent-Native Project Starter Roadmap

> 路线图是 **proposal / implementation plan**，并非已交付功能。对应 Issue 可以创建后逐项跟踪。

## Phase 0 — 可审查的模板基线
- [x] 五个最小 Skills 与 AGENTS.md 工程约定
- [x] 初始 GitHub/Gitea 贡献模板、静态策略检查
- [x] 公共案例的证据等级和研究索引
- [x] 为模板仓库补齐维护说明、模板完整性验证和 CI 工作流
- [ ] 完成 main 分支保护和必需检查的服务端验收（仓库已创建，见 Issue #7）
- [x] 采用 MIT License 并明确外部贡献策略（所有者决定，见 Issue #6）

## Phase 1 — GitHub/Gitea Provider 与初始化器
- [x] 设计 Provider 接口、能力检测与错误语义（#1：只读适配，未实现写入明确声明）
- [x] 实现非破坏性 `init`、`doctor`、`upgrade` 命令（#2：保留既有文件，提案走分支）
- [x] 为 Github 与 Gitea 编写契约测试和本地模拟 API 测试（不代表真实实例全部验收）
- [ ] 创建/校验 label、Issue、milestone、PR 规则以及分支保护

## Phase 2 — 受控 Agent 工作流
- [x] 可信租约与幂等事件处理，防止重复领取（#3：SQLite 库及绑定的只读恢复采集）
- [ ] 隔离 worktree、运行日志、重试预算及接管
- [ ] Draft PR 自动创建与结构化验证证据
- [ ] 独立 Reviewer，SHA/base 绑定与合并队列适配
- [ ] 人工审批与安全高风险停机门禁

## Phase 3 — 评价与经验自循环
- [ ] 指令/Skill 回归测试集与评测指标
- [ ] CI 故障归因、revert/返工复盘与经验晋升
- [ ] 跨语言模板适配与稳定版本发布

## 完成定义

2026-10-13：#8 → #9 → #10 → #11 → #12 已按依赖顺序完成一次性人工授权合并，主线 CI 逐次通过；原 Issue #1/#2/#3 已按各自协议验收关闭，#4/#5 继续部分完成，#7 未完成服务器验收。
当前实现/未验收边界和 #7 的具体治理阻塞见 [治理验收记录](GOVERNANCE_ACCEPTANCE.md)。
Phase 0 分支保护继续未完成；本次人工授权合并及 CI 成功不构成服务器验收或独立 GitHub 用户审批。
功能完成以验收证据和 CI 为准；main 合并 ≠ 发布完成。任何 Phase 2 的自动合并/发布必须在服务端门禁验证后才能启用。

[逐项验收与固定证据](ISSUE_ACCEPTANCE_2026-10-13.md) 记录关闭边界与 NOT_RUN 项；常驻控制服务、完整平台写入和真实模型评测仍不是已交付能力。
