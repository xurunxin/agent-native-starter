# LESSONS（经验与事故规则）

一条记录包含：发现日期、触发情境、根因、可重现证据、错误做法、可执行的新规则、自动化检查链接、适用范围、有效期/复核日期。

严重的权限或数据丢失问题立即升级强制保护；一般规则在多个独立场景确认后再晋升。禁止只根据 Agent 的自我报告断言风险已经消失。

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
