"""冲突检测器

检测重命名操作中的冲突：目标已存在、重复目标等。
"""

from collections import defaultdict
from pathlib import Path

from trename.models import (
    Conflict,
    ConflictType,
    DirNode,
    FileNode,
    RenameJSON,
    RenameNode,
)


class ConflictValidator:
    """冲突检测器"""

    def validate(self, rename_json: RenameJSON, base_path: Path) -> list[Conflict]:
        """检测所有冲突

        Args:
            rename_json: RenameJSON 结构
            base_path: 基础路径（文件系统中的实际路径）

        Returns:
            冲突列表
        """
        conflicts: list[Conflict] = []
        base_path = Path(base_path).resolve()

        # 收集所有目标路径用于检测重复
        target_paths: dict[Path, list[Path]] = defaultdict(list)

        # 递归检测
        for node in rename_json.root:
            self._validate_node(node, base_path, conflicts, target_paths)

        # 检测重复目标
        conflicts.extend(self._check_duplicate_targets(target_paths))

        return conflicts

    def _validate_node(
        self,
        node: RenameNode,
        parent_path: Path,
        conflicts: list[Conflict],
        target_paths: dict[Path, list[Path]],
    ) -> None:
        """递归验证节点

        Args:
            node: 当前节点
            parent_path: 父目录路径
            conflicts: 冲突列表（会被修改）
            target_paths: 目标路径映射（会被修改）
        """
        if isinstance(node, FileNode):
            src_path = parent_path / node.src
            if node.is_ready:
                tgt_path = parent_path / node.tgt
                # 检查目标是否已存在
                if self._check_target_exists(src_path, tgt_path):
                    conflicts.append(
                        Conflict(
                            type=ConflictType.TARGET_EXISTS,
                            src_path=src_path,
                            tgt_path=tgt_path,
                            message=f"目标文件已存在: {tgt_path}",
                        )
                    )
                # 记录目标路径
                target_paths[tgt_path].append(src_path)

        elif isinstance(node, DirNode):
            src_path = parent_path / node.src_dir
            current_path = src_path  # 用于子节点的路径计算

            if node.is_ready:
                tgt_path = parent_path / node.tgt_dir
                # 检查目标是否已存在
                if self._check_target_exists(src_path, tgt_path):
                    conflicts.append(
                        Conflict(
                            type=ConflictType.TARGET_EXISTS,
                            src_path=src_path,
                            tgt_path=tgt_path,
                            message=f"目标目录已存在: {tgt_path}",
                        )
                    )
                # 记录目标路径
                target_paths[tgt_path].append(src_path)

            # 递归处理子节点
            for child in node.children:
                self._validate_node(child, current_path, conflicts, target_paths)

    def _check_target_exists(self, src_path: Path, tgt_path: Path) -> bool:
        """检查目标路径是否已存在（且不是源路径本身）

        Args:
            src_path: 源路径
            tgt_path: 目标路径

        Returns:
            目标是否已存在
        """
        if src_path == tgt_path:
            return False
        return tgt_path.exists()

    def _check_duplicate_targets(
        self, target_paths: dict[Path, list[Path]]
    ) -> list[Conflict]:
        """检查重复目标

        Args:
            target_paths: 目标路径到源路径列表的映射

        Returns:
            重复目标冲突列表
        """
        conflicts: list[Conflict] = []

        for tgt_path, src_paths in target_paths.items():
            if len(src_paths) > 1:
                for src_path in src_paths:
                    conflicts.append(
                        Conflict(
                            type=ConflictType.DUPLICATE_TARGET,
                            src_path=src_path,
                            tgt_path=tgt_path,
                            message=f"多个源映射到同一目标: {tgt_path}",
                        )
                    )

        return conflicts

    def get_valid_operations(
        self, rename_json: RenameJSON, base_path: Path
    ) -> tuple[list[tuple[Path, Path]], list[Conflict]]:
        """获取有效的重命名操作和冲突

        Args:
            rename_json: RenameJSON 结构
            base_path: 基础路径

        Returns:
            (有效操作列表, 冲突列表)
        """
        conflicts = self.validate(rename_json, base_path)
        conflict_paths = {(c.src_path, c.tgt_path) for c in conflicts}

        operations: list[tuple[Path, Path]] = []
        base_path = Path(base_path).resolve()

        def collect_operations(node: RenameNode, parent_path: Path) -> None:
            if isinstance(node, FileNode):
                if node.is_ready:
                    src = parent_path / node.src
                    tgt = parent_path / node.tgt
                    if (src, tgt) not in conflict_paths:
                        operations.append((src, tgt))

            elif isinstance(node, DirNode):
                src_path = parent_path / node.src_dir
                # 先处理子节点
                for child in node.children:
                    collect_operations(child, src_path)
                # 再处理目录本身
                if node.is_ready:
                    tgt = parent_path / node.tgt_dir
                    if (src_path, tgt) not in conflict_paths:
                        operations.append((src_path, tgt))

        for node in rename_json.root:
            collect_operations(node, base_path)

        return operations, conflicts
