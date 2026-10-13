# Codex Skill 接入

可安装的 Skill 源目录是 `skills/project-bootstrap/`，包括 SKILL.md、agents/openai.yaml 和 references。
不需要新的初始化脚本、常驻服务或全局安装。README 顶部提供可直接复制给 Agent 的入口提示词。

## 项目级安装与调用
在核实 starter checkout 和固定 SHA 后，`python -m agent_starter init "/absolute/project" --dry-run`
预览目标；获准执行的 `init` 会以独占创建方式把 Skills 安装到目标的 `.agents/skills/`。
原目录和文件存在时不会覆盖。也可按项目安装流程复制完整 `skills/project-bootstrap`
到项目的 `.agents/skills/project-bootstrap`；已存在安装必须先审查，不能静默覆盖。

调用示例：
- `$project-bootstrap 为这个新项目规划并初始化 agent-native 规则，先给预览。`
- `$project-bootstrap 为这个既有项目做渐进 agent-native 接入，保留现有代码、AGENTS、CI 和许可证。`

正常自动发现保持启用；Skill 不改变审批/安全权限。安装后的 Skill 会提示定位 starter checkout，
因为这里只安装指令和 references，没有复制另一套初始化器。详见
[工作模式与命令](../skills/project-bootstrap/references/workflow.md)。

维护者可用本机 skill-creator 的 `scripts/quick_validate.py skills/project-bootstrap` 检查格式。
该工具需要本机可用的 PyYAML；不因验证器不可用而安装全局依赖。
行为验证：`python -m unittest discover -s tests -p test_bootstrap_adoption.py -v`；
全套：`python -m unittest discover -s tests -v`，以及 README 中的三个静态检查。
验证不调用模型 API，不传真实私有仓库资料。
