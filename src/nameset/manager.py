"""
压缩包ID管理器
统一管理压缩包的ID分配、历史记录和名称匹配
"""

import os
from typing import Optional, Dict, List, Any, Tuple
from loguru import logger

from .database import ArchiveDatabase
from .id_handler import ArchiveIDHandler


class ArchiveIDManager:
    """压缩包ID管理器主类"""
    
    def __init__(self, db_path: str = None):
        """
        初始化ID管理器
        
        Args:
            db_path: 数据库路径，默认使用项目根目录下的archives.db
        """
        if db_path is None:
            # 默认使用项目根目录的数据库
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, 'archives.db')
        
        self.db = ArchiveDatabase(db_path)
        self.db_path = db_path
        logger.info(f"压缩包ID管理器初始化完成，数据库: {db_path}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def close(self):
        """关闭管理器"""
        if hasattr(self, 'db') and self.db:
            try:
                self.db.close()
            except Exception as e:
                logger.warning(f"关闭数据库时出错: {e}")
            finally:
                self.db = None
        logger.debug("压缩包ID管理器已关闭")
    
    def process_archive_rename(self, archive_path: str, new_name: str, artist_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        处理压缩包重命名，包含完整的ID管理流程
        
        Args:
            archive_path: 压缩包当前路径
            new_name: 新的文件名（含扩展名）
            artist_name: 画师名称
            
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 压缩包ID)
        """
        try:
            current_name = os.path.basename(archive_path)
            logger.info(f"开始处理压缩包重命名: {current_name} -> {new_name}")
            
            # 第1步：检查或创建压缩包ID
            archive_id = self._get_or_assign_archive_id(archive_path, artist_name)
            if not archive_id:
                logger.error(f"无法获取或创建压缩包ID: {archive_path}")
                return False, None
            
            # 第2步：执行文件重命名
            new_path = os.path.join(os.path.dirname(archive_path), new_name)
            if current_name != new_name:
                try:
                    os.rename(archive_path, new_path)
                    logger.info(f"文件重命名成功: {current_name} -> {new_name}")
                except Exception as e:
                    logger.error(f"文件重命名失败: {e}")
                    return False, archive_id
            else:
                new_path = archive_path
                logger.debug(f"文件名未变化，跳过重命名: {new_name}")
            
            # 第3步：更新数据库记录
            metadata = {
                'artist_name': artist_name,
                'file_path': new_path,
                'rename_method': 'nameu',
                'operation_type': 'rename',
                'source': 'nameu_system',
                'file_size': self._get_file_size(new_path),
                'file_extension': os.path.splitext(new_name)[1].lower()
            }
            
            success = self.db.update_archive_name(
                archive_id=archive_id,
                new_name=new_name,
                old_name=current_name if current_name != new_name else None,
                reason="nameu重命名",
                metadata=metadata
            )
            
            if success:
                # 更新文件路径
                self.db.update_file_path(archive_id, new_path)
                logger.info(f"压缩包重命名处理完成: {archive_id}")
                return True, archive_id
            else:
                logger.error(f"更新数据库记录失败: {archive_id}")
                return False, archive_id
                
        except Exception as e:
            logger.error(f"处理压缩包重命名时出错: {e}")
            return False, None
    
    def _get_or_assign_archive_id(self, archive_path: str, artist_name: Optional[str] = None) -> Optional[str]:
        """
        获取或分配压缩包ID（完整流程）
        
        Args:
            archive_path: 压缩包路径
            artist_name: 画师名称
            
        Returns:
            Optional[str]: 压缩包ID，失败返回None
        """
        current_name = os.path.basename(archive_path)
        
        # 1. 检查压缩包注释中的ID
        logger.debug(f"检查压缩包注释中的ID: {current_name}")
        archive_id = ArchiveIDHandler.get_or_create_archive_id(archive_path)
        
        if archive_id:
            # 检查数据库中是否已存在此ID
            existing_info = self.db.get_archive_info(archive_id)
            if existing_info:
                # 更新路径（可能文件被移动了）
                if existing_info['file_path'] != archive_path:
                    self.db.update_file_path(archive_id, archive_path)
                    logger.debug(f"更新文件路径: {archive_id}")
                return archive_id
            else:
                # ID存在但数据库中没有记录，创建新记录
                if self.db.create_archive_record(archive_id, archive_path, current_name, artist_name):
                    logger.info(f"为现有ID创建数据库记录: {archive_id}")
                    return archive_id
        
        # 2. 尝试从数据库历史中匹配
        logger.debug(f"从数据库历史中匹配: {current_name}")
        archive_id = self._match_from_database_history(archive_path, current_name, artist_name)
        if archive_id:
            logger.info(f"从数据库历史匹配到ID: {archive_id}")
            # 更新压缩包注释
            ArchiveIDHandler.set_archive_comment(
                archive_path, 
                ArchiveIDHandler.create_comment_with_id(archive_id, {'matched_from': 'database'})
            )
            return archive_id
        
        # 3. 分配新ID
        logger.debug(f"分配新ID: {current_name}")
        new_id = ArchiveIDHandler.generate_id()
        if ArchiveIDHandler.set_archive_comment(
            archive_path,
            ArchiveIDHandler.create_comment_with_id(new_id, {'artist_name': artist_name})
        ):
            if self.db.create_archive_record(new_id, archive_path, current_name, artist_name):
                logger.info(f"分配新ID: {new_id}")
                return new_id
        
        logger.error(f"无法为压缩包分配ID: {archive_path}")
        return None
    
    def _match_from_database_history(self, archive_path: str, current_name: str, artist_name: Optional[str] = None) -> Optional[str]:
        """
        从数据库历史中匹配压缩包
        
        Args:
            archive_path: 压缩包路径
            current_name: 当前文件名
            artist_name: 画师名称
            
        Returns:
            Optional[str]: 匹配到的压缩包ID，未匹配返回None
        """
        # 先尝试通过文件哈希匹配（最准确）
        from .database import ArchiveDatabase
        temp_db = ArchiveDatabase(self.db.db_path)
        file_hash = temp_db._calculate_file_hash(archive_path)
        
        if file_hash:
            archive_id = self.db.get_archive_id_by_hash(file_hash)
            if archive_id:
                logger.info(f"通过文件哈希匹配到ID: {archive_id}")
                # 更新文件路径
                self.db.update_file_path(archive_id, archive_path)
                return archive_id
        
        # 通过文件名模糊匹配
        name_without_ext = os.path.splitext(current_name)[0]
        matches = self.db.find_archive_by_name(name_without_ext, artist_name)
        
        if matches:
            # 取第一个匹配结果（按更新时间排序）
            best_match = matches[0]
            logger.info(f"通过文件名匹配到候选ID: {best_match['id']} (相似度较高)")
            
            # 这里可以添加更复杂的匹配逻辑，比如编辑距离计算
            # 为了简单起见，直接返回第一个匹配
            return best_match['id']
        
        return None
    
    def get_archive_info(self, archive_id: str) -> Optional[Dict[str, Any]]:
        """
        获取压缩包的完整信息
        
        Args:
            archive_id: 压缩包ID
            
        Returns:
            Optional[Dict[str, Any]]: 压缩包信息
        """
        return self.db.get_archive_info(archive_id)
    
    def get_archive_history(self, archive_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取压缩包的历史记录
        
        Args:
            archive_id: 压缩包ID
            limit: 返回记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        return self.db.get_archive_history(archive_id, limit)
    
    def search_archives(self, query: str, artist_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索压缩包
        
        Args:
            query: 搜索关键词
            artist_name: 画师名称过滤
            
        Returns:
            List[Dict[str, Any]]: 匹配的压缩包列表
        """
        return self.db.find_archive_by_name(query, artist_name)
    
    def update_archive_metadata(self, archive_path: str, metadata: Dict[str, Any]) -> bool:
        """
        更新压缩包的元数据
        
        Args:
            archive_path: 压缩包路径
            metadata: 要更新的元数据
            
        Returns:
            bool: 是否更新成功
        """
        return ArchiveIDHandler.update_comment_metadata(archive_path, metadata)

    def _get_file_size(self, file_path: str) -> Optional[int]:
        """
        获取文件大小

        Args:
            file_path: 文件路径

        Returns:
            Optional[int]: 文件大小（字节），失败返回None
        """
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.warning(f"获取文件大小失败 {file_path}: {e}")
            return None

    def get_complete_archive_metadata(self, archive_id: str) -> Optional[Dict[str, Any]]:
        """
        获取压缩包的完整历史元数据

        Args:
            archive_id: 压缩包ID

        Returns:
            Optional[Dict[str, Any]]: 完整的历史元数据
        """
        return self.db.get_complete_archive_metadata(archive_id)

    def get_archive_name_history(self, archive_id: str) -> List[Dict[str, Any]]:
        """
        获取压缩包的名称变更历史

        Args:
            archive_id: 压缩包ID

        Returns:
            List[Dict[str, Any]]: 名称变更历史列表
        """
        return self.db.get_archive_name_history(archive_id)

    def get_archive_statistics(self, archive_id: str) -> Optional[Dict[str, Any]]:
        """
        获取压缩包的统计信息

        Args:
            archive_id: 压缩包ID

        Returns:
            Optional[Dict[str, Any]]: 统计信息
        """
        return self.db.get_archive_statistics(archive_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        import sqlite3
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # 总压缩包数量
                cursor.execute('SELECT COUNT(*) FROM archive_info')
                total_archives = cursor.fetchone()[0]
                
                # 总历史记录数量
                cursor.execute('SELECT COUNT(*) FROM archive_history')
                total_history = cursor.fetchone()[0]
                
                # 按画师分组的统计
                cursor.execute('''
                    SELECT artist_name, COUNT(*) 
                    FROM archive_info 
                    WHERE artist_name IS NOT NULL 
                    GROUP BY artist_name 
                    ORDER BY COUNT(*) DESC 
                    LIMIT 10
                ''')
                top_artists = cursor.fetchall()
                
                return {
                    'total_archives': total_archives,
                    'total_history_records': total_history,
                    'top_artists': [{'name': row[0], 'count': row[1]} for row in top_artists]
                }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                'total_archives': 0,
                'total_history_records': 0,
                'top_artists': []
            }
