
import pytest
import os
import sys
from nameu.core.filename_processor import get_unique_filename

def test_size_prefix_to_suffix():
    """测试 (10P-57.1M) 这种表示大小的纯数字加上特定几个字母（PVMBGN-+大小写）的行首前缀改为后缀"""
    directory = "."
    artist_name = "Hatori Sama"
    filename = "(10P-57.1M) (尼尔：机械纪元・2B# 魔术师) 012. 2B Magician [Hatori Sama (奈奈紀)].zip"
    
    result = get_unique_filename(directory, filename, artist_name)
    
    # 期望结果中 [10P-57.1M] 被移动到末尾，而 (尼尔：机械纪元・2B# 魔术师) 保留在开头
    assert "[10P-57.1M]" in result
    assert result.endswith("[10P-57.1M].zip")
    assert result.startswith("(尼尔：机械纪元・2B# 魔术师)")

def test_dot_prefix_preserved():
    """测试带 ・ 的前缀不会被错误处理为 [] 后缀，而是保留为 () 前缀"""
    directory = "."
    artist_name = "None"
    
    # 有数字的情况 (2B)
    filename1 = "(尼尔：机械纪元・2B# 魔术师) 012. 2B Magician.zip"
    result1 = get_unique_filename(directory, filename1, artist_name)
    assert result1.startswith("(尼尔：机械纪元・2B# 魔术师)")
    
    # 没有数字的情况 (通常之前会被错误处理为 [])
    filename2 = "(尼尔：机械纪元・魔术师) 012. 2B Magician.zip"
    result2 = get_unique_filename(directory, filename2, artist_name)
    assert result2.startswith("(尼尔：机械纪元・魔术师)")

def test_various_size_prefixes():
    """测试各种不同的大小/数量前缀"""
    directory = "."
    artist_name = "None"
    
    cases = [
        ("(10P) test.zip", "test [10P].zip"),
        ("(57.1M) test.zip", "test [57.1M].zip"),
        ("(10P-57.1M) test.zip", "test [10P-57.1M].zip"),
        ("(10p + 5m) test.zip", "test [10p + 5m].zip"),
        ("(123KB) test.zip", "test [123KB].zip"),
    ]
    
    for filename, expected_part in cases:
        result = get_unique_filename(directory, filename, artist_name)
        assert expected_part in result
