# 子系统索引

为每个正在维护的关键子系统建立一份文档，列出职责、权威状态源、主要调用链、API/事件契约、失败路径、兼容性和可运行验证命令。引用精确的源代码文件或符号；不要复制大段源码。

| 子系统 | 文档 | 验证入口 |
|---|---|---|
| 示例 | [example.md](example.md) | 待填写 |
| Provider | [provider.md](provider.md) | `python -m unittest discover -s tests -p test_provider.py -v` |
| 初始化器 | [bootstrap.md](bootstrap.md) | `python -m unittest discover -s tests -p test_bootstrap.py -v` |
