# sensi2pinyin

独立的敏感词转拼音工具（复刻自 nameu 的敏感词模块，保持原理一致）。

- 词库来自 `lexicons/Sensitive-lexicon/.../SensitiveLexicon.json`（已随包一并分发）
- 支持将文本中的敏感词替换为拼音（支持多种风格）
- 提供 CLI：处理 .txt 文件，支持交互输入路径，支持递归与原地覆盖

## 使用

- 命令行

```bash
python -m sensi2pinyin --help
sensi2pinyin <路径>  # 路径为 .txt 或目录；留空会提示交互输入
```

- 作为库

```python
from sensi2pinyin import replace_sensitive_to_pinyin
print(replace_sensitive_to_pinyin("这是成人网站测试"))
```
