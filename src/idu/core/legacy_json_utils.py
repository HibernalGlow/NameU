import os
import json
import time
from loguru import logger

def load_existing_uuids_from_json(json_record_path: str) -> set:
    """从JSON记录中加载现有UUID（仅兼容老方案）"""
    logger.info("[#current_stats]🔍 开始加载现有UUID... (legacy json)")
    start_time = time.time()
    if not os.path.exists(json_record_path):
        return set()
    try:
        with open(json_record_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
        uuids = set(records.get("record", {}).keys())
        elapsed = time.time() - start_time
        logger.info(f"[#current_stats]✅ 加载完成！共加载 {len(uuids)} 个UUID，耗时 {elapsed:.2f} 秒")
        return uuids
    except Exception as e:
        logger.error(f"[legacy]加载UUID记录失败: {e}")
        return set() 