# GitHub 仓库首次维护设置

本文件描述 **需要在真实 GitHub 仓库创建后执行的操作**；生成模板不代表已在 GitHub 生效。

1. 确认仓库为 **Public**，主分支为 `main`，已推送基线文件。
2. 仓库 Settings → Rules → Rulesets 创建保护 `main` 的规则：要求 PR、最新审查通过、必要状态检查、拒绝强制推送和删除。首次 CI 成功后再配置必需检查名（`validate` job）。注意仓库所有者的绕过角色和权限需要单独检查。
3. 为高风险路径（`AGENTS.md`、`skills/**`、`scripts/**`、`.github/workflows/**`、`template/.github/workflows/**`）增加 CODEOWNERS 或独立审查流程。
4. Settings → Actions：默认 GITHUB_TOKEN 最小权限，避免在执行不可信 PR 代码的任务中注入 secrets。不要给普通 Agent 管理员 token。
5. 开启适用的安全扫描、依赖告警、私密漏洞上报（按计划和账号能力决定），验证 webhook 的签名和事件幂等性。
6. 从 `docs/ROADMAP.md` 创建最初的 Issue，并用项目看板关联到相应阶段；明确哪些是“已实施”和“仅提案”。
7. 通过第一个低风险 PR 演练：旧代码测试反证 → head/base 证据 → CI → 独立审核 → 受控合并。确保保护规则实际拒绝不符合要求的变更。

## 可选的命令行发布

在此项目根目录运行 `bash scripts/publish-github.sh`，它会检查认证、git 工作区，创建 **xurunxin/agent-native-starter** 公开仓库并推送初始提交。该脚本不会开启自动合并或授权生产部署。

如目标仓库已经存在，脚本会直接终止；不要强推覆盖已有仓库。
