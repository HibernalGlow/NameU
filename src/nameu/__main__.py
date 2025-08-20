import os
import sys
import argparse
import pyperclip
from pathlib import Path
import subprocess
from colorama import init, Fore, Style

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

def main():
    """主函数 - 启动 vokein 任务选择器"""
    try:
        script_dir = Path(__file__).parent
        result = subprocess.run(
               "lata",
                cwd=script_dir
            )
            
        return result.returncode

    except Exception as e:
        print(f"[red]启动失败: {e}[/red]")
        return 1

if __name__ == "__main__":
    # 设置日志
    parser = argparse.ArgumentParser(description='处理文件名重命名')
    parser.add_argument('-c', '--clipboard', action='store_true', help='从剪贴板读取路径')
    parser.add_argument('-m', '--mode', choices=['multi', 'single'], help='处理模式：multi(多人模式)或single(单人模式)')
    parser.add_argument('--path', help='要处理的路径')
    parser.add_argument('-t', '--threads', type=int, default=16, help='并行线程数 (默认1 串行)')
    parser.add_argument('--no-artist', action='store_true', help='无画师模式 - 不添加画师名后缀')
    parser.add_argument('--keep-timestamp', action='store_true', help='保持文件的修改时间')
    parser.add_argument('--convert-sensitive', action='store_true', default=True, help='将敏感词转换为拼音')
    parser.add_argument('--no-convert-sensitive', dest='convert_sensitive', action='store_false', help='不转换敏感词',default=False)
    parser.add_argument('--rename-only', '--no-id', action='store_true', help='仅执行重命名，不生成/写入ID，不写入压缩包注释，不进行数据库记录 (与ID跟踪相关的所有操作禁用)')
    args = parser.parse_args()

    if len(sys.argv) == 1:  # 如果没有命令行参数，启动TUI界面
        main()
        sys.exit(0)

    # 处理路径参数
    if args.clipboard:
        try:
            path = pyperclip.paste().strip().strip('"')
            if not os.path.exists(path):
                print(f"{Fore.RED}剪贴板中的路径无效: {path}{Style.RESET_ALL}")
                exit(1)
            print(f"{Fore.GREEN}已从剪贴板读取路径: {path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}从剪贴板读取路径失败: {e}{Style.RESET_ALL}")
            exit(1)
    else:
        path = args.path or r"E:\1EHV"
        print(f"{Fore.GREEN}使用路径: {path}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}当前模式: {'多人模式' if args.mode == 'multi' else '单人模式'}{Style.RESET_ALL}")
      # 根据命令行参数设置全局变量
    add_artist_name_enabled = not args.no_artist
    # convert_sensitive_enabled = args.convert_sensitive
    convert_sensitive_enabled = False
    # 显示当前功能设置状态
    print(f"{Fore.CYAN}功能设置:{Style.RESET_ALL}")
    print(f"- 添加画师名: {'禁用' if args.no_artist else '启用'}")
    print(f"- 敏感词转拼音: {'启用' if convert_sensitive_enabled else '禁用'}")
    
    # 根据模式确定基础路径和处理方式
    # 是否启用ID跟踪（生成注释/数据库记录等）
    track_ids = not args.rename_only

    if args.mode == 'multi':
        base_path = path
        if args.keep_timestamp:
            older_timestamps = record_folder_timestamps(base_path)
        process_folders(base_path, add_artist_name_enabled, convert_sensitive_enabled, threads=args.threads, track_ids=track_ids)
        if args.keep_timestamp:
            restore_folder_timestamps(older_timestamps)
    else:  # single mode
        if not os.path.isdir(path):
            print(f"{Fore.RED}无效的路径: {path}{Style.RESET_ALL}")
            sys.exit(1)

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
        total_files = sum(len([f for f in files if f.lower().endswith(ARCHIVE_EXTENSIONS)]) for _, _, files in os.walk(artist_path))
        print(f"\n{Fore.GREEN}处理完成:{Style.RESET_ALL}")
        print(f"- 扫描了 {total_files} 个压缩文件")
        if modified_files_count > 0:
            print(f"- 重命名了 {modified_files_count} 个文件")
        else:
            print(f"- ✨ 所有文件名都符合规范，没有文件需要重命名")
