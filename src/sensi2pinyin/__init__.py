"""
独立的敏感词转拼音工具包。
复刻自 nameu.core.sensitive_word_processor 的实现思想，不改变原理。
"""

from .processor import SensitiveWordProcessor, replace_sensitive_to_pinyin

__all__ = [
    "SensitiveWordProcessor",
    "replace_sensitive_to_pinyin",
]
