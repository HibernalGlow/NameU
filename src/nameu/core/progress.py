import os
import threading
from typing import Dict, List, Optional
from enum import Enum, auto
from rich.tree import Tree
from rich.live import Live
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

class FileStatus(Enum):
    PENDING = auto()
    PROCESSING = auto()
    DONE = auto()
    FAILED = auto()
    SKIPPED = auto()

class ProgressManager:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.live: Optional[Live] = None
        self.tree = Tree("📁 [bold blue]NameU 处理树[/bold blue]")
        self.nodes: Dict[str, Tree] = {}  # path -> tree node
        self.file_status: Dict[str, FileStatus] = {}  # full_path -> status
        self.lock = threading.Lock()
        
        # 统计信息
        self.total_count = 0
        self.completed_count = 0
        
        # 全局进度条 (可选)
        self.overall_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        self.overall_task = None
        self.log_handler_id = None
        self.enabled = False

    def start(self):
        """启动 Live 显示"""
        if not self.enabled:
            return
        # 拦截 loguru 日志并重定向到 rich console
        from loguru import logger
        try:
            # 尝试移除原有的控制台处理器（如果存在）
            # 注意：这可能会影响其他部分的日志，但 Live 模式下通常需要接管输出
            self.log_handler_id = logger.add(
                lambda msg: self.console.print(msg, end=""),
                format="{message}",
                level="INFO",
                colorize=True
            )
        except Exception:
            pass

        self.live = Live(self._build_display_group(), console=self.console, refresh_per_second=4, transient=False)
        self.live.start()

    def stop(self):
        """停止 Live 显示"""
        from loguru import logger
        if self.log_handler_id is not None:
            logger.remove(self.log_handler_id)
            self.log_handler_id = None

        if self.live:
            # 最终刷新一次
            self.live.update(self._build_display_group())
            self.live.stop()
            self.live = None

    def _build_display_group(self):
        """构建整体显示组件"""
        return Group(
            self.tree,
            self.overall_progress
        )

    def add_directory(self, path: str, parent_path: Optional[str] = None):
        """在树中添加目录"""
        with self.lock:
            if path in self.nodes:
                return self.nodes[path]
                
            name = os.path.basename(path)
            if parent_path and parent_path in self.nodes:
                parent_node = self.nodes[parent_path]
                node = parent_node.add(f"📁 [blue]{name}[/blue]")
            else:
                node = self.tree.add(f"📁 [blue]{name}[/blue]")
            self.nodes[path] = node
            return node

    def add_file(self, file_path: str, parent_path: str):
        """在树中添加文件"""
        with self.lock:
            name = os.path.basename(file_path)
            if parent_path in self.nodes:
                parent_node = self.nodes[parent_path]
                # 这里不直接 add，而是先记录状态，在渲染时决定表现
                self.file_status[file_path] = FileStatus.PENDING
                self._update_node_text(file_path)
            self.total_count += 1
            if self.overall_task is None:
                self.overall_task = self.overall_progress.add_task("总体进度", total=self.total_count)
            else:
                self.overall_progress.update(self.overall_task, total=self.total_count)

    def update_status(self, file_path: str, status: FileStatus):
        """更新文件状态"""
        with self.lock:
            old_status = self.file_status.get(file_path)
            self.file_status[file_path] = status
            
            if status in [FileStatus.DONE, FileStatus.SKIPPED, FileStatus.FAILED] and old_status != status:
                if old_status in [FileStatus.PENDING, FileStatus.PROCESSING]:
                    self.completed_count += 1
                    if self.overall_task is not None:
                        self.overall_progress.update(self.overall_task, completed=self.completed_count)
            
            self._update_node_text(file_path)

    def _update_node_text(self, file_path: str):
        """刷新树节点文本"""
        # 为了性能和结构一致性，我们在添加文件时就创建节点
        # 如果节点不存在则创建
        parent_dir = os.path.dirname(file_path)
        name = os.path.basename(file_path)
        status = self.file_status.get(file_path, FileStatus.PENDING)
        
        icon = "⏳"
        style = "white"
        
        if status == FileStatus.PROCESSING:
            icon = "⚙️ "
            style = "bold yellow"
        elif status == FileStatus.DONE:
            icon = "✅"
            style = "green"
        elif status == FileStatus.FAILED:
            icon = "❌"
            style = "red"
        elif status == FileStatus.SKIPPED:
            icon = "⏩"
            style = "dim"

        display_text = f"{icon} [{style}]{name}[/{style}]"
        
        # 如果该文件已有节点，则更新它。注意 Tree 节点不易直接更新 text，
        # 在这种动态场景下，我们通常在渲染时重建树或动态替换。
        # 简单起见，我们暂存节点引用
        node_key = f"file:{file_path}"
        if node_key in self.nodes:
            self.nodes[node_key].label = display_text
        else:
            if parent_dir in self.nodes:
                node = self.nodes[parent_dir].add(display_text)
                self.nodes[node_key] = node

# 全局单例以便简单调用
_manager: Optional[ProgressManager] = None

def init_progress(console: Optional[Console] = None, enable: bool = False):
    global _manager
    _manager = ProgressManager(console)
    _manager.enabled = enable
    return _manager

def get_manager() -> Optional[ProgressManager]:
    return _manager
