# 初始化与渐进接入

## 先读现状
确认用户授权的目标目录、目标/非目标、Git 状态、默认分支、已有 AGENTS/CLAUDE、
工程规范、依赖/构建入口、CI 和许可证。未知权限或不可信代码只做只读计划。
不输出可能包含密钥的现有文件正文；在可信本地环境检查必要内容。
为 starter 记录固定 SHA，核对当前代码和命令；本 Skill 使用 Python 3.12+、标准库 CLI。

## 新项目
从已核实的 starter checkout，先预览（包括隐藏目录和 Skills）：

```bash
python -m agent_starter init "/absolute/project" --dry-run
```

预览不会创建目标目录、文件或 Git 分支。结果中的 `would_create` 是计划，不是已执行。
冲突或文件系统错误返回 exit 1；不覆盖冲突。得到执行授权后：

```bash
python -m agent_starter init "/absolute/project"
python -m agent_starter doctor "/absolute/project"
```

在目标项目新分支配置新增的占位文件和真实验证命令。初始化器不替换项目代码或许可证，
也不自动选择技术栈。缺少平台证据/可信验证时 doctor 返回缺口，不能当成初始化失败的
理由去删掉原文件或放宽规则。第一次接入选一个符合用户目标的低风险验收任务。

## 既有项目
1. 先完成上述只读现状检查。保留未提交工作；若使用者没有授权在当前树继续，
   在独立分支/worktree 中工作，不重置或覆盖原修改。
2. 运行 `init --dry-run`；检查 `would_create`、冲突路径和内容指纹。给出最小渐进计划：
   可先仅接入文档/Skills，再单独审查 CI/治理修改，不为套模板迁移语言或重写系统。
3. 授权后 `init` 只创建缺失文件；存在的 AGENTS、CI、许可证、代码仍不替换。
   需要调整既有规则时，在分支上人工编辑并私下核对差异；不要把敏感正文提交到公开报告。
4. 在目标项目适配新增文件、运行原有测试与授权的可信检查，记录保留文件的校验指纹
   和重复调用结果。不要用新增静态检查代替原有行为验证。
5. 提交可追踪变更并创建 Draft PR；未经本项目授权不合并、不关闭尚未落地的任务。

`doctor --verify "python scripts/policy_check.py"` 仅适用于已经核对过的可信目标检查。
doctor 不会自动执行 YAML 中的命令，离线平台和缺失验证为 NOT_RUN。

## 后续升级
```bash
python -m agent_starter upgrade "/absolute/project" --branch agent-starter/upgrade
```

升级要求干净 Git 仓库根目录和新分支，只写 `.agent-starter-upgrade/proposal.json`，
其中是 base SHA、路径和内容指纹，没有已有项目正文。逐项审查并在分支应用获准变更；
生成提案不等于规则已升级。已有报告不覆盖。通过 PR 保留维护者审批与版本证据。

## 平台
GitHub/Gitea Provider 提供有边界的只读 API；写入返回 not_implemented。
GitHub Check Runs 只读支持不代表保护策略已配置；Gitea Checks/Actions 不能假设与 GitHub 等价。
例如只读 doctor 可显式传 `--provider github --api-url https://api.github.com --repository owner/repo`，
私有项目凭据仅在已授权可信控制进程使用，不能送入不可信 PR 执行环境。
服务器保护、独立审批人、旁路审计由所有者另行授权和验收，不由 Skill 隐含配置。

## 回滚
接入前记录基线提交及保留项；交付分支/PR 作为回滚边界。
未合并时保留或移除本次分支的已知变更；只在明确授权后处理精确文件，
先确认它仍属于本次操作且没有后续用户修改，不运行泛化的 git clean/reset 或递归删除。
已合并变更通过受审 revert PR 回滚，不强推主分支。升级提案可以保留供审计。
