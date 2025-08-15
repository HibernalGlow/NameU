"""
NameSet 集成模块
为其他项目提供简化的集成接口
"""

import os
from typing import Optional, Tuple
from loguru import logger

from .manager import ArchiveIDManager
from .id_handler import ArchiveIDHandler


# 全局管理器实例
_global_manager: Optional[ArchiveIDManager] = None


def get_manager() -> ArchiveIDManager:
    """
    获取全局管理器实例
    
    Returns:
        ArchiveIDManager: 管理器实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = ArchiveIDManager()
    return _global_manager


def process_file_with_id_tracking(file_path: str, new_name: str, artist_name: Optional[str] = None) -> bool:
    """
    处理文件重命名并跟踪ID（替代原有的重命名逻辑）
    
    Args:
        file_path: 原文件路径
        new_name: 新文件名（包含扩展名）
        artist_name: 画师名称
        
    Returns:
        bool: 是否处理成功
    """
    try:
        # 只处理压缩文件
        if not file_path.lower().endswith(('.zip', '.rar', '.7z')):
            logger.debug(f"跳过非压缩文件: {file_path}")
            return False
        
        # 为每次调用创建独立的管理器实例
        with ArchiveIDManager() as manager:
            success, archive_id = manager.process_archive_rename(file_path, new_name, artist_name)
            
            if success and archive_id:
                logger.info(f"文件处理成功: {new_name} (ID: {archive_id})")
                return True
            else:
                logger.error(f"文件处理失败: {file_path}")
                return False
                
    except Exception as e:
        logger.error(f"处理文件时出错 {file_path}: {e}")
        return False


def get_archive_id_from_file(file_path: str) -> Optional[str]:
    """
    从文件获取压缩包ID
    
    Args:
        file_path: 文件路径
        
    Returns:
        Optional[str]: 压缩包ID，失败返回None
    """
    try:
        comment = ArchiveIDHandler.get_archive_comment(file_path)
        return ArchiveIDHandler.extract_id_from_comment(comment)
    except Exception as e:
        logger.error(f"获取压缩包ID失败 {file_path}: {e}")
        return None


# 简化接口
def process_archive_rename(archive_path: str, new_name: str, artist_name: Optional[str] = None) -> bool:
    """
    处理压缩包重命名的简化接口
    """
    return process_file_with_id_tracking(archive_path, new_name, artist_name)