import re
from dateutil import parser
from datetime import datetime
from loguru import logger

def extract_timestamp_from_name(name):
    logger.debug(f"开始从文件夹名称提取时间戳: {name}")
    # 常见时间格式正则
    patterns = [
        r"(20\d{2}|19\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12][0-9]|3[01])", # yyyy-mm-dd
        r"(20\d{2}|19\d{2})[-_.]?(0[1-9]|1[0-2])", # yyyy-mm
        r"(\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12][0-9]|3[01])", # yy-mm-dd
        r"(\d{2})[-_.]?(0[1-9]|1[0-2])", # yy-mm
    ]
    for pattern_index, pat in enumerate(patterns):
        match = re.search(pat, name)
        if match:
            matched_text = match.group()
            logger.debug(f"匹配到模式 {pattern_index+1}: {matched_text}")
            try:
                dt = parser.parse(matched_text)
                # 合理性校验
                if 2000 <= dt.year <= 2025 or 0 <= dt.year <= 25:
                    if 1 <= dt.month <= 12:
                        if not hasattr(dt, 'day') or 1 <= dt.day <= 31:
                            logger.info(f"从 '{name}' 成功提取时间戳: {dt}")
                            return dt
                        else:
                            logger.debug(f"日期超出范围: {dt.day}")
                    else:
                        logger.debug(f"月份超出范围: {dt.month}")
                else:
                    logger.debug(f"年份超出范围: {dt.year}")
            except Exception as e:
                logger.debug(f"解析时间失败: {matched_text}, 错误: {e}")
                continue
    
    logger.debug(f"未能从 '{name}' 提取有效时间戳")
    return None 