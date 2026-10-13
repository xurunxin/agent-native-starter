# 有限公开输入实测：2026-10-13（#5）
用户明确授权仅使用现有登录额度和公开输入。CLI 确认 ChatGPT 登录；不使用 API key、购买额度、私有代码、实际配置/数据或收费图像请求。
这是两个实际模型请求，每个规则版本一次、相同三个决策场景；不是合成 token 夹具，也不是真实项目代码实现试验。
## 固定来源
旧规则来自公开 starter 840cdeeac87d0668bac6b169b5dd989c56cf784e；新规则来自75b05504eea38a142df3329c4c1f5799ed21d1eb。
只取公开 AGENTS 和 bootstrap/review/learning Skill，新版包含 bootstrap references/metadata。
old/new-rules.bundle 保存实际发送规则的最小 Git 仓库，可离线 clone、按快照 SHA 冻结、重跑导入。
每套 prompt = 快照对应规则文本 + scenario.txt。scenario.txt SHA256：
4a70b3a25009203e61f377f127761762b926fbd58720449f816f408702993374。
dataset digest：3876d40bff6feb1168fcaf9151a0a9e5f4ce95b6e6efa1a2110befc54843b839。
A 对应此次已有 AGENTS 的 Go/Vue/Gitea 接入决策（仅匿名场景）；B/C 是通用审查/成本解释场景。
实际项目未确认公开，未复制其 AGENTS、代码、配置或运行时数据到实验。
## 实际观测
模型均为 gpt-6.1-sol（运行元数据），CLI0.162.0，ignore-user-config、ephemeral、read-only，无工具事件。
明确生成参数未设置，服务默认参数未记录；不能将其解释为完整可控实验。
分类检查：A bootstrap、B review、C evaluation，各1个场景；两次均3/3通过，错误0。
导入器按1个整体 batch记录成功率100%，不虚构每个场景的 token 分摊。
场景C中的示例120+30=150是题目数据，不能混同真实 CLI 消耗：

| 指标 | 旧规则 | 新规则 |
|---|---:|---:|
| input_tokens | 18002 | 19471 |
| output_tokens | 83 | 83 |
| total_tokens | 18085 | 19554 |
| cached_input_tokens | 0 | 7296 |
| seconds（CLI端到端） | 15.571 | 12.469 |
| cost_usd | null / NOT_MEASURED | null / NOT_MEASURED |

token来自原始 turn.completed 事件；费用未返回，不推算价格、不记0。
旧/新规则各一次，提示较明确，非盲评；模型默认、缓存、初始化和运行顺序可影响结果。
结论仅为同一小样本两边均满足判据；没有改善、节省或通用技能效果证据。
真实项目另在私有接入PR保存两套工作树的146项前端测试与Go构建/vet/test证据；测试兼容性不等于Agent效果。
## 验证/回放（无需模型请求）
在可信临时目录 clone old/new-rules.bundle。使用 PR #15 的 task_runs freeze/import 和 evaluation compare：
输入各snapshot、suite、results、artifacts，输出到源树外，与已保存reports/comparison核对。
import_public.py 是此次适配器；run_public.py/prepare_public.py 记录有限请求方式，不在回放中自动运行。
哈希仅证明一致性；不证明生产者签名、独立评审或语义正确性。人工核对可读scenario/答案/判据。
## 剩余验收
真实项目有分类构建/测试任务集和固定基线，但尚无其代码实现任务的Agent新旧对照或每次实际货币成本。
本组是匿名工作流决策pilot；#5仍partial。晋升需PR；本观测不授权安全规则放权。
#4/#7服务器策略按用户要求暂缓，独立审查/实际门禁尚未验收；不得关闭为已完成。
