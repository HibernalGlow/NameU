import os
import sys
import argparse
import pyperclip
from colorama import init, Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入自定义模块
from nameu.core.logger_config import setup_logger
from nameu.core.constants import ARCHIVE_EXTENSIONS
from nameu.core.file_processor import (
    process_artist_folder, process_folders, record_folder_timestamps,
    restore_folder_timestamps, get_artist_name
)

# 初始化 colorama
init()

# 全局配置变量
add_artist_name_enabled = True
logger, config_info = setup_logger(app_name="nameu", console_output=True)
console = Console()


def _resolve_clipboard_path() -> str:
    """Read and validate a filesystem path from the clipboard."""
    raw_value = pyperclip.paste()
    path = raw_value.strip().strip('"')
    if not path:
        raise ValueError("剪贴板为空")

    if os.path.exists(path):
        return path

    preview = raw_value.strip().splitlines()[0][:120]
    raise ValueError(
        f"剪贴板中的内容不是有效路径: {preview}\n"
        "请先在资源管理器中复制目标文件夹路径，或改用 --path 显式传入路径。"
    )

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="处理文件名重命名")
    parser.add_argument("-c", "--clipboard", action="store_true", help="从剪贴板读取路径")
    parser.add_argument(
        "-m",
        "--mode",
        choices=["multi", "single"],
        help="处理模式：multi(多人模式)或single(单人模式)",
    )
    parser.add_argument("--path", help="要处理的路径")
    parser.add_argument("-t", "--threads", type=int, default=16, help="并行线程数 (默认16)")
    parser.add_argument("--no-artist", action="store_true", help="无画师模式 - 不添加画师名后缀")
    parser.add_argument("--keep-timestamp", action="store_true", help="保持文件的修改时间")
    parser.add_argument(
        "--convert-sensitive",
        action="store_true",
        default=True,
        help="将敏感词转换为拼音",
    )
    parser.add_argument(
        "--no-convert-sensitive",
        dest="convert_sensitive",
        action="store_false",
        help="不转换敏感词",
        default=False,
    )
    parser.add_argument(
        "--rename-only",
        "--no-id",
        action="store_true",
        help="仅执行重命名，不生成/写入ID，不写入压缩包注释，不进行数据库记录",
    )
    return parser


def _interactive_args() -> argparse.Namespace:
    console.print(
        Panel.fit(
            "[bold cyan]NameU[/bold cyan]\n[dim]选择模式并执行重命名[/dim]",
            title="简易引导",
            border_style="cyan",
        )
    )

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("编号", style="cyan", justify="right")
    table.add_column("任务")
    table.add_column("说明", style="dim")
    table.add_row("1", "standard_multi", "多人模式，添加画师名")
    table.add_row("2", "standard_single", "单人模式，添加画师名")
    table.add_row("3", "no_artist_mode", "多人模式，不添加画师名")
    table.add_row("4", "rename_only", "多人模式，不添加画师名且不写 ID")
    table.add_row("5", "no_sensitive_convert", "多人模式，不转换敏感词")
    console.print(table)

    choice = Prompt.ask("请选择任务", choices=["1", "2", "3", "4", "5"], default="1")

    use_clipboard = Confirm.ask("从剪贴板读取路径", default=True)
    path = None
    if not use_clipboard:
        path = Prompt.ask("输入目标路径").strip().strip('"')

    threads = IntPrompt.ask("并行线程数", default=16)
    keep_timestamp = Confirm.ask("保持文件夹时间戳", default=True)

    mode = "multi"
    no_artist = False
    rename_only = False
    convert_sensitive = False

    if choice == "2":
        mode = "single"
    elif choice == "3":
        no_artist = True
    elif choice == "4":
        no_artist = True
        rename_only = True
    elif choice == "5":
        convert_sensitive = False

    return argparse.Namespace(
        clipboard=use_clipboard,
        mode=mode,
        path=path,
        threads=threads,
        no_artist=no_artist,
        keep_timestamp=keep_timestamp,
        convert_sensitive=convert_sensitive,
        rename_only=rename_only,
    )


def _run(args: argparse.Namespace) -> int:
    if args.clipboard:
        try:
            path = _resolve_clipboard_path()
            print(f"{Fore.GREEN}已从剪贴板读取路径: {path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}从剪贴板读取路径失败: {e}{Style.RESET_ALL}")
            return 1
    else:
        path = (args.path or "").strip()
        if not path:
            print(f"{Fore.RED}未提供有效路径，请使用 --path 或启用 --clipboard{Style.RESET_ALL}")
            return 1
        print(f"{Fore.GREEN}使用路径: {path}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}当前模式: {'多人模式' if args.mode == 'multi' else '单人模式'}{Style.RESET_ALL}")
    add_artist_name_enabled = not args.no_artist
    convert_sensitive_enabled = bool(args.convert_sensitive)

    print(f"{Fore.CYAN}功能设置:{Style.RESET_ALL}")
    print(f"- 添加画师名: {'禁用' if args.no_artist else '启用'}")
    print(f"- 敏感词转拼音: {'启用' if convert_sensitive_enabled else '禁用'}")

    track_ids = not args.rename_only

    if args.mode == "multi":
        base_path = path
        if not os.path.isdir(base_path):
            print(f"{Fore.RED}无效的路径: {path}{Style.RESET_ALL}")
            return 1
        if args.keep_timestamp:
            older_timestamps = record_folder_timestamps(base_path)
        process_folders(
            base_path,
            add_artist_name_enabled,
            convert_sensitive_enabled,
            threads=args.threads,
            track_ids=track_ids,
        )
        if args.keep_timestamp:
            restore_folder_timestamps(older_timestamps)
        return 0

    if not os.path.isdir(path):
        print(f"{Fore.RED}无效的路径: {path}{Style.RESET_ALL}")
        return 1

    artist_path = path
    base_path = os.path.dirname(artist_path)
    artist_name = get_artist_name(base_path, artist_path)
    print(f"{Fore.CYAN}正在处理画师文件夹: {os.path.basename(artist_path)}{Style.RESET_ALL}")
    if args.keep_timestamp:
        older_timestamps = record_folder_timestamps(artist_path)
    modified_files_count = process_artist_folder(
        artist_path,
        artist_name,
        add_artist_name_enabled,
        convert_sensitive_enabled,
        threads=args.threads,
        track_ids=track_ids,
    )
    if args.keep_timestamp:
        restore_folder_timestamps(older_timestamps)
    total_files = sum(
        len([f for f in files if f.lower().endswith(ARCHIVE_EXTENSIONS)])
        for _, _, files in os.walk(artist_path)
    )
    print(f"\n{Fore.GREEN}处理完成:{Style.RESET_ALL}")
    print(f"- 扫描了 {total_files} 个压缩文件")
    if modified_files_count > 0:
        print(f"- 重命名了 {modified_files_count} 个文件")
    else:
        print(f"- ✨ 所有文件名都符合规范，没有文件需要重命名")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if len(sys.argv) == 1:
        args = _interactive_args()
    return _run(args)

if __name__ == "__main__":
    sys.exit(main())
