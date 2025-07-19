import os
import json
import logging
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tqdm import tqdm
import subprocess
import re
from datetime import datetime
import orjson  # 添加更快的JSON解析库
from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(app_name="app", project_root=None, console_output=True):
    """配置 Loguru 日志系统
    
    Args:
        app_name: 应用名称，用于日志目录
        project_root: 项目根目录，默认为当前文件所在目录
        console_output: 是否输出到控制台，默认为True
        
    Returns:
        tuple: (logger, config_info)
            - logger: 配置好的 logger 实例
            - config_info: 包含日志配置信息的字典
    """
    # 获取项目根目录
    if project_root is None:
        project_root = Path(__file__).parent.resolve()
    
    # 清除默认处理器
    logger.remove()
    
    # 有条件地添加控制台处理器（简洁版格式）
    if console_output:
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <blue>{elapsed}</blue> | <level>{level.icon} {level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
        )
    
    # 使用 datetime 构建日志路径
    current_time = datetime.now()
    date_str = current_time.strftime("%Y-%m-%d")
    hour_str = current_time.strftime("%H")
    minute_str = current_time.strftime("%M%S")
    
    # 构建日志目录和文件路径
    log_dir = os.path.join(project_root, "logs", app_name, date_str, hour_str)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{minute_str}.log")
    
    # 添加文件处理器
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {elapsed} | {level.icon} {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,     )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger, config_info

logger, config_info = setup_logger(app_name="restore_name", console_output=True)

# 设置日志
def read_json(json_path):
    """读取JSON文件内容，使用orjson加速解析"""
    if os.path.exists(json_path):
        try:
            with open(json_path, 'rb') as file:  # 使用二进制模式打开
                return orjson.loads(file.read())
        except Exception as e:
            logger.error(f"JSON文件解析错误 {json_path}: {str(e)}")
    return {}

def write_json(json_path, data):
    """安全地写入JSON文件，使用orjson加速序列化"""
    temp_path = f"{json_path}.tmp"
    try:
        # 使用orjson序列化
        json_bytes = orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS
        )
        
        with open(temp_path, 'wb') as file:  # 使用二进制模式写入
            file.write(json_bytes)
        
        # 原子化替换
        if os.path.exists(json_path):
            os.replace(temp_path, json_path)
        else:
            os.rename(temp_path, json_path)
        return True
    except Exception as e:
        logger.error(f"写入JSON文件失败 {json_path}: {str(e)}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False

def get_archive_name_from_json(json_data, cutoff_time=None, use_earliest=False):
    """从JSON数据中获取压缩包名称
    
    Args:
        json_data: JSON数据
        cutoff_time: 截止时间，datetime对象，只获取这个时间之前的记录
        use_earliest: 是否使用最早的记录，True为最早，False为最新
    """
    if not json_data or not isinstance(json_data, dict) or "timestamps" not in json_data:
        return None
    
    # 定义黑名单关键词集合
    blacklist_keywords = {'Z0FBQ'}
    
    # 获取所有时间戳并排序
    timestamps = list(json_data["timestamps"].keys())
    if not timestamps:
        return None
        
    # 根据选择决定遍历顺序
    timestamps.sort(reverse=not use_earliest)
    
    # 遍历时间戳找到符合条件的记录
    for timestamp in timestamps:
        record = json_data["timestamps"][timestamp]
        archive_name = record.get('archive_name', '')
        
        # 检查文件名是否包含黑名单关键词
        if any(keyword in archive_name for keyword in blacklist_keywords):
            continue
            
        # 如果设置了截止时间
        if cutoff_time:
            try:
                record_time = datetime.fromisoformat(timestamp)
                if record_time > cutoff_time:
                    continue
            except (ValueError, TypeError):
                continue
                
        return archive_name
        
    return None

def get_archive_uuid(archive_path):
    """从压缩包中获取 JSON 文件名作为 UUID"""
    try:
        cmd = ['7z', 'l', archive_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 在输出中查找 .json 文件
        for line in result.stdout.splitlines():
            if '.json' in line:
                # 提取 JSON 文件名（去掉扩展名）
                json_name = line.split()[-1]  # 获取最后一列（文件名）
                return os.path.splitext(json_name)[0]  # 去掉 .json 扩展名
    except Exception as e:
        logger.error(f"获取UUID失败 {archive_path}: {str(e)}")
    return None

def load_uuid_json_cache(uuid_directory):
    """预先加载所有UUID-JSON文件的路径映射
    
    Args:
        uuid_directory: UUID文件的根目录
        
    Returns:
        dict: {uuid: json_file_path} 映射
    """
    logger.info("开始扫描并缓存UUID-JSON文件...")
    start_time = datetime.now()
    uuid_cache = {}
    
    # 递归遍历目录查找所有JSON文件
    for root, _, files in os.walk(uuid_directory):
        for file in files:
            if file.endswith('.json'):
                uuid = os.path.splitext(file)[0]
                uuid_cache[uuid] = os.path.join(root, file)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"缓存完成，共找到 {len(uuid_cache)} 个JSON文件，耗时 {elapsed:.2f} 秒")
    return uuid_cache

def process_single_archive(archive_path, uuid_directory, stats_lock, stats, uuid_cache, cutoff_time=None, use_earliest=False):
    """处理单个压缩包的重命名"""
    try:
        current_dir = os.path.dirname(archive_path)
        current_name = os.path.basename(archive_path)
        
        # 获取压缩包对应的 UUID
        uuid = get_archive_uuid(archive_path)
        if not uuid:
            logger.warning(f"无法从压缩包获取UUID: {current_name}")
            with stats_lock:
                stats['errors'] += 1
            return
            
        # 从缓存中查找JSON文件路径
        json_path = uuid_cache.get(uuid)
        if not json_path:
            logger.warning(f"在缓存中找不到对应的JSON文件: {uuid}")
            with stats_lock:
                stats['errors'] += 1
            return
            
        json_data = read_json(json_path)
        target_name = get_archive_name_from_json(json_data, cutoff_time, use_earliest)
            
        if not target_name:
            logger.warning(f"找不到有效的文件名记录: {current_name}")
            with stats_lock:
                stats['skipped'] += 1
            return
        
        if target_name != current_name:
            new_path = os.path.join(current_dir, target_name)
            
            base_name, ext = os.path.splitext(target_name)
            counter = 1
            while os.path.exists(new_path):
                new_path = os.path.join(current_dir, f"{base_name}_{counter}{ext}")
                counter += 1
            
            os.rename(archive_path, new_path)
            logger.info(f"重命名: {current_name} -> {os.path.basename(new_path)}")
            with stats_lock:
                stats['renamed'] += 1
        else:
            with stats_lock:
                stats['skipped'] += 1
                
    except Exception as e:
        logger.error(f"处理文件时出错 {archive_path}: {str(e)}", exc_info=True)
        with stats_lock:
            stats['errors'] += 1

def rename_archives(target_directory, uuid_directory, cutoff_time=None, use_earliest=False, max_workers=8):
    """使用多线程重命名压缩包"""
    logger = logging.getLogger(__name__)
    stats = {'renamed': 0, 'skipped': 0, 'errors': 0}
    stats_lock = threading.Lock()
    
    # 预先加载所有UUID-JSON文件的路径映射
    uuid_cache = load_uuid_json_cache(uuid_directory)
    
    # 获取所有压缩包
    archive_files = []
    for root, _, files in os.walk(target_directory):
        for file in files:
            if file.endswith(('.zip', '.rar', '.7z')) and not file.endswith('.tdel'):
                archive_files.append(os.path.join(root, file))
    
    total_files = len(archive_files)
    logger.info(f"找到 {total_files} 个压缩包待处理")
    
    # 使用线程池处理文件
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        with tqdm(total=total_files) as pbar:
            futures = []
            for archive_path in archive_files:
                future = executor.submit(
                    process_single_archive,
                    archive_path,
                    uuid_directory,
                    stats_lock,
                    stats,
                    uuid_cache,  # 传递缓存到处理函数
                    cutoff_time,
                    use_earliest
                )
                future.add_done_callback(lambda p: pbar.update())
                futures.append(future)
            
            # 等待所有任务完成
            for future in futures:
                future.result()
    
    logger.info("处理完成:")
    logger.info(f"重命名: {stats['renamed']} 个文件")
    logger.info(f"跳过: {stats['skipped']} 个文件")
    logger.info(f"错误: {stats['errors']} 个文件")
def main():
    # 设置日志
    target_directory = input("请输入压缩包所在目录路径: ").strip().strip('"')
    uuid_directory = r'E:\1BACKUP\ehv\uuid'
    
    # 获取恢复模式选择
    mode_choice = input("请选择恢复模式（1: 最新文件名, 2: 最早文件名）[默认1]: ").strip()
    use_earliest = mode_choice == "2"
    logger.info(f"使用{'最早' if use_earliest else '最新'}文件名模式")
    
    # 获取截止时间
    cutoff_time_str = input("请输入截止时间（格式：YYYY-MM-DD HH:MM:SS，直接回车则不限制时间）: ").strip()
    cutoff_time = None
    if cutoff_time_str:
        try:
            cutoff_time = datetime.strptime(cutoff_time_str, '%Y-%m-%d %H:%M:%S')
            logger.info(f"设置截止时间: {cutoff_time}")
        except ValueError:
            logger.error("时间格式错误，将不使用时间限制")
    
    logger.info(f"开始处理目录: {target_directory}")
    logger.info(f"JSON文件目录: {uuid_directory}")
    
    rename_archives(target_directory, uuid_directory, cutoff_time, use_earliest)
    
if __name__ == '__main__':
    main()

    
