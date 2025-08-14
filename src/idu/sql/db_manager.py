import sqlite3
from typing import Optional, Dict, Any
from loguru import logger

class DBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        # 检查是否已有bak字段
        cursor.execute("PRAGMA table_info(artworks)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'bak' not in columns:
            # 如果表已存在但无bak字段，自动添加
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS artworks (
                    uuid TEXT PRIMARY KEY,
                    json_data TEXT NOT NULL,
                    file_name TEXT,
                    artist TEXT,
                    relative_path TEXT,
                    created_time TEXT
                )
            ''')
            try:
                cursor.execute('ALTER TABLE artworks ADD COLUMN bak TEXT')
            except Exception:
                pass
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS artworks (
                    uuid TEXT PRIMARY KEY,
                    json_data TEXT NOT NULL,
                    file_name TEXT,
                    artist TEXT,
                    relative_path TEXT,
                    created_time TEXT,
                    bak TEXT
                )
            ''')
        # archive_name索引（file_name即archive_name）
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_artworks_file_name ON artworks(file_name)')
        except Exception:
            pass
        self.conn.commit()

    def insert_or_replace(self, uuid: str, json_data: str, file_name: str, artist: str, relative_path: str, created_time: str, bak: str = None):
        cursor = self.conn.cursor()
        if bak is not None:
            cursor.execute('''
                INSERT OR REPLACE INTO artworks (uuid, json_data, file_name, artist, relative_path, created_time, bak)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (uuid, json_data, file_name, artist, relative_path, created_time, bak))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO artworks (uuid, json_data, file_name, artist, relative_path, created_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (uuid, json_data, file_name, artist, relative_path, created_time))
        self.conn.commit()
        logger.info(f"[DB] 插入/更新: uuid={uuid}, file_name={file_name}, artist={artist}, relative_path={relative_path}, created_time={created_time}, bak={'有' if bak else '无'}")

    def get_by_uuid(self, uuid: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM artworks WHERE uuid = ?', (uuid,))
        row = cursor.fetchone()
        if row:
            logger.info(f"[DB] 查询: uuid={uuid} 命中")
            return {
                'uuid': row[0],
                'json_data': row[1],
                'file_name': row[2],
                'artist': row[3],
                'relative_path': row[4],
                'created_time': row[5],
            }
        logger.info(f"[DB] 查询: uuid={uuid} 未命中")
        return None

    def delete_by_uuid(self, uuid: str):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM artworks WHERE uuid = ?', (uuid,))
        self.conn.commit()

    def update_json_data(self, uuid: str, json_data: str):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE artworks SET json_data = ? WHERE uuid = ?', (json_data, uuid))
        self.conn.commit()

    def get_all_uuids(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT uuid FROM artworks')
        uuids = [row[0] for row in cursor.fetchall()]
        logger.info(f"[DB] 查询所有uuid, 共{len(uuids)}条")
        return uuids

    def get_by_archive_name(self, archive_name: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM artworks WHERE file_name = ?', (archive_name,))
        row = cursor.fetchone()
        if row:
            logger.info(f"[DB] 查询: archive_name={archive_name} 命中")
            return {
                'uuid': row[0],
                'json_data': row[1],
                'file_name': row[2],
                'artist': row[3],
                'relative_path': row[4],
                'created_time': row[5],
            }
        logger.info(f"[DB] 查询: archive_name={archive_name} 未命中")
        return None

    def close(self):
        self.conn.close() 