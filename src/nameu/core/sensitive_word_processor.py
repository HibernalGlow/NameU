"""
敏感词处理模块，提供敏感词检测和拼音转换功能
"""

import os
import json
from loguru import logger
from pathlib import Path
import pypinyin
from typing import List, Set, Dict, Optional
class SensitiveWordProcessor:
    """敏感词处理器类"""
    
    def __init__(self):
        """初始化敏感词处理器"""
        self.sensitive_words = set()
        self.load_sensitive_words()

    def load_sensitive_words(self) -> None:
        """从JSON文件加载敏感词库"""
        try:
            # 获取敏感词词库JSON文件的绝对路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "lexicons", "Sensitive-lexicon", 
                                     "ThirdPartyCompatibleFormats", "TrChat", "SensitiveLexicon.json")
            
            # 如果文件不存在，尝试其他可能的路径
            if not os.path.exists(json_path):
                # 检查项目根目录下的路径
                root_dir = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
                alt_path = os.path.join(root_dir, "src", "nameu", "core", "lexicons", "Sensitive-lexicon", 
                                       "ThirdPartyCompatibleFormats", "TrChat", "SensitiveLexicon.json")
                if os.path.exists(alt_path):
                    json_path = alt_path
            
            # 如果还是找不到，检查temp目录
            if not os.path.exists(json_path):
                temp_path = os.path.join(root_dir, "sensitive-lexicon-temp", "Sensitive-lexicon-main",
                                        "ThirdPartyCompatibleFormats", "TrChat", "SensitiveLexicon.json")
                if os.path.exists(temp_path):
                    json_path = temp_path
            
            logger.info(f"尝试从以下路径加载敏感词库: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "words" in data and isinstance(data["words"], list):
                    self.sensitive_words = set(data["words"])
                    logger.info(f"成功加载 {len(self.sensitive_words)} 个敏感词")
                else:
                    logger.warning("敏感词库格式不正确")
        except Exception as e:
            logger.error(f"加载敏感词库失败: {e}")
    
    def is_sensitive(self, text: str) -> bool:
        """
        检查文本是否包含敏感词
        
        Args:
            text: 待检测的文本
            
        Returns:
            bool: 如果文本包含敏感词返回True，否则返回False
        """
        if not text or not self.sensitive_words:
            return False
            
        for word in self.sensitive_words:
            if word in text:
                return True
                
        return False
    
    def get_matching_sensitive_words(self, text: str) -> List[str]:
        """
        获取文本中包含的所有敏感词
        
        Args:
            text: 待检测的文本
            
        Returns:
            List[str]: 文本中包含的敏感词列表
        """
        if not text or not self.sensitive_words:
            return []
            
        matching_words = []
        for word in self.sensitive_words:
            if word in text:
                matching_words.append(word)
                
        return matching_words
    
    def convert_to_pinyin(self, text: str, style: str = 'default') -> str:
        """
        将文本转换为拼音
        
        Args:
            text: 待转换的文本
            style: 拼音风格，可选值：
                  'default': 普通风格，不带声调
                  'tone': 带声调
                  'first_letter': 首字母
                  'initials': 声母
                  'finals': 韵母
                  
        Returns:
            str: 转换后的拼音文本
        """
        style_map = {
            'default': pypinyin.NORMAL,
            'tone': pypinyin.TONE,
            'first_letter': pypinyin.FIRST_LETTER,
            'initials': pypinyin.INITIALS,
            'finals': pypinyin.FINALS
        }
        
        style_code = style_map.get(style, pypinyin.NORMAL)
        
        result = pypinyin.lazy_pinyin(text, style=style_code)
        return ''.join(result)
    


# 创建单例实例
sensitive_processor = SensitiveWordProcessor()
