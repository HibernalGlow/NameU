"""
进度管理模块 - 提供 Rich 终端 UI 支持

功能:
1. 动态文件树显示 (智能折叠，限制显示数量)
2. 参考 repacku 的进度条样式
3. 线程安全更新
"""
import os
import threading
from typing import Dict, List, Optional, Set
from enum import Enum, auto
from collections import deque
from rich.tree import Tree
from rich.live import Live
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.progress import (
    Progress, 
    SpinnerColumn, 
    TextColumn, 
    BarColumn, 
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn
)

# === 配置常量 ===
MAX_FILES_PER_DIR = 5       # 每个目录最多显示的文件数
MAX_RECENT_COMPLETED = 3    # 已完成文件中最多保留显示的数量
SHOW_PROCESSING_FIRST = True # 优先显示正在处理的文件

class FileStatus(Enum):
    PENDING = auto()
    PROCESSING = auto()
    DONE = auto()
    FAILED = auto()
    SKIPPED = auto()

class ProgressManager:
    """
    智能进度管理器
    
    - 动态树: 每个目录只显示有限数量的文件，优先展示正在处理的项目
    - 折叠策略: 已完成的目录会显示汇总而非全部文件
    - 进度条: 参考 repacku 风格
    """
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.live: Optional[Live] = None
        self.lock = threading.Lock()
        
        # 目录和文件追踪
        self.directories: Dict[str, Set[str]] = {}  # dir_path -> set of file_paths
        self.file_status: Dict[str, FileStatus] = {}  # full_path -> status
        self.dir_order: List[str] = []  # 保持目录添加顺序
        
        # 统计信息
        self.total_count = 0
        self.completed_count = 0
        
        # 参考 repacku 样式的进度条
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self.console,
            transient=True
        )
        self.main_task = None
        self.enabled = False
        self.log_handler_id = None

    def start(self):
        """启动 Live 显示"""
        if not self.enabled:
            return
            
        from loguru import logger
        try:
            logger.remove()
            self.log_handler_id = logger.add(
                lambda msg: self.console.print(msg, end=""),
                format="{message}",
                level="INFO",
                colorize=True
            )
        except Exception:
            pass

        if self.main_task is None:
            self.main_task = self.progress.add_task("[cyan]准备中...", total=1)

        self.live = Live(self._build_display(), console=self.console, refresh_per_second=4, transient=False)
        self.live.start()

    def stop(self):
        """停止 Live 显示"""
        from loguru import logger
        if self.enabled and self.log_handler_id is not None:
            logger.remove(self.log_handler_id)
            self.log_handler_id = None

        if self.live:
            self.live.update(self._build_display())
            self.live.stop()
            self.live = None

    def _build_display(self):
        """构建智能树形显示"""
        tree = Tree("📁 [bold blue]NameU 处理进度[/bold blue]")
        
        for dir_path in self.dir_order:
            files = self.directories.get(dir_path, set())
            if not files:
                continue
            
            dir_name = os.path.basename(dir_path)
            
            # 统计该目录下的状态
            processing = []
            pending = []
            done = []
            failed = []
            
            for fp in files:
                st = self.file_status.get(fp, FileStatus.PENDING)
                if st == FileStatus.PROCESSING:
                    processing.append(fp)
                elif st == FileStatus.PENDING:
                    pending.append(fp)
                elif st == FileStatus.DONE or st == FileStatus.SKIPPED:
                    done.append(fp)
                elif st == FileStatus.FAILED:
                    failed.append(fp)
            
            total_in_dir = len(files)
            done_count = len(done) + len(failed)
            
            # 目录节点：显示进度概览
            if done_count == total_in_dir:
                # 全部完成，折叠显示
                fail_text = f" [red]({len(failed)} 失败)[/red]" if failed else ""
                dir_node = tree.add(f"📁 [green]{dir_name}[/green] ✅ {done_count}/{total_in_dir}{fail_text}")
            else:
                # 正在处理中
                dir_node = tree.add(f"📁 [blue]{dir_name}[/blue] ({done_count}/{total_in_dir})")
                
                # 智能选择要显示的文件
                files_to_show: List[tuple] = []  # (path, status)
                
                # 1. 优先显示正在处理的
                for fp in processing:
                    files_to_show.append((fp, FileStatus.PROCESSING))
                
                # 2. 显示失败的（重要）
                for fp in failed:
                    files_to_show.append((fp, FileStatus.FAILED))
                
                # 3. 如果还有空位，显示最近完成的
                remaining_slots = MAX_FILES_PER_DIR - len(files_to_show)
                if remaining_slots > 0:
                    for fp in done[-MAX_RECENT_COMPLETED:]:
                        if len(files_to_show) < MAX_FILES_PER_DIR:
                            files_to_show.append((fp, FileStatus.DONE))
                
                # 4. 如果还有空位，显示待处理的
                remaining_slots = MAX_FILES_PER_DIR - len(files_to_show)
                if remaining_slots > 0:
                    for fp in pending[:remaining_slots]:
                        files_to_show.append((fp, FileStatus.PENDING))
                
                # 渲染文件节点
                for fp, st in files_to_show:
                    name = os.path.basename(fp)
                    icon, style = self._get_status_style(st)
                    dir_node.add(f"{icon} [{style}]{name}[/{style}]")
                
                # 如果有隐藏的文件，显示省略信息
                hidden_count = total_in_dir - len(files_to_show)
                if hidden_count > 0:
                    dir_node.add(f"[dim]... 还有 {hidden_count} 个文件[/dim]")
        
        return Group(tree, self.progress)

    def _get_status_style(self, status: FileStatus) -> tuple:
        """返回状态对应的图标和样式"""
        if status == FileStatus.PROCESSING:
            return "⚙️ ", "bold yellow"
        elif status == FileStatus.DONE:
            return "✅", "green"
        elif status == FileStatus.FAILED:
            return "❌", "red"
        elif status == FileStatus.SKIPPED:
            return "⏩", "dim"
        else:  # PENDING
            return "⏳", "white"

    def add_directory(self, path: str, parent_path: Optional[str] = None):
        """注册目录"""
        with self.lock:
            if path not in self.directories:
                self.directories[path] = set()
                self.dir_order.append(path)

    def add_file(self, file_path: str, parent_path: str):
        """注册文件"""
        with self.lock:
            if parent_path not in self.directories:
                self.directories[parent_path] = set()
                self.dir_order.append(parent_path)
            
            self.directories[parent_path].add(file_path)
            self.file_status[file_path] = FileStatus.PENDING
            self.total_count += 1
            
            if self.main_task is not None:
                self.progress.update(self.main_task, total=self.total_count, description=f"[cyan]规划中: {self.total_count} 文件")

    def update_status(self, file_path: str, status: FileStatus):
        """更新文件状态"""
        with self.lock:
            old_status = self.file_status.get(file_path)
            self.file_status[file_path] = status
            
            if status in [FileStatus.DONE, FileStatus.SKIPPED, FileStatus.FAILED]:
                if old_status in [FileStatus.PENDING, FileStatus.PROCESSING]:
                    self.completed_count += 1
                    if self.main_task is not None:
                        self.progress.update(
                            self.main_task, 
                            completed=self.completed_count, 
                            description=f"[cyan]处理中: {self.completed_count}/{self.total_count}"
                        )
            
            # 触发 Live 刷新
            if self.live:
                self.live.update(self._build_display())

# 全局单例
_manager: Optional[ProgressManager] = None

def init_progress(console: Optional[Console] = None, enable: bool = False):
    global _manager
    _manager = ProgressManager(console)
    _manager.enabled = enable
    return _manager

def get_manager() -> Optional[ProgressManager]:
    return _manager
