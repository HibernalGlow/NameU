import re
from dateutil import parser
from datetime import datetime

def extract_timestamp_from_name(name):
    # 常见时间格式正则
    patterns = [
        r"(20\d{2}|19\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12][0-9]|3[01])", # yyyy-mm-dd
        r"(20\d{2}|19\d{2})[-_.]?(0[1-9]|1[0-2])", # yyyy-mm
        r"(\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12][0-9]|3[01])", # yy-mm-dd
        r"(\d{2})[-_.]?(0[1-9]|1[0-2])", # yy-mm
    ]
    for pat in patterns:
        match = re.search(pat, name)
        if match:
            try:
                dt = parser.parse(match.group())
                # 合理性校验
                if 2000 <= dt.year <= 2025 or 0 <= dt.year <= 25:
                    if 1 <= dt.month <= 12:
                        if not hasattr(dt, 'day') or 1 <= dt.day <= 31:
                            return dt
            except Exception:
                continue
    return None 