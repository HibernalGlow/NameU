"""
敏感词处理与转拼音（独立包）
保持与原实现一致的基本原理：
- 从 JSON 词库加载敏感词
- 通过包含判断检测敏感词
- 使用 pypinyin 按风格转换为拼音
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Optional, Set

from loguru import logger
import pypinyin


class SensitiveWordProcessor:
    """敏感词处理器（独立包版本）"""

    def __init__(self) -> None:
        self.sensitive_words: Set[str] = set()
        self.load_sensitive_words()

    def _candidate_lexicon_paths(self) -> List[str]:
        """可能的敏感词库 JSON 路径列表（按优先级）。"""
        paths: List[str] = []
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 1) 本包内的相对路径（若未来复制词库到本包）
        paths.append(
            os.path.join(
                current_dir,
                "lexicons",
                "Sensitive-lexicon",
                "ThirdPartyCompatibleFormats",
                "TrChat",
                "SensitiveLexicon.json",
            )
        )
        # 2) 兼容原项目路径：src/nameu/core/lexicons/...
        root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
        paths.append(
            os.path.join(
                root_dir,
                "nameu",
                "core",
                "lexicons",
                "Sensitive-lexicon",
                "ThirdPartyCompatibleFormats",
                "TrChat",
                "SensitiveLexicon.json",
            )
        )
        # 3) 进一步回退：尝试项目根的绝对路径拼接
        repo_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        paths.append(
            os.path.join(
                repo_root,
                "src",
                "nameu",
                "core",
                "lexicons",
                "Sensitive-lexicon",
                "ThirdPartyCompatibleFormats",
                "TrChat",
                "SensitiveLexicon.json",
            )
        )
        # 4) 兼容临时解压目录（与原实现一致）
        paths.append(
            os.path.join(
                repo_root,
                "sensitive-lexicon-temp",
                "Sensitive-lexicon-main",
                "ThirdPartyCompatibleFormats",
                "TrChat",
                "SensitiveLexicon.json",
            )
        )
        return paths

    def load_sensitive_words(self) -> None:
        """从 JSON 文件加载敏感词库。"""
        for path in self._candidate_lexicon_paths():
            try:
                if os.path.exists(path):
                    logger.info(f"加载敏感词库: {path}")
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        words = data.get("words")
                        if isinstance(words, list):
                            self.sensitive_words = set(words)
                            logger.info(f"已加载敏感词数: {len(self.sensitive_words)}")
                            return
                        else:
                            logger.warning("敏感词库格式不正确，继续尝试其他路径…")
            except Exception as e:  # noqa: BLE001
                logger.error(f"加载敏感词库失败（{path}）: {e}")
        if not self.sensitive_words:
            logger.warning("未能加载敏感词库，将作为空词库运行。")

    # 基本能力保持与原实现一致
    def is_sensitive(self, text: str) -> bool:
        if not text or not self.sensitive_words:
            return False
        return any(word in text for word in self.sensitive_words)

    def get_matching_sensitive_words(self, text: str) -> List[str]:
        if not text or not self.sensitive_words:
            return []
        return [w for w in self.sensitive_words if w in text]

    def convert_to_pinyin(self, text: str, style: str = "default") -> str:
        style_map = {
            "default": pypinyin.NORMAL,
            "tone": pypinyin.TONE,
            "first_letter": pypinyin.FIRST_LETTER,
            "initials": pypinyin.INITIALS,
            "finals": pypinyin.FINALS,
        }
        style_code = style_map.get(style, pypinyin.NORMAL)
        result = pypinyin.lazy_pinyin(text, style=style_code)
        return "".join(result)


# 单例（便于 CLI 直接使用）
processor = SensitiveWordProcessor()


def replace_sensitive_to_pinyin(text: str, style: str = "default") -> str:
    """将文本中的敏感词替换为指定风格的拼音。"""
    if not processor.is_sensitive(text):
        return text
    replaced = text
    # 与原理保持一致：找到出现过的词再做替换
    for word in processor.get_matching_sensitive_words(text):
        pinyin = processor.convert_to_pinyin(word, style)
        replaced = replaced.replace(word, pinyin)
    return replaced
