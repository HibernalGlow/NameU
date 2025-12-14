"""文件扫描器

使用 pathlib 递归扫描目录，生成 RenameJSON 结构。
"""

import logging
from pathlib import Path

from trename.models import DirNode, FileNode, RenameJSON, RenameNode

logger = logging.getLogger(__name__)


class FileScanner:
    """文件扫描器 - 扫描目录生成 RenameJSON"""

    def __init__(self, ignore_hidden: bool = True):
        """初始化扫描器

        Args:
            ignore_hidden: 是否忽略隐藏文件/目录（以 . 开头）
        """
        self.ignore_hidden = ignore_hidden

    def scan(self, root_path: Path) -> RenameJSON:
        """扫描目录，返回 RenameJSON 结构

        Args:
            root_path: 要扫描的根目录路径

        Returns:
            RenameJSON 结构

        Raises:
            FileNotFoundError: 目录不存在
            NotADirectoryError: 路径不是目录
        """
        root_path = Path(root_path).resolve()

        if not root_path.exists():
            raise FileNotFoundError(f"目录不存在: {root_path}")

        if not root_path.is_dir():
            raise NotADirectoryError(f"路径不是目录: {root_path}")

        # 扫描根目录下的所有项目
        nodes = self._scan_children(root_path)
        return RenameJSON(root=nodes)

    def scan_as_single_dir(self, root_path: Path) -> RenameJSON:
        """将目录本身作为根节点扫描

        Args:
            root_path: 要扫描的目录路径

        Returns:
            RenameJSON 结构，root 包含单个 DirNode
        """
        root_path = Path(root_path).resolve()

        if not root_path.exists():
            raise FileNotFoundError(f"目录不存在: {root_path}")

        if not root_path.is_dir():
            raise NotADirectoryError(f"路径不是目录: {root_path}")

        dir_node = self._scan_dir(root_path)
        return RenameJSON(root=[dir_node])

    def _scan_children(self, dir_path: Path) -> list[RenameNode]:
        """扫描目录下的所有子项

        Args:
            dir_path: 目录路径

        Returns:
            子节点列表
        """
        nodes: list[RenameNode] = []

        try:
            items = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        except PermissionError:
            logger.warning(f"权限不足，跳过目录: {dir_path}")
            return nodes

        for item in items:
            # 跳过隐藏文件
            if self.ignore_hidden and item.name.startswith("."):
                continue

            try:
                if item.is_dir():
                    nodes.append(self._scan_dir(item))
                else:
                    nodes.append(FileNode(src=item.name))
            except PermissionError:
                logger.warning(f"权限不足，跳过: {item}")
            except OSError as e:
                logger.warning(f"无法访问 {item}: {e}")

        return nodes

    def _scan_dir(self, dir_path: Path) -> DirNode:
        """扫描单个目录

        Args:
            dir_path: 目录路径

        Returns:
            DirNode 对象
        """
        children = self._scan_children(dir_path)
        return DirNode(src_dir=dir_path.name, children=children)

    def to_json(self, rename_json: RenameJSON, indent: int = 2) -> str:
        """将 RenameJSON 序列化为 JSON 字符串

        Args:
            rename_json: RenameJSON 对象
            indent: 缩进空格数

        Returns:
            JSON 字符串
        """
        return rename_json.model_dump_json(indent=indent, exclude_none=True)

    @staticmethod
    def from_json(json_str: str) -> RenameJSON:
        """从 JSON 字符串解析 RenameJSON

        Args:
            json_str: JSON 字符串

        Returns:
            RenameJSON 对象

        Raises:
            pydantic.ValidationError: JSON 格式或结构无效
        """
        return RenameJSON.model_validate_json(json_str)
