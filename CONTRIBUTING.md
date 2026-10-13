# 贡献指南

项目处于 Early Preview。欢迎通过 Issue 提交需求、可复现的 bug、平台兼容问题和模板质量改进。代码变更采用分支 + Draft PR；不要直接推送 `main`。

## 发起 Issue

说明希望达成的可观察行为、当前行为、环境/平台版本、验收条件、相关源码/文档和风险。未定义验收条件的探索任务应标记为 proposal，不能由 agent 直接认定完成。

## 提交 PR

- 一个 PR 只对应清晰的目标，超出范围的工作单独记录 Issue。
- 解释修改前后行为、影响文件、向后兼容性和风险。
- 提供实际运行的命令、退出状态、head SHA 及结果；未运行项必须明确列出。
- 修改工程标准/权限/Actions/Skills 必须走维护者审查。作者不能自审自合。
- 契约有变化时，同步更新相应文档；文档描述现状，不把尚未实现的能力说成已实现。

## 开源许可与外部贡献

本仓库接受外部 Issue 和 Pull Request。仓库原创代码和文档采用 [MIT License](LICENSE)。

- 目前**不强制 CLA 或 DCO**；如果未来需要，必须提前公开变更规则，不能追溯强加。
- 提交者应有权授权其贡献，并同意自己的贡献按项目的 MIT 许可证分发；不能提交未获授权、许可证不兼容的第三方代码或材料。
- 请按照 [SECURITY.md](SECURITY.md) 私密报告安全漏洞，不要在公开 Issue / PR 中披露凭证、敏感数据或漏洞利用细节。

## 本地检查

```bash
python3 scripts/policy_check.py
python3 scripts/validate_templates.py
python3 template/scripts/policy_check.py
```

> 这些检查只涵盖当前静态模板健全性，不代替受保护分支、Code Review 和真实环境验收。
