"""
进度管理模块 - 提供 Rich 终端 UI 支持

功能:
1. 动态文件树显示 (智能折叠，限制显示数量)
2. 参考 repacku 的进度条样式
3. 线程安全更新
"""
import os
import threading
from typing import Deque, Dict, List, Optional, Set
from enum import Enum, auto
from collections import deque
from rich.tree import Tree
from rich.live import Live
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
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
MAX_FILES_PER_DIR = 3
MAX_VISIBLE_DIRS = 6
MAX_VISIBLE_FAILED_DIRS = 2
MAX_RECENT_RENAMES = 8

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
        self.failed_count = 0
        self.processing_count = 0
        self.renamed_count = 0
        self.recent_renames: Deque[dict] = deque(maxlen=MAX_RECENT_RENAMES)
        self.render_tick = 0
        
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
        self.render_tick += 1
        summary = self._build_summary_panel()
        tree = Tree("📁 [bold blue]NameU 处理进度[/bold blue]")

        visible_dirs = self._get_visible_directories()

        for dir_path in visible_dirs:
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
            
            dir_node = tree.add(f"📁 [blue]{dir_name}[/blue] ({done_count}/{total_in_dir})")

            files_to_show: List[tuple] = []
            for fp in processing:
                files_to_show.append((fp, FileStatus.PROCESSING))
            for fp in failed:
                if len(files_to_show) < MAX_FILES_PER_DIR:
                    files_to_show.append((fp, FileStatus.FAILED))
            remaining_slots = MAX_FILES_PER_DIR - len(files_to_show)
            if remaining_slots > 0:
                for fp in pending[:remaining_slots]:
                    files_to_show.append((fp, FileStatus.PENDING))

            for fp, st in files_to_show:
                name = os.path.basename(fp)
                icon, style = self._get_status_style(st)
                dir_node.add(f"{icon} [{style}]{name}[/{style}]")

            hidden_count = total_in_dir - len(files_to_show)
            if hidden_count > 0:
                dir_node.add(f"[dim]... 还有 {hidden_count} 个文件[/dim]")
        
        recent = self._build_recent_panel()
        top = Columns([summary, recent], equal=True, expand=True)
        return Group(top, tree, self.progress)

    def _build_summary_panel(self):
        pending_count = max(0, self.total_count - self.completed_count - self.processing_count)
        lines = [f"[bold cyan]文件[/bold cyan] {self.completed_count}/{self.total_count}"]
        stats = [f"[yellow]{self.processing_count} 处理中[/yellow]"]
        if pending_count:
            stats.append(f"[white]{pending_count} 待处理[/white]")
        if self.failed_count:
            stats.append(f"[red]{self.failed_count} 失败[/red]")
        if self.renamed_count:
            stats.append(f"[magenta]{self.renamed_count} 改名[/magenta]")
        lines.append("  ".join(stats))
        return Panel("\n".join(lines), title="摘要", border_style="cyan")

    def _build_recent_panel(self):
        if not self.recent_renames:
            body = "[dim]暂无重命名预览[/dim]"
        else:
            lines = []
            for item in list(self.recent_renames)[-MAX_RECENT_RENAMES:]:
                suffix = " [yellow][重名避让][/yellow]" if item["duplicate"] else ""
                lines.append(f"[dim]{item['old']}[/dim]\n→ [green]{item['new']}[/green]{suffix}")
            body = "\n".join(lines)
        return Panel(body, title="最近改名", border_style="magenta")

    def _get_visible_directories(self) -> List[str]:
        active_dirs: List[str] = []
        failed_dirs: List[str] = []

        for dir_path in self.dir_order:
            files = self.directories.get(dir_path, set())
            if not files:
                continue

            has_failed = False
            all_completed = True
            for fp in files:
                status = self.file_status.get(fp, FileStatus.PENDING)
                if status == FileStatus.FAILED:
                    has_failed = True
                if status not in (FileStatus.DONE, FileStatus.SKIPPED, FileStatus.FAILED):
                    all_completed = False

            if not all_completed:
                active_dirs.append(dir_path)
            elif has_failed:
                failed_dirs.append(dir_path)

        visible_active = self._rotate_list(active_dirs, MAX_VISIBLE_DIRS)
        visible_failed = failed_dirs[-MAX_VISIBLE_FAILED_DIRS:]
        return visible_active + visible_failed

    def _rotate_list(self, items: List[str], limit: int) -> List[str]:
        if len(items) <= limit:
            return items

        start = (self.render_tick // 4) % len(items)
        ordered = items[start:] + items[:start]
        return ordered[:limit]

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

            if old_status == FileStatus.PROCESSING and status != FileStatus.PROCESSING:
                self.processing_count = max(0, self.processing_count - 1)
            elif old_status != FileStatus.PROCESSING and status == FileStatus.PROCESSING:
                self.processing_count += 1
            
            if status in [FileStatus.DONE, FileStatus.SKIPPED, FileStatus.FAILED]:
                if old_status in [FileStatus.PENDING, FileStatus.PROCESSING]:
                    self.completed_count += 1
                    if status == FileStatus.FAILED:
                        self.failed_count += 1
                    if self.main_task is not None:
                        self.progress.update(
                            self.main_task, 
                            completed=self.completed_count, 
                            description=f"[cyan]处理中: {self.completed_count}/{self.total_count}"
                        )
            
            # 触发 Live 刷新
            if self.live:
                self.live.update(self._build_display())

    def record_rename(self, old_name: str, new_name: str, duplicate: bool = False):
        with self.lock:
            self.renamed_count += 1
            self.recent_renames.append(
                {
                    "old": old_name,
                    "new": new_name,
                    "duplicate": duplicate,
                }
            )
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
