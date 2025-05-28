from rich.prompt import Prompt
from rich.console import Console
import pyperclip
import os

def get_path():
    console = Console()
    path = Prompt.ask("请输入目标路径（留空则自动从剪贴板获取）")
    if not path:
        try:
            path = pyperclip.paste()
            console.print(f"[green]已从剪贴板获取路径：{path}")
        except Exception as e:
            console.print(f"[red]剪贴板读取失败: {e}")
            return None
    path = path.strip('"')
    if not os.path.exists(path):
        console.print(f"[red]路径无效: {path}")
        return None
    return path 