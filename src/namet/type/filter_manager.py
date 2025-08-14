"""
过滤管理器

负责处理文件格式过滤逻辑，包括包含/排除过滤器和压缩包级别过滤
"""

from typing import Dict, List, Set
from .file_type_detector import get_file_type
from .file_type_detector import get_kind


class FilterManager:
    """过滤管理器，处理文件和压缩包的过滤逻辑"""
    
    def __init__(self, format_filters: Dict = None):
        """初始化过滤管理器
        
        Args:
            format_filters: 格式过滤配置，包含include/exclude/formats/type/part等
        """
        self.format_filters = format_filters or {}
    
    def is_file_format_match(self, file_path: str, filters: Dict = None) -> bool:
        """统一判断文件/文件夹是否符合过滤条件
        Args:
            file_path: 路径
            filters: 过滤参数字典
        Returns:
            bool: 符合条件返回True，否则False
        """
        import os
        from .file_type_detector import get_file_type
        filters = filters or self.format_filters or {}
        include_formats = filters.get('--include', [])
        exclude_formats = filters.get('--exclude', [])
        formats = filters.get('--formats', [])
        file_type = filters.get('--type')
        # formats 兼容 include
        if formats and not include_formats:
            include_formats = formats
        # 获取文件类型
        current_file_type = get_file_type(file_path)
        # 文件夹扩展名特殊处理
        if current_file_type == 'folder':
            ext = 'folder'
        else:
            ext = os.path.splitext(file_path.lower())[1]
            if ext.startswith('.'):
                ext = ext[1:]
        # 类型过滤
        if file_type and current_file_type != file_type:
            return False
        # 排除列表
        if exclude_formats and ext in exclude_formats:
            return False
        # 包含列表
        if include_formats and ext not in include_formats:
            return False
        return True
    
    def should_filter_file(self, file_path: str) -> bool:
        """判断文件或文件夹是否应该被过滤掉（不符合条件返回True）"""
        if not self.format_filters:
            return False
        return not self.is_file_format_match(file_path, self.format_filters)
    
    def is_part_mode_enabled(self) -> bool:
        """检查是否启用了部分解压模式
        
        Returns:
            bool: 如果启用了部分解压模式返回True，否则返回False
        """
        return self.format_filters.get('--part', False)
