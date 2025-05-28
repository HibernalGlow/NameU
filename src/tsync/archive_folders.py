import os
import shutil
from datetime import datetime
from rich.console import Console
from loguru import logger
console = Console()

# 预定义格式 - 使用标准strftime格式
FORMATS = {
    # 单层格式
    'year': '%Y',                   # 2023
    'year_month': '%Y-%m',          # 2023-05
    'year_month_day': '%Y-%m-%d',   # 2023-05-15
    'month_day': '%m-%d',           # 05-15
    'day': '%d',                    # 15
    
    # 多层格式 (使用路径分隔符)
    'nested_y_m': ['%Y', '%m'],                # 2023/05
    'nested_y_m_d': ['%Y', '%m', '%d'],        # 2023/05/15
    'nested_ym_d': ['%Y-%m', '%d'],            # 2023-05/15
    'nested_y_md': ['%Y', '%m-%d'],            # 2023/05-15
}

def archive_folder(src_folder, dt: datetime, base_dst, format_key='year_month', dry_run=False):
    """
    format_key: 预定义格式的键名
    dry_run: 预览模式，不实际移动文件
    """
    if format_key not in FORMATS:
        logger.error(f'格式参数错误，支持的格式: {", ".join(FORMATS.keys())}')
        raise ValueError(f'格式参数错误，支持的格式: {", ".join(FORMATS.keys())}')
    
    # 使用strftime格式化路径
    format_spec = FORMATS[format_key]
    
    # 处理多层级路径
    if isinstance(format_spec, list):
        # 生成每一层的路径
        path_components = [dt.strftime(fmt) for fmt in format_spec]
        # 逐层构建路径
        dst = base_dst
        for component in path_components:
            dst = os.path.join(dst, component)
    else:
        # 单层路径
        folder_date = dt.strftime(format_spec)
        dst = os.path.join(base_dst, folder_date)
    
    folder_name = os.path.basename(src_folder.rstrip(os.sep))
    dst_folder = os.path.join(dst, folder_name)
    
    if dry_run:
        logger.debug(f"预览: 将 {src_folder} 移动到 {dst_folder}")
        console.print(f"[cyan]预览: 将 {src_folder} 移动到 {dst_folder}")
        return dst_folder
    
    if not os.path.exists(dst):
        logger.debug(f"创建目录: {dst}")
        os.makedirs(dst)
    
    logger.info(f"移动文件夹: {src_folder} -> {dst_folder}")
    shutil.move(src_folder, dst_folder)
    return dst_folder
