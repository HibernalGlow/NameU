import os
import sys
import time
import logging
import argparse
import pyperclip
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# 添加父目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(parent_dir)

from textual_preset import create_config_app
from textual_logger import TextualLoggerManager
from nodes.comic.uuid.archive_processor import ArchiveProcessor
from nodes.comic.uuid.uuid_record_manager import UuidRecordManager
from nodes.comic.uuid.json_handler import JsonHandler
from nodes.comic.uuid.path_handler import PathHandler
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

logger, config_info = setup_logger(app_name="auto_uuid", console_output=True)


# 定义日志布局配置
TEXTUAL_LAYOUT = {
    "current_stats": {
        "ratio": 2,
        "title": "📊 总体进度",
        "style": "lightyellow"
    },
    "current_progress": {
        "ratio": 2,
        "title": "🔄 当前进度",
        "style": "lightcyan"
    },
    "process": {
        "ratio": 3,
        "title": "📝 处理日志",
        "style": "lightpink"
    },
    "update": {
        "ratio": 2,
        "title": "ℹ️ 更新日志",
        "style": "lightblue"
    }
}
def init_TextualLogger():
    """初始化TextualLogger"""
    TextualLoggerManager.set_layout(TEXTUAL_LAYOUT, config_info['log_file'])
    logger.info("[#update]✅ 日志系统初始化完成")

# 初始化日志配置


# 从 main.py 中融合的类
class CommandManager:
    """命令行参数管理器"""
    
    @staticmethod
    def init_parser():
        parser = argparse.ArgumentParser(description='处理文件UUID和JSON生成')
        parser.add_argument('-c', '--clipboard', action='store_true', help='从剪贴板读取路径')
        parser.add_argument('-m', '--mode', choices=['multi', 'single'], help='处理模式：multi(多人模式)或single(单人模式)')
        parser.add_argument('--no-artist', action='store_true', help='无画师模式 - 不添加画师名')
        parser.add_argument('--keep-timestamp', action='store_true', help='保持文件的修改时间')
        parser.add_argument('--path', help='要处理的路径')
        parser.add_argument('-a', '--auto-sequence', action='store_true', help='自动执行完整序列：UUID-JSON -> 自动文件名 -> UUID-JSON')
        parser.add_argument('-r', '--reorganize', action='store_true', help='重新组织 UUID 文件结构')
        parser.add_argument('-u', '--update-records', action='store_true', help='更新 UUID 记录文件')
        parser.add_argument('--convert', action='store_true', help='转换YAML到JSON结构')
        parser.add_argument('--order', choices=['path', 'mtime'], default='mtime',
                          help='处理顺序: path(按路径升序) 或 mtime(按修改时间倒序)')
        return parser

    @staticmethod
    def get_target_directory(args):
        if args.clipboard:
            try:
                target_directory = pyperclip.paste().strip().strip('"')
                if not os.path.exists(target_directory):
                    logger.error(f"[#process]剪贴板中的路径无效: {target_directory}")
                    sys.exit(1)
                logger.info(f"[#current_stats]已从剪贴板读取路径: {target_directory}")
            except Exception as e:
                logger.error(f"[#process]从剪贴板读取路径失败: {e}")
                sys.exit(1)
        else:
            target_directory = args.path or r"E:\1EHV"
            logger.info(f"[#current_stats]使用路径: {target_directory}")
        return target_directory

class TaskExecutor:
    """任务执行器"""
    
    def __init__(self, args, target_directory: str):
        self.args = args
        self.target_directory = target_directory
        self.max_workers = 16
        self.confirmed_artists = set()
        self.uuid_directory = r'E:\1BACKUP\ehv\uuid'
        self.archive_processor = ArchiveProcessor(
            self.target_directory, 
            self.uuid_directory,
            self.max_workers,
            order=args.order  # 添加排序参数
        )
        self.uuid_record_manager = UuidRecordManager(self.uuid_directory)

    def _confirm_artists(self) -> None:
        """确认画师信息"""
        print("\n正在扫描画师信息...")
        artists = set()
        
        # 扫描所有压缩文件以获取画师信息
        for root, _, files in os.walk(self.target_directory):
            for file in files:
                if file.endswith(('.zip', '.rar', '.7z')):
                    archive_path = os.path.join(root, file)
                    artist = PathHandler.get_artist_name(self.target_directory, archive_path, self.args.mode)
                    if artist:
                        artists.add(artist)
        
        # 显示画师信息并等待确认
        if self.args.mode == 'single':
            if len(artists) > 1:
                print("\n⚠️ 警告：在单人模式下检测到多个画师名称：")
                for i, artist in enumerate(sorted(artists), 1):
                    print(f"{i}. {artist}")
                print("\n请确认这是否符合预期？如果不符合，请检查目录结构。")
            elif len(artists) == 1:
                print(f"\n检测到画师: {next(iter(artists))}")
            else:
                print("\n⚠️ 警告：未检测到画师名称！")
            
            input("\n按回车键继续...")
            
        else:  # 多人模式
            print(f"\n共检测到 {len(artists)} 个画师目录：")
            for i, artist in enumerate(sorted(artists), 1):
                print(f"{i}. {artist}")
            
            input("\n按回车键继续...")
        
        self.confirmed_artists = artists

    def execute_tasks(self) -> None:
        """执行所有任务"""
        # 首先确认画师信息
        self._confirm_artists()
        
        init_TextualLogger()

        logger.info(f"[#current_stats]当前模式: {'多人模式' if self.args.mode == 'multi' else '单人模式'}")

        if self.args.convert:
            self._execute_convert_task()
            return

        if self.args.reorganize:
            self._execute_reorganize_task()

        if self.args.update_records:
            self._execute_update_records_task()

        if self.args.auto_sequence:
            self._execute_auto_sequence()
        elif not self.args.reorganize and not self.args.update_records:
            self._execute_normal_process()

    def _execute_convert_task(self) -> None:
        """执行YAML转JSON任务"""
        self.uuid_record_manager.convert_yaml_to_json_structure()
        sys.exit(0)

    def _execute_reorganize_task(self) -> None:
        """执行重组任务"""
        logger.info("[#current_stats]📝 开始重新组织 UUID 文件...")
        self.uuid_record_manager.reorganize_uuid_files()

    def _execute_update_records_task(self) -> None:
        """执行更新记录任务"""
        logger.info("[#current_stats]📝 开始更新 UUID 记录...")
        self.uuid_record_manager.update_json_records()

    def _execute_auto_sequence(self) -> None:
        """优化后的自动序列执行"""
        # 直接开始处理，不进行预热
        logger.info("[#current_stats]🔄 开始合并处理流程...")
        self.archive_processor.process_archives()
        self._run_auto_filename_script()
        
        logger.info("[#current_stats]✨ 优化后的处理流程完成！")

    def _execute_normal_process(self) -> None:
        """执行普通处理流程"""
        self.archive_processor.process_archives()

    def _run_auto_filename_script(self) -> None:
        """运行自动文件名脚本"""
        auto_filename_script = os.path.join(os.path.dirname(__file__), 'one_name.py')
        if not os.path.exists(auto_filename_script):
            logger.error(f"[#process]找不到自动文件名脚本: {auto_filename_script}")
            return

        try:
            cmd = [sys.executable, auto_filename_script]
            if self.args.clipboard:
                cmd.extend(['-c'])
            if self.args.mode:
                cmd.extend(['-m', self.args.mode])

            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='ignore',
                startupinfo=startupinfo
            )

            for line in result.stdout.splitlines():
                if line.strip():
                    logger.info(line)

            logger.info("[#current_stats]✅ 自动文件名处理完成")
        except subprocess.CalledProcessError as e:
            logger.error(f"[#process]自动文件名处理失败: {str(e)}")
            if e.output:
                logger.error(f"[#process]错误输出: {e.output}")

def run_command(args=None):
    """运行命令行模式"""
    # 初始化命令行解析器
    
    parser = CommandManager.init_parser()
    if args is None:
        args = parser.parse_args()

    # 获取目标目录
    target_directory = CommandManager.get_target_directory(args)

    # 执行任务
    executor = TaskExecutor(args, target_directory)
    executor.execute_tasks()
    
    return 0

def main_tui():
    """TUI界面模式入口"""
    # 定义复选框选项
    checkbox_options = [
        ("无画师模式 - 不添加画师名", "--no-artist", "--no-artist"),
        ("保持时间戳 - 保持文件的修改时间", "--keep-timestamp", "--keep-timestamp", True),
        ("多画师模式 - 处理整个目录", "--mode multi", "--mode multi"),
        ("单画师模式 - 只处理单个画师的文件夹", "--mode single", "--mode single"),
        ("从剪贴板读取路径", "-c", "-c", True),  # 默认开启
        ("自动序列 - 执行完整处理流程", "-a", "-a"),  # 添加序列模式选项
        ("重组UUID - 按时间重组UUID文件", "-r", "-r"),  # 添加重组选项
        ("更新记录 - 更新UUID记录文件", "-u", "-u"),  # 添加更新记录选项
        ("转换YAML - 转换现有YAML到JSON", "--convert", "--convert"),  # 添加YAML转换选项
        ("按路径排序 - 按文件路径升序处理", "--order path", "--order path"),
        ("按时间排序 - 按修改时间倒序处理", "--order mtime", "--order mtime", True),  # 默认选中
    ]

    # 定义输入框选项
    input_options = [
        ("路径", "--path", "--path", "", "输入要处理的路径，留空使用默认路径"),
    ]

    # 预设配置
    preset_configs = {
        "标准多画师": {
            "description": "标准多画师模式，会添加画师名",
            "checkbox_options": ["--keep-timestamp", "--mode multi", "-c"],
            "input_values": {"--path": ""}
        },
        "标准单画师": {
            "description": "标准单画师模式，会添加画师名", 
            "checkbox_options": ["--keep-timestamp", "--mode single", "-c"],
            "input_values": {"--path": ""}
        },
        "无画师模式": {
            "description": "不添加画师名的重命名模式",
            "checkbox_options": ["--no-artist", "--keep-timestamp", "-c"],
            "input_values": {"--path": ""}
        },
        "完整序列": {
            "description": "执行完整处理流程：UUID-JSON -> 自动文件名 -> UUID-JSON",
            "checkbox_options": ["--keep-timestamp", "-c", "-a"],
            "input_values": {"--path": ""}
        },
        "UUID更新": {
            "description": "重组UUID文件结构并更新记录",
            "checkbox_options": ["-r", "-u"],
            "input_values": {"--path": ""}
        },
        "完整维护": {
            "description": "执行完整序列并更新UUID记录",
            "checkbox_options": ["--keep-timestamp", "-c", "-a", "-r", "-u"],
            "input_values": {"--path": ""}
        },
        "YAML转换": {
            "description": "转换现有YAML文件到JSON格式",
            "checkbox_options": ["--convert"],
            "input_values": {"--path": ""}
        }
    }

    # 定义回调函数
    def on_run(params: dict):
        """TUI配置界面的回调函数"""
        # 将TUI参数转换为命令行参数格式
        cmd_args = []
        
        # 添加选中的复选框选项
        for arg, enabled in params['options'].items():
            if enabled:
                # 分解可能含有空格的选项（如 "--mode multi"）
                parts = arg.split()
                cmd_args.extend(parts)
                
        # 添加输入框的值
        for arg, value in params['inputs'].items():
            if value.strip():
                cmd_args.append(arg)
                cmd_args.append(value)
        
        # 初始化TextualLogger
        
        # 使用解析器解析参数
        parser = CommandManager.init_parser()
        args = parser.parse_args(cmd_args)
        
        # init_TextualLogger()
        # 执行命令
        run_command(args)

    # 创建并运行配置界面
    app = create_config_app(
        program=__file__,
        title="UUID-JSON 工具",
        checkbox_options=checkbox_options,
        input_options=input_options,
        preset_configs=preset_configs,
        # on_run=on_run
    )
    app.run()

def main():
    """主函数入口"""
    # 如果没有命令行参数，启动TUI界面
    if len(sys.argv) == 1:
        main_tui()
        return 0
    
    # 否则使用命令行模式
    return run_command()

if __name__ == "__main__":
    sys.exit(main())
