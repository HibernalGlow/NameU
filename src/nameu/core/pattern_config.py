import toml
import os
from ast import literal_eval

# 配置文件路径
PATTERN_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'filename_patterns.toml')

# 缓存
_patterns_cache = None

def load_patterns():
    global _patterns_cache
    if _patterns_cache is None:
        with open(PATTERN_CONFIG_PATH, 'r', encoding='utf-8') as f:
            _patterns_cache = toml.load(f)
    return _patterns_cache

def get_patterns(group: str, file_type: str = 'all'):
    """
    获取指定 group（如 basic_patterns）和 type（如 image、archive、all）的 patterns 列表。
    优先 type 专属，没有就 fallback 到 all。
    返回：
      - patterns: list
      - is_pair: 是否为 (pattern, replacement) 二元组
    """
    patterns_dict = load_patterns().get(group, {})
    # 优先 type 专属
    if file_type in patterns_dict:
        patterns = patterns_dict[file_type]
    else:
        patterns = patterns_dict.get('all', {}).get('patterns', [])
    # 判断是否为二元组
    is_pair = bool(patterns and isinstance(patterns[0], list) and len(patterns[0]) == 2)
    # 解析字符串为正则表达式和替换内容
    if is_pair:
        # [(pattern, replacement), ...]
        return [(literal_eval(repr(p)), literal_eval(repr(r))) for p, r in patterns], True
    else:
        # [pattern, ...]
        return [literal_eval(repr(p)) for p in patterns], False 