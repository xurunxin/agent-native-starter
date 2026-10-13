# 公开项目与可验证程度（2026-10-13）

| 项目 | 公共证据 | 可以借鉴 | 不应推断 |
|---|---|---|---|
| yetone/magpie | 公开 AGENTS.md、LESSONS.md、PR 审查、CI、发布 | 语义文档、测试反证、SHA 绑定、经验沉淀 | 所有变更都强制 PR、全自治无人工 |
| microsoft/agentrc | README 明确自用 GitHub Agentic Workflows，定义 issue/draft PR/CI doctor | 动态规则生成、指令评测与漂移检测 | 每个修复都无人干预成功 |
| karpathy/autoresearch | program.md 明确只改 train.py，固定预算评价及 keep/discard | 范围约束、可重复实验、失败回滚 | 适合无条件套用到生产代码 |
| github/gh-aw | Markdown 编译为 Actions 工作流、权限隔离 | Agent 与确定性自动化分工 | Gitea 上能直接使用 gh-aw |
| apache/magpie | 明确人工批准和命令级 sandbox guard | 最小权限、安全预检 | 已经实现自动合并 |
| aws-samples/remote-swe-agents | agent 创建公开 PR 样例和云开发环境 | 执行环境隔离、远程任务 | 独立验证的生产级成功率 |
| zxkane/autonomous-dev-team | Issue label→worktree→reviewer 源代码/说明 | 自治循环与多模型适配 | 其宣称的零人工合并已通过第三方审计 |
| jarod-rosenthal/oncallshift | AI 编写完整多端代码库的公开声明与源码 | 大规模代码结构、测试面 | 长期 SLA 和线上成熟度 |

来源：
- https://github.com/yetone/magpie
- https://github.com/microsoft/agentrc
- https://github.com/karpathy/autoresearch/blob/master/program.md
- https://github.com/github/gh-aw
- https://github.com/apache/magpie
- https://github.com/aws-samples/remote-swe-agents
- https://github.com/zxkane/autonomous-dev-team
- https://github.com/jarod-rosenthal/oncallshift
- https://docs.gitea.com/usage/issues-prs/issue-pull-request-templates/
- https://docs.gitea.com/1.27/usage/access-control/protected-branches/
