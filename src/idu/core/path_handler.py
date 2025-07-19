import os
from pathlib import Path
from datetime import datetime

from loguru import logger

class PathHandler:
    """路径处理类"""
    
    @staticmethod
    def get_artist_name(target_directory: str, archive_path: str, mode: str = 'multi') -> str:
        """从压缩文件路径中提取艺术家名称
        
        Args:
            target_directory: 目标目录路径
            archive_path: 压缩文件路径
            mode: 处理模式，'multi'表示多人模式，'single'表示单人模式
            
        Returns:
            str: 艺术家名称
        """
        if mode == 'single':
            # 单人模式：直接使用目标目录的最后一个文件夹名作为画师名
            return Path(target_directory).name
        else:
            # 多人模式：使用相对路径的第一级子文件夹名作为画师名
            try:
                # 将路径转换为相对路径
                archive_path = Path(archive_path)
                target_path = Path(target_directory)
                
                # 获取相对于目标目录的路径
                relative_path = archive_path.relative_to(target_path)
                
                # 获取第一级子文件夹名
                if len(relative_path.parts) > 0:
                    return relative_path.parts[0]
                
                logger.warning(f"[#process]无法从路径提取画师名: {archive_path}")
                return ""
                
            except Exception as e:
                logger.error(f"[#process]提取画师名失败: {str(e)}")
                return ""
    
    @staticmethod
    def get_relative_path(target_directory: str, archive_path: str) -> str:
        """获取相对路径
        
        Args:
            target_directory: 目标目录路径
            archive_path: 压缩文件路径
            
        Returns:
            str: 相对路径，不包含文件名
        """
        try:
            # 将路径转换为Path对象并规范化
            archive_path = Path(archive_path).resolve()
            target_path = Path(target_directory).resolve()
            
            # 获取相对路径
            relative_path = archive_path.relative_to(target_path)
            
            # 如果是直接在目标目录下的文件，返回"."
            if not relative_path.parent.parts:
                return "."
                
            # 返回父目录的相对路径（不包含文件名），保持原始路径分隔符
            relative_str = str(relative_path.parent)
            # 如果路径中包含反斜杠，保持原样
            if '\\' in archive_path.as_posix():
                relative_str = relative_str.replace('/', '\\')
            return relative_str
            
        except Exception as e:
            # 如果出错，记录错误但返回一个安全的默认值
            logger.error(f"[#process]获取相对路径失败 ({archive_path}): {str(e)}")
            return "."
    
    @staticmethod
    def get_uuid_path(uuid_directory: str, timestamp: str) -> str:
        """根据时间戳生成按年月日分层的UUID文件路径"""
        date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        year = str(date.year)
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"
        
        # 创建年月日层级目录
        year_dir = os.path.join(uuid_directory, year)
        month_dir = os.path.join(year_dir, month)
        day_dir = os.path.join(month_dir, day)
        
        # 确保目录存在
        os.makedirs(day_dir, exist_ok=True)
        
        return day_dir
    
    @staticmethod
    def get_short_path(long_path: str) -> str:
        """将长路径转换为短路径格式"""
        try:
            import win32api
            return win32api.GetShortPathName(long_path)
        except ImportError:
            return long_path
