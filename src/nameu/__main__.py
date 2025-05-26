import os
import sys
import argparse
import pyperclip
from colorama import init, Fore, Style

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入自定义模块
from textual_preset import create_config_app
from nameu.core.logger_config import setup_logger
from nameu.core.constants import ARCHIVE_EXTENSIONS
from nameu.core.file_processor import (
    process_artist_folder, process_folders, record_folder_timestamps,
    restore_folder_timestamps, get_artist_name
)
from nameu.type.filter_manager import FilterManager

# 初始化 colorama
init()

# 全局配置变量
add_artist_name_enabled = True
logger, config_info = setup_logger(app_name="nameu", console_output=True)

def tui():
    """主函数"""
    # 定义复选框选项
    checkbox_options = [
        ("无画师模式 - 不添加画师名后缀", "no_artist", "--no-artist"),
        ("保持时间戳 - 保持文件的修改时间", "keep_timestamp", "--keep-timestamp", True),
        ("多画师模式 - 处理整个目录", "multi_mode", "--mode multi"),
        ("单画师模式 - 只处理单个画师的文件夹", "single_mode", "--mode single"),
        ("从剪贴板读取路径", "clipboard", "-c", True),  # 默认开启
        ("敏感词转拼音 - 将文件名中的敏感词转换为拼音", "convert_sensitive", "--convert-sensitive", False),  # 默认开启
    ]

    # 定义输入框选项
    input_options = [
        ("路径", "path", "--path", "", "输入要处理的路径，留空使用默认路径"),
    ]    # 预设配置
    preset_configs = {
        "标准多画师": {
            "description": "标准多画师模式，会添加画师名后缀",
            "checkbox_options": ["keep_timestamp", "multi_mode", "clipboard"],
            "input_values": {"path": ""}
        },
        "标准单画师": {
            "description": "标准单画师模式，会添加画师名后缀", 
            "checkbox_options": ["keep_timestamp", "single_mode", "clipboard"],
            "input_values": {"path": ""}
        },
        "无画师模式": {
            "description": "不添加画师名后缀的重命名模式",
            "checkbox_options": ["no_artist", "keep_timestamp", "clipboard"],
            "input_values": {"path": ""}
        },
        "无敏感词转换": {
            "description": "不将敏感词转换为拼音的模式",
            "checkbox_options": ["keep_timestamp", "multi_mode", "clipboard"],
            "input_values": {"path": ""}
        },
        "只处理视频": {
            "description": "只处理视频文件，应用视频专属命名规则",
            "checkbox_options": ["keep_timestamp", "multi_mode", "clipboard"],
            "input_values": {"path": ""},
            "filter_options": {"--type": "video"}
        }
    }

    # 创建并运行配置界面
    app = create_config_app(
        program=__file__,
        checkbox_options=checkbox_options,
        input_options=input_options,
        title="自动唯一文件名工具",
        preset_configs=preset_configs
    )
    app.run()
def main():
    # 设置日志
    parser = argparse.ArgumentParser(description='处理文件名重命名')
    parser.add_argument('-c', '--clipboard', action='store_true', help='从剪贴板读取路径')
    parser.add_argument('-m', '--mode', choices=['multi', 'single'], help='处理模式：multi(多人模式)或single(单人模式)')
    parser.add_argument('--path', help='要处理的路径')
    parser.add_argument('--no-artist', action='store_true', help='无画师模式 - 不添加画师名后缀')
    parser.add_argument('--keep-timestamp', action='store_true', help='保持文件的修改时间')
    parser.add_argument('--convert-sensitive', action='store_true', default=True, help='将敏感词转换为拼音')
    parser.add_argument('--no-convert-sensitive', dest='convert_sensitive', action='store_false', help='不转换敏感词',default=False)
    # 新增过滤参数
    parser.add_argument('-i', '--include', nargs='*', help='只处理指定格式（如 jpg png 或 folder）')
    parser.add_argument('-e', '--exclude', nargs='*', help='排除指定格式（如 gif 或 folder）')
    parser.add_argument('-t', '--type', help='指定文件类型类别（如 image, video, text, folder）')
    args = parser.parse_args()

    if len(sys.argv) == 1:  # 如果没有命令行参数，启动TUI界面
        tui()
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
    
    # 组装过滤参数
    format_filters = {
        '--include': args.include or [],
        '--exclude': args.exclude or [],
        '--type': args.type,
    }
    filter_manager = FilterManager(format_filters)
    
    # 根据模式确定基础路径和处理方式
    if args.mode == 'multi':
        base_path = path
        if args.keep_timestamp:
            older_timestamps = record_folder_timestamps(base_path)
        process_folders(base_path, add_artist_name_enabled, convert_sensitive_enabled, filter_manager=filter_manager)
        if args.keep_timestamp:
            restore_folder_timestamps(older_timestamps)
    else:  # single mode
        if not os.path.isdir(path):
            print(f"{Fore.RED}无效的路径: {path}{Style.RESET_ALL}")
            sys.exit(1)
            
        # 在单人模式下，path是画师文件夹的路径
        artist_path = path
        base_path = os.path.dirname(artist_path)  # 获取父目录作为base_path
        artist_name = get_artist_name(base_path, artist_path)
        
        print(f"{Fore.CYAN}正在处理画师文件夹: {os.path.basename(artist_path)}{Style.RESET_ALL}")
        
        if args.keep_timestamp:
            older_timestamps = record_folder_timestamps(artist_path)
            
        modified_files_count = process_artist_folder(artist_path, artist_name, add_artist_name_enabled, convert_sensitive_enabled, filter_manager=filter_manager)
        
        if args.keep_timestamp:
            restore_folder_timestamps(older_timestamps)
        
        # 统计该文件夹中的压缩文件总数
        total_files = sum(len([f for f in files if f.lower().endswith(ARCHIVE_EXTENSIONS)])
                         for _, _, files in os.walk(artist_path))
        
        print(f"\n{Fore.GREEN}处理完成:{Style.RESET_ALL}")
        print(f"- 扫描了 {total_files} 个压缩文件")
        if modified_files_count > 0:
            print(f"- 重命名了 {modified_files_count} 个文件")
        else:
            print(f"- ✨ 所有文件名都符合规范，没有文件需要重命名")
if __name__ == "__main__":
    main()