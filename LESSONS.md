# LESSONS · 当前仍适用的经验

**写入时机**：仅当发生有证据的实际失败，并且可复用（通常在两个独立任务复现）时，才通过可信审查添加。普通完成/偶发小错不写经验。详情见 [经验维护协议](docs/EXPERIENCE_POLICY.md)。

**阅读方式**：开始相关任务时只读适用经验。长日志保留在 Issues/PR；AGENTS.md 保留最简入口。超过 12 个活动规则或 120 行、进入稳定化里程碑或重要交接时，使用 learning-loop 合并、压缩、淘汰重复或已无效内容。

## 活动经验

<!-- 每条最多六个短句：触发、做法、原因、证据、范围、复核。确认无新经验时保持此节为空。 -->

## 现有案例与证据（待复核，不视为自动晋升）

## 2026-10-13：静态规则不能证明 GitHub 分支保护已生效（提案，#7）

- 根因：仓库中的 AGENTS.md、配置和 CODEOWNERS 是声明；GitHub 服务端仍需要单独配置。
- 触发条件：新仓库完成模板推送与 CI 后，尚未完成服务器治理验收。
- 证据：main `61158b3ae0da3b571053427d67a7028605face86` 的 `validate` 成功；
  `gh api repos/xurunxin/agent-native-starter/rulesets` 返回 `[]`；
  `gh api repos/xurunxin/agent-native-starter/branches/main/protection` 返回 HTTP 404 `Branch not protected`。
- 重现：以现有授权执行以上两个只读 API，核对对应 main SHA 和 CI check run；权限不足返回 403 时只能记录未知。
- 错误做法：将本地 policy_check 或绿色 CI 当作禁止直推/缺少审批时拒绝合并的证据。
- 预防提案：由所有者审批实际保护策略，再通过低风险 Draft PR 保存失败检查、缺少审批和授权成功路径的验收记录。
- 自动检查：`tests/test_review.py:test_protection_unknown_draft_and_auto_merge_block`；线上验收样本 `evals/tasks.json:live-protected-main` 当前 NOT_RUN。
- 适用范围：GitHub starter 初始化；不能外推为所有 Gitea 版本的等价保护行为。
- 复核日期：2027-01-13，或保护策略/权限/默认分支变化时立即复核。
- 晋升状态：Draft PR 待审；不增加 Agent 权限，不宣称服务器保护已修复。
