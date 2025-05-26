import sqlite3
import os
from typing import Optional, Dict, Any
from loguru import logger

class DBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS artworks (
                uuid TEXT PRIMARY KEY,
                json_data TEXT NOT NULL,看
                
                file_name TEXT,
                artist TEXT,
                relative_path TEXT,
                created_time TEXT
            )
        ''')
        self.conn.commit()

    def insert_or_replace(self, uuid: str, json_data: str, file_name: str, artist: str, relative_path: str, created_time: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO artworks (uuid, json_data, file_name, artist, relative_path, created_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (uuid, json_data, file_name, artist, relative_path, created_time))
        self.conn.commit()
        logger.info(f"[DB] 插入/更新: uuid={uuid}, file_name={file_name}, artist={artist}, relative_path={relative_path}, created_time={created_time}")

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

    def close(self):
        self.conn.close() 