# GitHub 仓库首次维护设置

本文件描述 **需要在真实 GitHub 仓库创建后执行的操作**；生成模板不代表已在 GitHub 生效。

1. 确认仓库为 **Public**，主分支为 `main`，已推送基线文件。
2. 仓库 Settings → Rules → Rulesets 创建保护 `main` 的规则：要求 PR、最新审查通过、必要状态检查、拒绝强制推送和删除。首次 CI 成功后再配置必需检查名（`validate` job）。注意仓库所有者的绕过角色和权限需要单独检查。
3. 为高风险路径（`AGENTS.md`、`skills/**`、`scripts/**`、`.github/workflows/**`、`template/.github/workflows/**`）增加 CODEOWNERS 或独立审查流程。
4. Settings → Actions：默认 GITHUB_TOKEN 最小权限，避免在执行不可信 PR 代码的任务中注入 secrets。不要给普通 Agent 管理员 token。
5. 开启适用的安全扫描、依赖告警、私密漏洞上报（按计划和账号能力决定），验证 webhook 的签名和事件幂等性。
6. 从 `docs/ROADMAP.md` 创建最初的 Issue，并用项目看板关联到相应阶段；明确哪些是“已实施”和“仅提案”。
7. 通过第一个低风险 PR 演练：旧代码测试反证 → head/base 证据 → CI → 独立审核 → 受控合并。确保保护规则实际拒绝不符合要求的变更。

## 仓库已初始化后的维护

仓库已创建，首批 Roadmap Issues 已归档在 GitHub Issues 中，首次建仓脚本和批量创建 Issues 的一次性脚本已移除。后续新任务直接按 Issue 模板提出，避免重复创建。

MIT 许可证已添加至 [LICENSE](../LICENSE)；仓库的许可证选择记录见 [Issue #6](https://github.com/xurunxin/agent-native-starter/issues/6)。

> GitHub 仓库已经存在、CI 可以运行，不代表 Rulesets/分支保护已经生效；请按 [Issue #7](https://github.com/xurunxin/agent-native-starter/issues/7) 独立验收服务端门禁。

2026-10-13 的所有者权限只读核查确认 main 尚未受保护，详见
[治理验收记录](GOVERNANCE_ACCEPTANCE.md) 和 [配置提案](proposals/main-protection.json)。
提案尚未应用；独立审批人、bypass 范围与实际失败/成功路径仍待所有者决策和验收。
