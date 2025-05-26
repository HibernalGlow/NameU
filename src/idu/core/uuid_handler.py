import os
import json
import time
import logging
from nanoid import generate
from typing import Set

from loguru import logger


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
    def load_existing_uuids() -> Set[str]:
        """从JSON记录中加载现有UUID"""
        logger.info("[#current_stats]🔍 开始加载现有UUID...")
        start_time = time.time()
        
        json_record_path = r'E:\1BACKUP\ehv\uuid\uuid_records.json'
        if not os.path.exists(json_record_path):
            return set()
            
        try:
            with open(json_record_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
            # 从record键获取数据
            uuids = set(records.get("record", {}).keys())
            
            elapsed = time.time() - start_time
            logger.info(f"[#current_stats]✅ 加载完成！共加载 {len(uuids)} 个UUID，耗时 {elapsed:.2f} 秒")
            return uuids
            
        except Exception as e:
            logger.error(f"[#process]加载UUID记录失败: {e}")
            return set()
