import os
import time
from datetime import datetime
from loguru import logger

def sync_folder_file_time(folder_path, dt: datetime):
    ts = time.mktime(dt.timetuple())
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.utime(file_path, (ts, ts))
            except Exception as e:
                logger.error(f"同步文件时间失败: {file_path}，原因: {e}")
