---
name: project-bootstrap
description: 使用 agent-native-starter 为新项目初始化规则与 Skills，或在保留既有代码、CI 和许可证的前提下渐进改造已有项目；用户要求 agent-native 接入时使用。
---

# Project bootstrap and adoption

先确认用户目标、目标仓库、托管平台和当前授权范围，再判断是新项目初始化还是既有项目改造。
提供包含保留项、拟新增文件、冲突、验证命令和回滚方式的简短计划，然后在已授权范围执行。
此 Skill 不增加写入、凭据、服务器保护、合并或发布权限。

## 入口与模式
- 使用用户指定的 starter checkout；若没有，只读检查真实仓库
  https://github.com/xurunxin/agent-native-starter ，核对固定版本和执行代码后再运行。
  不从未知下载内容自动执行脚本，不安装到全局或改安全设置。
- 从 starter checkout 运行现有 Python CLI；安装到目标项目后也须定位 starter checkout，
  不假定已安装 Skill 的相对路径中仍存在初始化器。
- 新项目：先检查目标是否为空/已有文件；预览并安装模板、Skills，按目标配置新增文件。
- 已有项目：先读项目 AGENTS/工程文档及构建入口，保留架构、代码、CI、许可证和用户目标；
  使用非写入预览、冲突报告与新分支渐进接入。不要把模板当覆盖指令。
- 命令、平台差异和回滚见 [references/workflow.md](references/workflow.md)，按当前模式读取。

## 工程模式与文档基线

新建项目默认为 `build`，但先核对是否已有生产用户：确属试验可用 `explore`，已有稳定公共契约应为 `ga`。阶段只控制开发期的验证成本，不能放宽凭证、数据或发布门禁。既有项目不能因安装 starter 自动降级质量模式，必须先提出对照差异。
安装后目标项目应有 工程约定 `docs/engineering.md`、文档规范 `docs/DOCUMENTATION_POLICY.md`与简洁文档索引；不要把长期计划写进根 README，不复制各类历史聊天和阶段代号。复杂既有文档使用 documentation-curation，重复/旧版实现使用 repository-consolidation；二者按需调用，不自动进行大规模重写。

## 接入选择与 Agent 指引

- **默认用轻量接入**：`init TARGET --dry-run` 再 `init TARGET`；显式 `--profile full` 才装全部本平台适用模板，平台可用 `--platform github|gitea|none` 指定。没有明确平台时不猜测自托管 Gitea 主机。
- 预览需要列出选中、明确跳过、已有冲突。安装选择保存在 `.agent-starter/adoption.json`；`doctor` 用这份清单判断真正缺失，不要求补装“有意排除”的文件。
- 安装后新 Agent 应直接读到：`AGENTS.md` 的任务阶段判断与 Skill 路由、`docs/engineering.md` 的四问、`LESSONS.md` 活动经验和 `docs/EXPERIENCE_POLICY.md` 更新/压缩时机。没有证据的日常任务不追加经验。
- **已有 AGENTS.md 不覆盖**。冲突意味着需在独立 PR 中人工/Agent 审阅一段简短路由并整合进原文，不可因为旧规则不兼容就静默替换。已经安装了旧全量模板的项目继续按旧清单检查；需有意迁移，不在默认 init 里删除文件。
- 不把完整 CI、调度库、Gitea/GitHub 不适用模板安装视作轻量接入的“缺口”。`doctor` 未执行平台/测试时必须标 NOT_RUN，不把轻量解释为已通过审查或服务器保护。

## 执行边界
使用现有 `init --dry-run`、`init`、`doctor`、`upgrade`，不重复实现初始化器。
不执行从 Issue/YAML 任意取得的验证命令；`doctor --verify` 只运行用户授权的可信命令。
冲突报告只含路径和指纹，不能把已有文件正文、密钥或私有代码复制到日志/PR。
升级提案和模板不是已生效的服务器治理；Provider 写入、常驻调度和自动合并未提供。
工作流和规则变更通过可审分支/Draft PR，并保留所需的可信维护者审批。

## 强制输出
- 识别的模式、用户目标、保留项、冲突及拟执行计划。
- 固定 starter SHA、实际命令/退出码、变更清单和 PR/提交。
- 幂等性、冲突保护与回滚证据；没有运行的项目标记 NOT_RUN。
- 平台能力缺口和下一步；不以本地检查通过证明服务器保护生效。

## 安全底线
遵守目标仓库已有约定；不静默覆盖、不自审自合、不读取超出授权的凭据。
不使用自动合并、强推、批量清理或全局安装作为接入的隐含步骤。
