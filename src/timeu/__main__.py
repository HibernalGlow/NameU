import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import orjson
from loguru import logger
from tqdm import tqdm

from nameset.id_handler import ArchiveIDHandler

SUPPORTED_ARCHIVE_EXTENSIONS = (".zip", ".rar", ".7z")


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

logger, config_info = setup_logger(app_name="timeu", console_output=True)


def _extract_archive_id(file_path: str) -> Optional[str]:
    """尝试读取压缩包注释并提取归档ID。"""

    if not file_path.lower().endswith(SUPPORTED_ARCHIVE_EXTENSIONS):
        return None

    comment = ArchiveIDHandler.get_archive_comment(file_path)
    if not comment:
        return None

    return ArchiveIDHandler.extract_id_from_comment(comment)

class TimestampManager:
    def __init__(self, backup_dir='timestamp_backups'):
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 将备份目录设置为脚本目录下的子目录
        self.backup_dir = os.path.join(script_dir, backup_dir)
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def save_timestamps(self, directory, version_name=None):
        if version_name is None:
            version_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        backup_file = os.path.join(self.backup_dir, f"timestamps_{version_name}.json")
        timestamps = {}
        
        # 确保读取最新的注释信息
        ArchiveIDHandler.clear_comment_cache()

        # 单次遍历处理所有文件和目录
        processed_count = 0
        with tqdm(desc="保存时间戳") as pbar:
            for root, dirs, files in os.walk(directory):
                # 处理目录
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        stats = os.stat(dir_path)
                        timestamps[dir_path] = {
                            'access_time': stats.st_atime,
                            'mod_time': stats.st_mtime,
                        }
                    except OSError as e:
                        print(f"警告: 无法访问目录 {dir_path}: {e}")
                    processed_count += 1
                
                # 处理文件
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        stats = os.stat(file_path)
                        record = {
                            'access_time': stats.st_atime,
                            'mod_time': stats.st_mtime,
                        }

                        archive_id = _extract_archive_id(file_path)
                        if archive_id:
                            record['archive_id'] = archive_id

                        timestamps[file_path] = record
                    except OSError as e:
                        print(f"警告: 无法访问文件 {file_path}: {e}")
                    processed_count += 1
                
                # 批量更新进度条
                pbar.update(len(dirs) + len(files))
                pbar.set_description(f"保存时间戳 ({processed_count} 个项目)")
        
        with open(backup_file, 'wb') as f:
            f.write(orjson.dumps(timestamps))
        print(f"时间戳已保存到 {backup_file}")

    def list_backups(self):
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.startswith("timestamps_") and file.endswith(".json"):
                version = file[11:-5]
                backups.append(version)
        return backups

    def restore_timestamps(self, version_name=None):
        if version_name is None:
            backups = self.list_backups()
            if not backups:
                print("没有找到任何备份")
                return
            print("\n可用的备份版本：")
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup}")
            try:
                choice = int(input("\n请选择要恢复的版本编号: "))
                if 1 <= choice <= len(backups):
                    version_name = backups[choice-1]
                else:
                    print("无效的选择")
                    return
            except ValueError:
                print("无效的输入")
                return

        backup_file = os.path.join(self.backup_dir, f"timestamps_{version_name}.json")
        if not os.path.exists(backup_file):
            print(f"备份文件 {backup_file} 不存在")
            return

        with open(backup_file, 'rb') as f:
            timestamps = orjson.loads(f.read())
        
        with tqdm(total=len(timestamps), desc="恢复时间戳") as pbar:
            for path, times in timestamps.items():
                if os.path.exists(path):
                    os.utime(path, (times['access_time'], times['mod_time']))
                pbar.update(1)
        print("时间戳已恢复")

def main():
    manager = TimestampManager()
    while True:
        print("\n1. 保存时间戳")
        print("2. 恢复时间戳")
        print("3. 查看所有备份")
        print("4. 退出")
        
        choice = input("请选择操作: ")
        
        if choice == "1":
            directory = input("请输入要保存时间戳的目录路径: ")
            if not os.path.exists(directory):
                print("目录不存在")
                continue
            version_name = input("请输入版本名称（直接回车使用时间戳作为版本名）: ").strip()
            version_name = version_name if version_name else None
            manager.save_timestamps(directory, version_name)
        elif choice == "2":
            manager.restore_timestamps()
        elif choice == "3":
            backups = manager.list_backups()
            if not backups:
                print("没有找到任何备份")
            else:
                print("\n可用的备份版本：")
                for i, backup in enumerate(backups, 1):
                    print(f"{i}. {backup}")
        elif choice == "4":
            break
        else:
            print("无效的选择")

if __name__ == "__main__":
    main()