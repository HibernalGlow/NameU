"""
压缩包名称恢复功能
支持将指定文件夹下的压缩包恢复到历史中的指定名称
"""

import os
from typing import Callable, List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from ..database import ArchiveDatabase
from ..manager import ArchiveIDManager
from ..id_handler import ArchiveIDHandler


class ArchiveRestoreManager:
    """压缩包名称恢复管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化恢复管理器
        
        Args:
            db_path: 数据库路径
        """
        self.manager = ArchiveIDManager(db_path)
        self.db = self.manager.db
    
    def scan_folder_archives(
        self,
        folder_path: str,
        recursive: bool = True,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        扫描文件夹下的所有压缩包并获取其历史信息
        
        Args:
            folder_path: 文件夹路径
            recursive: 是否递归扫描子目录
            
        Returns:
            List[Dict[str, Any]]: 压缩包信息列表
        """
        archives = []
        
        # 支持的压缩包格式
        archive_extensions = ('.zip', '.rar', '.7z')
        
        try:
            if recursive:
                walker = os.walk(folder_path)
            else:
                filenames = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                walker = [(folder_path, [], filenames)]

            for root, _, filenames in walker:
                for filename in filenames:
                    if filename.lower().endswith(archive_extensions):
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, folder_path)

                        # 尝试获取压缩包ID
                        archive_info = self._get_archive_info_by_name(filename, file_path)
                        if archive_info:
                            archive_info['relative_path'] = relative_path
                            archives.append(archive_info)
                        else:
                            archives.append({
                                'current_file': filename,
                                'file_path': file_path,
                                'relative_path': relative_path,
                                'archive_id': None,
                                'has_history': False,
                                'history_count': 0,
                                'message': '未找到历史记录'
                            })

                        if on_progress:
                            on_progress(file_path)
        
        except Exception as e:
            logger.error(f"扫描文件夹失败 {folder_path}: {e}")
        
        return archives
    
    def _get_archive_info_by_name(self, filename: str, file_path: str) -> Optional[Dict[str, Any]]:
        """
        根据文件名获取压缩包信息
        
        Args:
            filename: 文件名
            file_path: 文件路径
            
        Returns:
            Optional[Dict[str, Any]]: 压缩包信息
        """
        archive_id: Optional[str] = None

        # 方法1: 通过压缩包注释提取ID
        comment = ArchiveIDHandler.get_archive_comment(file_path)
        archive_id = ArchiveIDHandler.extract_id_from_comment(comment)

        # 方法2: 直接从路径查找
        if not archive_id:
            archive_id = self.db.get_archive_id_by_path(file_path)

        # 方法3: 通过名称模糊匹配
        if not archive_id:
            name_without_ext = os.path.splitext(filename)[0]
            matches = self.db.find_archive_by_name(name_without_ext)
            if matches:
                archive_id = matches[0]['id']
        
        # 方法4: 通过文件哈希匹配
        if not archive_id:
            file_hash = self.db._calculate_file_hash(file_path)
            if file_hash:
                archive_id = self.db.get_archive_id_by_hash(file_hash)
        
        if archive_id:
            # 获取基本信息
            info = self.db.get_archive_info(archive_id)
            history = self.db.get_archive_history(archive_id, limit=50)
            
            return {
                'current_file': filename,
                'file_path': file_path,
                'archive_id': archive_id,
                'current_name': info['current_name'] if info else filename,
                'artist_name': info['artist_name'] if info else None,
                'has_history': len(history) > 0,
                'history_count': len(history),
                'history': history,
                'created_at': info['created_at'] if info else None
            }
        
        return None
    
    def get_restore_options(self, archive_id: str) -> List[Dict[str, Any]]:
        """
        获取可恢复的历史名称选项
        
        Args:
            archive_id: 压缩包ID
            
        Returns:
            List[Dict[str, Any]]: 可恢复的选项列表
        """
        history = self.db.get_archive_history(archive_id, limit=50)
        options = []
        
        for i, record in enumerate(history):
            # 提供恢复到old_name或new_name的选项
            if record['old_name'] and record['old_name'] != record['new_name']:
                options.append({
                    'option_id': f"{i}_old",
                    'name': record['old_name'],
                    'timestamp': record['timestamp'],
                    'reason': record['reason'],
                    'type': 'old_name',
                    'description': f"恢复到重命名前: {record['old_name']}"
                })
            
            options.append({
                'option_id': f"{i}_new",
                'name': record['new_name'],
                'timestamp': record['timestamp'],
                'reason': record['reason'],
                'type': 'new_name',
                'description': f"恢复到当时状态: {record['new_name']}"
            })
        
        # 去重并按时间排序
        unique_options = {}
        for option in options:
            key = option['name']
            if key not in unique_options or option['timestamp'] > unique_options[key]['timestamp']:
                unique_options[key] = option
        
        return sorted(unique_options.values(), key=lambda x: x['timestamp'], reverse=True)
    
    def restore_archive_name(self, file_path: str, target_name: str, reason: str = "手动恢复") -> Tuple[bool, str]:
        """
        恢复压缩包到指定名称
        
        Args:
            file_path: 当前文件路径
            target_name: 目标名称
            reason: 恢复原因
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            current_filename = os.path.basename(file_path)
            target_path = os.path.join(os.path.dirname(file_path), target_name)
            
            # 检查目标文件是否已存在
            if os.path.exists(target_path) and target_path != file_path:
                return False, f"目标文件已存在: {target_name}"
            
            # 执行重命名
            if current_filename != target_name:
                os.rename(file_path, target_path)
                logger.info(f"文件恢复成功: {current_filename} -> {target_name}")
            
            # 更新数据库记录
            success, archive_id = self.manager.process_archive_rename(
                file_path if current_filename == target_name else target_path,
                target_name,
                None  # 不修改画师名称
            )
            
            if success:
                return True, f"恢复成功: {target_name}"
            else:
                return False, "数据库更新失败"
                
        except Exception as e:
            logger.error(f"恢复文件名失败: {e}")
            return False, f"恢复失败: {str(e)}"
    
    def batch_restore_folder(self, folder_path: str, restore_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量恢复文件夹下的压缩包
        
        Args:
            folder_path: 文件夹路径
            restore_rules: 恢复规则列表
                [
                    {
                        "archive_id": "压缩包ID",
                        "target_name": "目标名称",
                        "reason": "恢复原因"
                    }
                ]
        
        Returns:
            Dict[str, Any]: 恢复结果统计
        """
        results = {
            'total': len(restore_rules),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        for rule in restore_rules:
            archive_id = rule['archive_id']
            target_name = rule['target_name']
            reason = rule.get('reason', '批量恢复')
            
            # 获取当前文件信息
            info = self.db.get_archive_info(archive_id)
            if not info:
                results['details'].append({
                    'archive_id': archive_id,
                    'success': False,
                    'message': '找不到压缩包信息'
                })
                results['failed'] += 1
                continue
            
            current_path = info['file_path']
            if not os.path.exists(current_path):
                results['details'].append({
                    'archive_id': archive_id,
                    'current_name': info['current_name'],
                    'success': False,
                    'message': '文件不存在'
                })
                results['failed'] += 1
                continue
            
            # 执行恢复
            success, message = self.restore_archive_name(current_path, target_name, reason)
            results['details'].append({
                'archive_id': archive_id,
                'current_name': info['current_name'],
                'target_name': target_name,
                'success': success,
                'message': message
            })
            
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    def preview_restore_by_date(self, folder_path: str, target_date: str) -> List[Dict[str, Any]]:
        """
        预览恢复到指定日期状态的效果
        
        Args:
            folder_path: 文件夹路径
            target_date: 目标日期 (格式: "2025-07-15")
            
        Returns:
            List[Dict[str, Any]]: 预览结果
        """
        archives = self.scan_folder_archives(folder_path)
        preview = []
        
        for archive in archives:
            if not archive.get('has_history'):
                continue
            
            archive_id = archive['archive_id']
            current_name = archive['current_file']
            
            # 查找指定日期最接近的历史记录
            target_name = self._find_name_by_date(archive_id, target_date)
            
            preview.append({
                'archive_id': archive_id,
                'current_name': current_name,
                'target_name': target_name,
                'will_change': current_name != target_name,
                'file_path': archive['file_path']
            })
        
        return preview
    
    def _find_name_by_date(self, archive_id: str, target_date: str) -> str:
        """
        查找指定日期时的文件名
        
        Args:
            archive_id: 压缩包ID
            target_date: 目标日期
            
        Returns:
            str: 当时的文件名
        """
        history = self.db.get_archive_history(archive_id, limit=100)
        target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
        
        # 查找最接近且不超过目标日期的记录
        for record in reversed(history):  # 从最早的记录开始
            record_time = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
            if record_time.date() <= target_datetime.date():
                return record['new_name']
        
        # 如果没有找到，返回当前名称
        info = self.db.get_archive_info(archive_id)
        return info['current_name'] if info else "未知"
    
    def close(self):
        """关闭管理器"""
        if hasattr(self, 'manager'):
            self.manager.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
