"""
NameSet - 压缩包唯一ID管理系统
为压缩包提供唯一ID、历史记录和智能匹配功能
"""

from .manager import ArchiveIDManager
from .database import ArchiveDatabase
from .id_handler import ArchiveIDHandler

__version__ = "1.0.0"
__author__ = "HibernalGlow"
__description__ = "压缩包唯一ID管理系统"

__all__ = ['ArchiveIDManager', 'ArchiveDatabase', 'ArchiveIDHandler']
