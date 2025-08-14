import os
import sys
import argparse
import pyperclip
import subprocess

from idu.core.archive_processor import ArchiveProcessor
from idu.core.uuid_record_manager import UuidRecordManager
from idu.core.path_handler import PathHandler
from loguru import logger


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

if __name__ == "__main__":
    sys.exit(run_command())
