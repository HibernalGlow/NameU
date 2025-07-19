"""
NameU与NameSet的集成模块
"""

import os
from typing import Optional
from loguru import logger

try:
    # 尝试导入独立的nameset包
    from nameset.integration import process_file_with_id_tracking
    NAMESET_AVAILABLE = True
except ImportError:

        logger.warning("NameSet系统不可用，将使用传统重命名方式")
        NAMESET_AVAILABLE = False


def process_archive_with_tracking(file_path: str, new_name: str, artist_name: Optional[str] = None) -> bool:
    """
    使用NameSet跟踪处理压缩包重命名
    
    Args:
        file_path: 文件路径
        new_name: 新文件名
        artist_name: 画师名称
        
    Returns:
        bool: 是否处理成功
    """
    if NAMESET_AVAILABLE:
        return process_file_with_id_tracking(file_path, new_name, artist_name)
    else:
        # 回退到传统重命名
        try:
            new_path = os.path.join(os.path.dirname(file_path), new_name)
            os.rename(file_path, new_path)
            return True
        except Exception as e:
            logger.error(f"传统重命名失败: {e}")
            return False


def is_nameset_available() -> bool:
    """检查NameSet是否可用"""
    return NAMESET_AVAILABLE
