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
        try:
            # 获取消息内容
            message = record["message"]
            formatted_message = ""

            # 根据消息内容做特殊处理
            if "重命名:" in message:
                formatted_message = process_rename_message(message)
            elif "出错" in message.lower() or "error" in message.lower():
                formatted_message = process_error_message(message)
            elif record["level"].name == "INFO":
                formatted_message = f"<green>✅ {message}</green>"
            elif record["level"].name == "WARNING":
                formatted_message = f"<yellow>⚠️ {message}</yellow>"
            elif record["level"].name == "ERROR":
                formatted_message = f"<red>❌ {message}</red>"
            else:
                formatted_message = f"<white>ℹ️ {message}</white>"

            # 确保每条消息都以换行符结尾
            if formatted_message and not formatted_message.endswith('\n'):
                formatted_message += '\n'

            return formatted_message

        except Exception:
            # 如果格式化过程中出现任何错误，返回一个安全的字符串
            try:
                return f"<white>ℹ️ {str(message)[:100]}...</white>\n"
            except:
                return "<white>ℹ️ [日志格式化错误]</white>\n"
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
        enqueue=True,     )
    
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

    # 转义可能在文件名中出现的花括号 {} - 防止被当作格式化占位符处理
    message = message.replace("{", "{{").replace("}", "}}")

    # 提取原始路径和新路径
    try:
        parts = message.split(" -> ", 1)  # 最多分割一次，以防文件名中包含 " -> "
        if len(parts) != 2:
            return f"<cyan>🔄 {message}</cyan>"

        old_path, new_path = parts
        old_path = old_path.replace("重命名: ", "")

        # 分离路径和文件名
        old_dir, old_name = os.path.split(old_path)
        new_dir, new_name = os.path.split(new_path)

        # 如果路径相同，只显示文件名的差异
        if old_dir == new_dir:
            return highlight_diff(old_name, new_name)
        else:
            # 如果路径不同，使用更安全的格式
            return f"🔄 从 '{old_path}' 到 '{new_path}'"
    except Exception:
        # 如果解析失败，返回安全的原始消息，避免格式化问题
        return f"<cyan>🔄 重命名操作已完成</cyan>"


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
    try:
        # 转义花括号，防止格式化错误
        old_str_escaped = old_str.replace("{", "{{").replace("}", "}}")
        new_str_escaped = new_str.replace("{", "{{").replace("}", "}}")

        # 简化处理方式，不再逐字符比较
        if old_str == new_str:
            return f"🔄 {old_str_escaped}"

        # 使用更安全的方式展示变化
        return f"🔄 <s><red>{old_str_escaped}</red></s> → <b><green>{new_str_escaped}</green></b>"
    except Exception:
        # 如果出现异常，返回一个安全的字符串
        return f"🔄 从 '{old_str}' 重命名为 '{new_str}'"


if __name__ == "__main__":
    # 测试日志系统
    setup_logger("test")
    logger.info("普通信息")
    logger.warning("警告信息")
    logger.error("错误信息")
    logger.info("重命名: /path/to/old/file.txt -> /path/to/new/file.txt")
    logger.info("重命名: /same/path/oldname.txt -> /same/path/newname.txt")

