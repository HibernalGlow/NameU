"""
压缩包数据库管理模块
使用SQLite存储压缩包的ID、历史记录和名称变更
"""

import os
import sqlite3
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from loguru import logger
import hashlib


class ArchiveDatabase:
    """压缩包数据库管理类"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_database()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def close(self):
        """关闭数据库连接"""
        # SQLite使用的是临时连接，无需特殊处理
        pass
    
    def _init_database(self):
        """初始化数据库表结构"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 使用临时连接初始化表结构
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # 压缩包基本信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS archive_info (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_hash TEXT,
                    current_name TEXT NOT NULL,
                    artist_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 压缩包历史记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS archive_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    archive_id TEXT NOT NULL,
                    old_name TEXT,
                    new_name TEXT NOT NULL,
                    reason TEXT,
                    metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (archive_id) REFERENCES archive_info (id)
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_archive_path ON archive_info (file_path)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_archive_hash ON archive_info (file_hash)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_history_archive_id ON archive_history (archive_id)
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    def _calculate_file_hash(self, file_path: str, chunk_size: int = 8192) -> Optional[str]:
        """
        计算文件的MD5哈希值（用于匹配）
        
        Args:
            file_path: 文件路径
            chunk_size: 读取块大小
            
        Returns:
            Optional[str]: 文件哈希值，失败返回None
        """
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"计算文件哈希失败 {file_path}: {e}")
            return None
    
    def get_archive_id_by_path(self, file_path: str) -> Optional[str]:
        """
        根据文件路径获取压缩包ID
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[str]: 压缩包ID，未找到返回None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM archive_info WHERE file_path = ?
            ''', (file_path,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_archive_id_by_hash(self, file_hash: str) -> Optional[str]:
        """
        根据文件哈希获取压缩包ID（用于文件移动后的匹配）
        
        Args:
            file_hash: 文件哈希值
            
        Returns:
            Optional[str]: 压缩包ID，未找到返回None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM archive_info WHERE file_hash = ?
            ''', (file_hash,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def find_archive_by_name(self, name: str, artist_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        根据文件名查找历史记录（模糊匹配）
        
        Args:
            name: 文件名（不含扩展名）
            artist_name: 画师名称（可选）
            
        Returns:
            List[Dict[str, Any]]: 匹配的记录列表
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            base_query = '''
                SELECT DISTINCT ai.id, ai.current_name, ai.artist_name, ai.created_at
                FROM archive_info ai
                LEFT JOIN archive_history ah ON ai.id = ah.archive_id
                WHERE (ai.current_name LIKE ? OR ah.old_name LIKE ? OR ah.new_name LIKE ?)
            '''
            params = [f'%{name}%', f'%{name}%', f'%{name}%']
            
            if artist_name:
                base_query += ' AND ai.artist_name = ?'
                params.append(artist_name)
            
            base_query += ' ORDER BY ai.updated_at DESC LIMIT 10'
            
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'current_name': row[1],
                    'artist_name': row[2],
                    'created_at': row[3]
                }
                for row in results
            ]
    
    def create_archive_record(self, archive_id: str, file_path: str, current_name: str, 
                            artist_name: Optional[str] = None) -> bool:
        """
        创建新的压缩包记录
        
        Args:
            archive_id: 压缩包ID
            file_path: 文件路径
            current_name: 当前文件名
            artist_name: 画师名称
            
        Returns:
            bool: 是否创建成功
        """
        try:
            file_hash = self._calculate_file_hash(file_path)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO archive_info (id, file_path, file_hash, current_name, artist_name)
                    VALUES (?, ?, ?, ?, ?)
                ''', (archive_id, file_path, file_hash, current_name, artist_name))
                conn.commit()
                
            logger.info(f"创建压缩包记录: {archive_id} -> {current_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建压缩包记录失败: {e}")
            return False
    
    def update_archive_name(self, archive_id: str, new_name: str, old_name: Optional[str] = None,
                          reason: str = "nameu重命名", metadata: Optional[Dict] = None) -> bool:
        """
        更新压缩包名称并记录历史

        Args:
            archive_id: 压缩包ID
            new_name: 新文件名
            old_name: 旧文件名
            reason: 修改原因
            metadata: 额外的元数据

        Returns:
            bool: 是否更新成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 获取当前名称
                if not old_name:
                    cursor.execute('SELECT current_name FROM archive_info WHERE id = ?', (archive_id,))
                    result = cursor.fetchone()
                    if result:
                        old_name = result[0]

                # 更新当前名称
                cursor.execute('''
                    UPDATE archive_info
                    SET current_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_name, archive_id))

                # 构建完整的历史元数据
                complete_metadata = self._build_complete_metadata(archive_id, metadata)

                # 添加历史记录
                metadata_json = json.dumps(complete_metadata, ensure_ascii=False) if complete_metadata else None
                cursor.execute('''
                    INSERT INTO archive_history (archive_id, old_name, new_name, reason, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (archive_id, old_name, new_name, reason, metadata_json))

                conn.commit()

            logger.info(f"更新压缩包名称: {archive_id} {old_name} -> {new_name}")
            return True

        except Exception as e:
            logger.error(f"更新压缩包名称失败: {e}")
            return False

    def _build_complete_metadata(self, archive_id: str, current_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        构建包含完整历史信息的元数据

        Args:
            archive_id: 压缩包ID
            current_metadata: 当前操作的元数据

        Returns:
            Dict[str, Any]: 完整的元数据，包含所有历史信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 获取基本信息
                cursor.execute('''
                    SELECT current_name, artist_name, created_at, file_path, file_hash
                    FROM archive_info WHERE id = ?
                ''', (archive_id,))
                info_result = cursor.fetchone()

                # 获取所有历史记录
                cursor.execute('''
                    SELECT old_name, new_name, reason, metadata, timestamp
                    FROM archive_history
                    WHERE archive_id = ?
                    ORDER BY timestamp ASC
                ''', (archive_id,))
                history_results = cursor.fetchall()

                # 构建完整元数据
                complete_metadata = {
                    'archive_id': archive_id,
                    'first_created_at': info_result[2] if info_result else None,
                    'current_timestamp': datetime.now().isoformat(),
                    'basic_info': {
                        'current_name': info_result[0] if info_result else None,
                        'artist_name': info_result[1] if info_result else None,
                        'file_path': info_result[3] if info_result else None,
                        'file_hash': info_result[4] if info_result else None
                    },
                    'name_history': [],
                    'operation_history': [],
                    'current_operation': current_metadata or {}
                }

                # 添加历史记录
                for record in history_results:
                    old_name, new_name, reason, metadata_str, timestamp = record

                    # 名称变更历史
                    if old_name and old_name != new_name:
                        complete_metadata['name_history'].append({
                            'from': old_name,
                            'to': new_name,
                            'timestamp': timestamp,
                            'reason': reason
                        })

                    # 操作历史
                    operation_record = {
                        'timestamp': timestamp,
                        'reason': reason,
                        'old_name': old_name,
                        'new_name': new_name
                    }

                    # 解析历史元数据
                    if metadata_str:
                        try:
                            historical_metadata = json.loads(metadata_str)
                            operation_record['metadata'] = historical_metadata
                        except:
                            operation_record['metadata_raw'] = metadata_str

                    complete_metadata['operation_history'].append(operation_record)

                # 统计信息
                complete_metadata['statistics'] = {
                    'total_operations': len(history_results),
                    'total_renames': len([r for r in history_results if r[0] and r[0] != r[1]]),
                    'unique_names': len(set([r[1] for r in history_results if r[1]])),
                    'first_operation': history_results[0][4] if history_results else None,
                    'last_operation': history_results[-1][4] if history_results else None
                }

                return complete_metadata

        except Exception as e:
            logger.error(f"构建完整元数据失败: {e}")
            return current_metadata or {}

    def get_complete_archive_metadata(self, archive_id: str) -> Optional[Dict[str, Any]]:
        """
        获取压缩包的完整历史元数据

        Args:
            archive_id: 压缩包ID

        Returns:
            Optional[Dict[str, Any]]: 完整的历史元数据，未找到返回None
        """
        try:
            # 获取最新的历史记录中的完整元数据
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT metadata FROM archive_history
                    WHERE archive_id = ? AND metadata IS NOT NULL
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (archive_id,))

                result = cursor.fetchone()
                if result and result[0]:
                    try:
                        return json.loads(result[0])
                    except:
                        logger.warning(f"解析元数据失败: {archive_id}")

                # 如果没有历史记录，构建基础元数据
                return self._build_complete_metadata(archive_id)

        except Exception as e:
            logger.error(f"获取完整元数据失败: {e}")
            return None

    def get_archive_name_history(self, archive_id: str) -> List[Dict[str, Any]]:
        """
        获取压缩包的名称变更历史（简化版本）

        Args:
            archive_id: 压缩包ID

        Returns:
            List[Dict[str, Any]]: 名称变更历史列表
        """
        complete_metadata = self.get_complete_archive_metadata(archive_id)
        if complete_metadata and 'name_history' in complete_metadata:
            return complete_metadata['name_history']
        return []

    def get_archive_statistics(self, archive_id: str) -> Optional[Dict[str, Any]]:
        """
        获取压缩包的统计信息

        Args:
            archive_id: 压缩包ID

        Returns:
            Optional[Dict[str, Any]]: 统计信息，未找到返回None
        """
        complete_metadata = self.get_complete_archive_metadata(archive_id)
        if complete_metadata and 'statistics' in complete_metadata:
            return complete_metadata['statistics']
        return None
    
    def get_archive_history(self, archive_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取压缩包的历史记录
        
        Args:
            archive_id: 压缩包ID
            limit: 返回记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT old_name, new_name, reason, metadata, timestamp
                FROM archive_history
                WHERE archive_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (archive_id, limit))
            
            results = cursor.fetchall()
            
            return [
                {
                    'old_name': row[0],
                    'new_name': row[1],
                    'reason': row[2],
                    'metadata': json.loads(row[3]) if row[3] else None,
                    'timestamp': row[4]
                }
                for row in results
            ]

    def find_history_by_new_name(self, new_name: str) -> List[Dict[str, Any]]:
        """根据历史记录中的新名称精确匹配条目"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                    SELECT id, archive_id, old_name, new_name, reason, metadata, timestamp
                    FROM archive_history
                    WHERE new_name = ?
                    ORDER BY timestamp DESC
                ''',
                (new_name,),
            )

            results = []
            for row in cursor.fetchall():
                metadata_obj: Optional[Dict[str, Any]] = None
                metadata_raw = row[5]
                if metadata_raw:
                    try:
                        metadata_obj = json.loads(metadata_raw)
                    except Exception as exc:  # pragma: no cover - 记录并继续
                        logger.warning(f"解析历史元数据失败 (history_id={row[0]}): {exc}")

                results.append(
                    {
                        'history_id': row[0],
                        'archive_id': row[1],
                        'old_name': row[2],
                        'new_name': row[3],
                        'reason': row[4],
                        'metadata': metadata_obj,
                        'timestamp': row[6],
                    }
                )

            return results
    
    def get_archive_info(self, archive_id: str) -> Optional[Dict[str, Any]]:
        """
        获取压缩包的完整信息
        
        Args:
            archive_id: 压缩包ID
            
        Returns:
            Optional[Dict[str, Any]]: 压缩包信息，未找到返回None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, file_path, file_hash, current_name, artist_name, created_at, updated_at
                FROM archive_info
                WHERE id = ?
            ''', (archive_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            return {
                'id': result[0],
                'file_path': result[1],
                'file_hash': result[2],
                'current_name': result[3],
                'artist_name': result[4],
                'created_at': result[5],
                'updated_at': result[6]
            }
    
    def update_file_path(self, archive_id: str, new_path: str) -> bool:
        """
        更新文件路径（用于文件移动后）
        
        Args:
            archive_id: 压缩包ID
            new_path: 新的文件路径
            
        Returns:
            bool: 是否更新成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE archive_info 
                    SET file_path = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (new_path, archive_id))
                conn.commit()
                
            logger.debug(f"更新文件路径: {archive_id} -> {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"更新文件路径失败: {e}")
            return False
