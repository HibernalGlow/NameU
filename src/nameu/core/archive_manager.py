"""
NameU 压缩包管理器模块
提供统一的压缩包ID管理接口
"""

from typing import Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from nameset.manager import ArchiveIDManager

# 全局管理器实例缓存
_manager_instance: Optional['ArchiveIDManager'] = None


def get_archive_manager():
    """
    获取压缩包ID管理器单例实例
    
    Returns:
        ArchiveIDManager: 管理器实例，如果不可用则返回None
    """
    global _manager_instance
    
    if _manager_instance is None:
        try:
            from nameset.integration import get_manager
            _manager_instance = get_manager()
            logger.debug("NameU 获取压缩包ID管理器成功")
        except ImportError:
            logger.warning("压缩包ID管理系统不可用")
            return None
    
    return _manager_instance


def is_archive_management_available() -> bool:
    """
    检查压缩包ID管理功能是否可用
    
    Returns:
        bool: 是否可用
    """
    return get_archive_manager() is not None


def assign_archive_id(archive_path: str, artist_name: Optional[str] = None) -> Optional[str]:
    """
    为压缩包分配ID（如果尚未有ID）
    
    Args:
        archive_path: 压缩包路径
        artist_name: 画师名称
        
    Returns:
        Optional[str]: 压缩包ID，失败返回None
    """
    manager = get_archive_manager()
    if manager is None:
        return None
    
    try:
        # 获取或创建ID，但不重命名文件
        archive_id = manager._get_or_assign_archive_id(archive_path, artist_name)
        return archive_id
    except Exception as e:
        logger.error(f"分配压缩包ID失败: {e}")
        return None


def get_archive_id(archive_path: str) -> Optional[str]:
    """
    获取压缩包的ID（不创建新ID）
    
    Args:
        archive_path: 压缩包路径
        
    Returns:
        Optional[str]: 压缩包ID，没有则返回None
    """
    try:
        from nameset.integration import get_archive_id_from_file
        return get_archive_id_from_file(archive_path)
    except ImportError:
        logger.debug("无法获取压缩包ID，管理系统不可用")
        return None


def process_archive_rename(archive_path: str, new_name: str, artist_name: Optional[str] = None) -> bool:
    """
    处理压缩包重命名并管理ID
    
    Args:
        archive_path: 原文件路径
        new_name: 新文件名
        artist_name: 画师名称
        
    Returns:
        bool: 是否处理成功
    """
    manager = get_archive_manager()
    if manager is None:
        return False
    
    try:
        success, archive_id = manager.process_archive_rename(archive_path, new_name, artist_name)
        return success
    except Exception as e:
        logger.error(f"处理压缩包重命名失败: {e}")
        return False
