import os
import re
import argparse
import pyperclip
import subprocess

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
    )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger, config_info

logger, config_info = setup_logger(app_name="snu", console_output=True)



def extract_number_and_name(folder_name):
    """从文件夹名称中提取序号和名称"""
    match = re.match(r'^(\d)[\.\s-]+(.+)$', folder_name)
    if match:
        return int(match.group(1)), match.group(2)
    return None, folder_name

def should_process_folder(folder_name):
    """判断文件夹是否需要处理（是否符合数字开头格式）"""
    return bool(re.match(r'^\d[\.\s-]+', folder_name))

def get_folder_priority(name):
    """根据文件夹名称获取优先级"""
    priority_keywords = ["同人志", "商业", "单行", "CG", "画集"]
    # 转换为小写进行比较
    name_lower = name.lower()
    for i, keyword in enumerate(priority_keywords):
        if keyword.lower() in name_lower:
            return i
    return len(priority_keywords)  # 没有关键词的排在最后

def is_sequence_continuous(folders):
    """检查文件夹序号是否连续"""
    numbers = [folder[0] for folder in folders]
    return all(numbers[i] == numbers[i-1] + 1 for i in range(1, len(numbers)))

def fix_folder_sequence(base_path):
    """修复文件夹的序号顺序，只在序号不连续时按关键词排序"""
    try:
        # 获取直接子文件夹
        folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
        
        # 提取需要处理的文件夹（数字开头的）
        numbered_folders = []
        for folder in folders:
            num, name = extract_number_and_name(folder)
            if num is not None:
                numbered_folders.append((num, name, folder))
          # 如果没有需要处理的文件夹，直接返回
        if not numbered_folders:
            logger.warning(f"目录 {base_path} 中没有发现需要处理的编号文件夹")
            return
        
        # 先按原序号排序
        numbered_folders.sort(key=lambda x: x[0])
        
        # 检查序号是否连续
        if is_sequence_continuous(numbered_folders):
            logger.success(f"目录 {base_path} 中的文件夹序号已经连续，无需调整")
            return
            
        # 序号不连续时，按关键词优先级排序
        numbered_folders.sort(key=lambda x: (get_folder_priority(x[1]), x[0]))
        
        # 重新编号
        changes = []
        for i, (_, name, old_folder) in enumerate(numbered_folders, 1):
            new_folder = f"{i}. {name}"
            if new_folder != old_folder:
                old_path = os.path.join(base_path, old_folder)
                new_path = os.path.join(base_path, new_folder)
                
                try:
                    # 保存原始时间戳
                    original_stat = os.stat(old_path)
                    
                    # 重命名文件夹
                    os.rename(old_path, new_path)
                      # 恢复时间戳
                    os.utime(new_path, (original_stat.st_atime, original_stat.st_mtime))
                    
                    changes.append((old_folder, new_folder))
                    logger.info(f"{old_folder} -> {new_folder}")
                except Exception as e:
                    logger.error(f"重命名文件夹失败 {old_folder}: {str(e)}")
        
        if changes:
            logger.success(f"成功修复了 {len(changes)} 个文件夹的序号")        
    except Exception as e:
        logger.error(f"处理目录 {base_path} 时出错: {str(e)}")

def process_artist_folders(root_path):
    """处理所有画师文件夹"""
    try:
        # 先运行预处理脚本
        logger.info("运行预处理脚本 cleanf")
        subprocess.run(["cleanf"], check=True)
        
        # 获取所有画师文件夹
        artist_folders = [f for f in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, f))]
        
        for artist_folder in artist_folders:
            artist_path = os.path.join(root_path, artist_folder)
            logger.info(f"处理画师文件夹: {artist_folder}")
            fix_folder_sequence(artist_path)
            
    except Exception as e:
        logger.error(f"处理根目录 {root_path} 时出错: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='修复文件夹序号连续性')
    parser.add_argument('paths', nargs='*', help='要处理的路径列表')
    parser.add_argument('-c', '--clipboard', action='store_true', help='从剪贴板读取路径')
    args = parser.parse_args()

    paths = []
    if args.paths:  # 处理直接传入的路径
        for path in args.paths:
            if os.path.exists(path):
                paths.append(path)
            else:
                logger.error(f"路径无效: {path}")
    elif args.clipboard:
        try:
            clipboard_content = pyperclip.paste().strip()
            for line in clipboard_content.splitlines():
                path = line.strip().strip('"')
                if os.path.exists(path):
                    paths.append(path)
                else:
                    logger.error(f"剪贴板中的路径无效: {path}")
        except Exception as e:
            logger.error(f"从剪贴板读取路径失败: {e}")
    else:
        paths = [r"E:\1EHV"]

    if not paths:
        logger.error("没有有效的路径可以处理")
        exit(1)

    # 处理每个路径
    for path in paths:
        logger.info(f"处理路径: {path}")
        process_artist_folders(path)
if __name__ == "__main__":
    main()