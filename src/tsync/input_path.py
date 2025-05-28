from rich.prompt import Prompt
from rich.console import Console
import pyperclip
import os
from loguru import logger

def get_path():
    console = Console()
    path = Prompt.ask("请输入目标路径（留空则自动从剪贴板获取）")
    if not path:
        try:
            path = pyperclip.paste()
            logger.info(f"从剪贴板获取路径：{path}")
            console.print(f"[green]已从剪贴板获取路径：{path}")
        except Exception as e:
            logger.error(f"剪贴板读取失败: {e}")
            console.print(f"[red]剪贴板读取失败: {e}")
            return None
    path = path.strip('"')
    if not os.path.exists(path):
        logger.warning(f"路径无效: {path}")
        console.print(f"[red]路径无效: {path}")
        return None
    logger.info(f"使用路径: {path}")
    return path 