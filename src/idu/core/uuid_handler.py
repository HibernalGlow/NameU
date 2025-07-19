from nanoid import generate
from ..sql.db_manager import DBManager
from loguru import logger
from .legacy_json_utils import load_existing_uuids_from_json
import os

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

    @staticmethod
    def ensure_db_has_uuids(db_path: str, legacy_json_path: str):
        db = DBManager(db_path)
        uuids = db.get_all_uuids()
        if not uuids and os.path.exists(legacy_json_path):
            legacy_uuids = load_existing_uuids_from_json(legacy_json_path)
            for uuid in legacy_uuids:
                db.insert_or_replace(uuid, "{}", "", "", "", "", None)
            logger.info(f"[兼容] 已从老json导入 {len(legacy_uuids)} 个UUID到数据库")
        db.close()
