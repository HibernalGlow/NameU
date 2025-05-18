"""
基于loguru的日志配置模块
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from difflib import Differ
from loguru import logger

# 定义全局变量，用于跟踪上一条重命名消息
_last_rename_message = None

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
        project_root = Path(__file__).parent.parent.parent.resolve()
    
    # 清除默认处理器
    logger.remove()
    
    # 自定义日志格式处理函数
    def formatter(record):
        # 获取消息内容
        message = record["message"]
        # 根据消息内容做特殊处理
        if "重命名:" in message:
            return process_rename_message(message)
        elif "出错" in message.lower() or "error" in message.lower():
            return process_error_message(message)
        elif record["level"].name == "INFO":
            return f"<green>✅ {message}</green>"
        elif record["level"].name == "WARNING":
            return f"<yellow>⚠️ {message}</yellow>"
        elif record["level"].name == "ERROR":
            return f"<red>❌ {message}</red>"
        else:
            return f"<white>ℹ️ {message}</white>"
      # 有条件地添加控制台处理器
    if console_output:
        logger.add(
            sys.stdout,
            level="INFO",
            format=lambda record: formatter(record)
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
    
    # 添加文件处理器 - 不使用自定义格式，保持原始消息
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


def process_rename_message(message):
    """处理重命名消息的格式化
    
    Args:
        message: 包含重命名信息的消息
        
    Returns:
        str: 格式化后的消息
    """
    global _last_rename_message
    
    # 如果消息完全相同，跳过显示
    if message == _last_rename_message:
        return ""
    
    _last_rename_message = message
    
    # 提取原始路径和新路径
    try:
        old_path, new_path = message.split(" -> ")
        old_path = old_path.replace("重命名: ", "")
        
        # 分离路径和文件名
        old_dir, old_name = os.path.split(old_path)
        new_dir, new_name = os.path.split(new_path)
        
        # 如果路径相同，只显示文件名的差异
        if old_dir == new_dir:
            return highlight_diff(old_name, new_name)
        else:
            # 如果路径不同，分别显示旧路径和新路径
            return f"🔄 <s><red>{old_path}</red></s> -> <b><green>{new_path}</green></b>"
    except Exception:
        # 如果解析失败，返回原始消息
        return f"<cyan>🔄 {message}</cyan>"


def process_error_message(message):
    """处理错误消息的格式化
    
    Args:
        message: 包含错误信息的消息
        
    Returns:
        str: 格式化后的消息
    """
    if "codec can't encode" in message or "codec can't decode" in message:
        # 编码错误，简化显示
        try:
            filename = message.split("character", 1)[0].split("encode", 1)[0].strip()
            return f"<red>❌ 编码错误: {filename}</red>"
        except Exception:
            return f"<red>❌ {message}</red>"
    elif "path is on mount" in message:
        # 路径错误，简化显示
        try:
            folder = message.split("处理文件夹", 1)[1].split("出错", 1)[0].strip()
            return f"<yellow>⚠️ 跨盘符: {folder}</yellow>"
        except Exception:
            return f"<yellow>⚠️ {message}</yellow>"
    else:
        # 其他错误
        return f"<red>❌ {message}</red>"


def highlight_diff(old_str, new_str):
    """使用 difflib 高亮显示字符串差异
    
    Args:
        old_str: 原始字符串
        new_str: 新字符串
        
    Returns:
        str: 包含高亮差异的Markdown格式字符串
    """
    d = Differ()
    diff = list(d.compare(old_str, new_str))
    
    colored = []
    for elem in diff:
        if elem.startswith('-'):
            # 删除部分：红色 + 删除线
            colored.append(f"<s><red>{elem[2:]}</red></s>")
        elif elem.startswith('+'):
            # 新增部分：绿色 + 加粗
            colored.append(f"<b><green>{elem[2:]}</green></b>")
        elif elem.startswith(' '):
            # 未修改部分：原样显示
            colored.append(elem[2:])
    
    return '🔄 ' + ''.join(colored)


if __name__ == "__main__":
    # 测试日志系统
    setup_logger("test")
    logger.info("普通信息")
    logger.warning("警告信息")
    logger.error("错误信息")
    logger.info("重命名: /path/to/old/file.txt -> /path/to/new/file.txt")
    logger.info("重命名: /same/path/oldname.txt -> /same/path/newname.txt")

