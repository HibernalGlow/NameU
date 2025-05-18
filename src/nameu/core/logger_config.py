import logging
from colorama import Fore, Style
from difflib import Differ
import os

class ColoredFormatter(logging.Formatter):
    """自定义的彩色日志格式化器"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_msg = None
        self._msg_count = {}
        
    def format(self, record):
        # 如果是重命名消息，检查是否重复
        if "重命名" in record.msg:
            # 如果消息完全相同，不重复显示
            if record.msg == self._last_msg:
                return ""
            self._last_msg = record.msg
            
            # 提取原始路径和新路径
            old_path, new_path = record.msg.split(" -> ")
            old_path = old_path.replace("重命名: ", "")
            
            # 分离路径和文件名
            old_dir, old_name = os.path.split(old_path)
            new_dir, new_name = os.path.split(new_path)
            
            # 如果路径相同，只显示文件名的差异
            if old_dir == new_dir:
                record.msg = highlight_diff(old_name, new_name)
            else:
                # 如果路径不同，分别显示旧路径和新路径
                record.msg = f"🔄 {Fore.RED}\033[9m{old_path}\033[29m{Style.RESET_ALL} -> {Fore.GREEN}\033[1m{new_path}\033[22m{Style.RESET_ALL}"
        elif "出错" in record.msg.lower() or "error" in record.msg.lower():
            # 错误信息处理
            if "codec can't encode" in record.msg or "codec can't decode" in record.msg:
                # 编码错误，简化显示
                filename = record.msg.split("character", 1)[0].split("encode", 1)[0].strip()
                record.msg = f"❌ {Fore.RED}编码错误{Style.RESET_ALL}: {filename}"
            elif "path is on mount" in record.msg:
                # 路径错误，简化显示
                folder = record.msg.split("处理文件夹", 1)[1].split("出错", 1)[0].strip()
                record.msg = f"⚠️ {Fore.YELLOW}跨盘符{Style.RESET_ALL}: {folder}"
            else:
                # 其他错误
                record.msg = f"❌ {Fore.RED}{record.msg}{Style.RESET_ALL}"
        else:
            # 其他类型的日志
            if record.levelno == logging.INFO:
                color = Fore.GREEN
                emoji = "✅ "
            elif record.levelno == logging.WARNING:
                color = Fore.YELLOW
                emoji = "⚠️ "
            elif record.levelno == logging.ERROR:
                color = Fore.RED
                emoji = "❌ "
            else:
                color = Fore.WHITE
                emoji = "ℹ️ "
            record.msg = f"{emoji}{color}{record.msg}{Style.RESET_ALL}"
            
        return super().format(record)

def highlight_diff(old_str: str, new_str: str) -> str:
    """使用 difflib 高亮显示字符串差异"""
    d = Differ()
    diff = list(d.compare(old_str, new_str))
    
    colored = []
    for elem in diff:
        if elem.startswith('-'):
            # 删除部分：红色 + 删除线
            colored.append(f"{Fore.RED}\033[9m{elem[2:]}\033[29m{Style.RESET_ALL}")
        elif elem.startswith('+'):
            # 新增部分：绿色 + 加粗
            colored.append(f"{Fore.GREEN}\033[1m{elem[2:]}\033[22m{Style.RESET_ALL}")
        elif elem.startswith(' '):
            # 未修改部分：原样显示
            colored.append(elem[2:])
    return '🔄 ' + ''.join(colored)

def setup_logger():
    """配置日志处理器"""
    logging.basicConfig(level=logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter('%(message)s'))
    logging.getLogger('').handlers = [console_handler]
