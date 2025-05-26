import os
import json
import time
import logging
from nanoid import generate
from typing import Set

from loguru import logger
from idu.sql.db_manager import DBManager


class UuidHandler:
    """UUID处理类"""
    
    @staticmethod
    def generate_uuid(existing_uuids: set) -> str:
        """生成一个唯一的16位UUID"""
        while True:
            new_uuid = generate(size=16)
            if new_uuid not in existing_uuids:
                return new_uuid
    
    @staticmethod
    def load_existing_uuids(db_path: str) -> set:
        """直接从数据库artworks表加载现有UUID"""
        db = DBManager(db_path)
        uuid_set = set(db.get_all_uuids())
        db.close()
        return uuid_set
