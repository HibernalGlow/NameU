"""Path restoration utilities leveraging NameSet archive history."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from loguru import logger

from nameset.manager import ArchiveIDManager
from nameset.id_handler import ArchiveIDHandler

SUPPORTED_EXTENSIONS: Sequence[str] = (".zip", ".rar", ".7z")

LOOKUP_ARCHIVE_INFO = "archive_info"
LOOKUP_ARCHIVE_HISTORY = "archive_history"

RESTORE_LOOKUP_PIPELINE: List[str] = [LOOKUP_ARCHIVE_INFO, LOOKUP_ARCHIVE_HISTORY]


@dataclass
class LookupResult:
    archive_id: str
    source: str
    history_record: Optional[Dict[str, object]] = None
    info_record: Optional[Dict[str, object]] = None


def configure_lookup_pipeline(order: Sequence[str]) -> None:
    allowed = {LOOKUP_ARCHIVE_INFO, LOOKUP_ARCHIVE_HISTORY}
    seen: set[str] = set()
    validated: List[str] = []
    for item in order:
        if item not in allowed:
            raise ValueError(f"未知的查询来源: {item}")
        if item not in seen:
            validated.append(item)
            seen.add(item)
    if not validated:
        raise ValueError("查询来源列表不能为空")
    RESTORE_LOOKUP_PIPELINE[:] = validated


@dataclass
class RestoreOutcome:
    """Result of attempting to restore a single file's path."""

    source_path: str
    archive_id: Optional[str]
    target_path: Optional[str]
    status: str
    message: str
    history_id: Optional[int] = None


class PathRestoreManager:
    """High-level service restoring misplaced archives to recorded destinations."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        *,
        create_missing_dirs: bool = True,
    ) -> None:
        self._manager = ArchiveIDManager(db_path)
        self._db = self._manager.db
        self._create_dirs = create_missing_dirs

    def close(self) -> None:
        self._manager.close()

    def __enter__(self) -> "PathRestoreManager":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # pragma: no cover - context manager boilerplate
        self.close()

    def restore_from_directory(
        self,
        source_dir: str | os.PathLike[str],
        *,
        recursive: bool = True,
        extensions: Sequence[str] | None = SUPPORTED_EXTENSIONS,
        dry_run: bool = True,
        on_progress: Optional[Callable[[str, Optional["RestoreOutcome"]], None]] = None,
    ) -> List[RestoreOutcome]:
        """Attempt to restore every archive under *source_dir*.

        Args:
            source_dir: Directory containing misplaced files.
            recursive: Whether to walk the directory recursively.
            extensions: File suffixes to include; ``None`` means all files.
            dry_run: If ``True`` only plan moves without touching the filesystem.
        """

        outcomes: List[RestoreOutcome] = []
        for file_path in self._iter_files(source_dir, recursive=recursive, extensions=extensions):
            outcome = self.restore_file(file_path, dry_run=dry_run)
            outcomes.append(outcome)
            if on_progress:
                on_progress(file_path, outcome)
        return outcomes

    def restore_file(self, file_path: str | os.PathLike[str], *, dry_run: bool = True) -> RestoreOutcome:
        """Restore a single file based on the archive history."""

        source_path = os.fspath(file_path)
        if not os.path.exists(source_path):
            return RestoreOutcome(
                source_path=source_path,
                archive_id=None,
                target_path=None,
                status="missing",
                message="文件不存在",
            )

        source_abs = os.path.abspath(source_path)
        filename = os.path.basename(source_path)

        lookup_result: Optional[LookupResult] = None
        fallback_outcome: Optional[RestoreOutcome] = None
        for source in RESTORE_LOOKUP_PIPELINE:
            if source == LOOKUP_ARCHIVE_INFO:
                candidate = self._lookup_via_archive_info(source_abs)
            elif source == LOOKUP_ARCHIVE_HISTORY:
                candidate = self._lookup_via_archive_history(source_path, filename)
            else:  # pragma: no cover - future-proof fallback
                continue

            if isinstance(candidate, RestoreOutcome):
                if fallback_outcome is None:
                    fallback_outcome = candidate
                continue
            if candidate:
                lookup_result = candidate
                break

        if not lookup_result:
            if fallback_outcome:
                return fallback_outcome
            return RestoreOutcome(
                source_path=source_path,
                archive_id=None,
                target_path=None,
                status="no-match",
                message="未能在配置的查询顺序中找到匹配记录",
            )

        archive_id = lookup_result.archive_id
        history_record = lookup_result.history_record
        info_record = lookup_result.info_record or self._db.get_archive_info(archive_id)

        target_path: Optional[str] = None
        if history_record:
            target_path = self._resolve_target_path(history_record, archive_id)

        if not target_path and info_record and info_record.get("file_path"):
            target_path = str(info_record["file_path"])

        if not target_path:
            return RestoreOutcome(
                source_path=source_path,
                archive_id=archive_id,
                target_path=None,
                status="no-target",
                message="历史记录中缺少目标路径信息",
                history_id=history_record.get("history_id") if history_record else None,
            )

        target_abs = os.path.abspath(target_path)
        if os.path.normcase(source_abs) == os.path.normcase(target_abs):
            # Update DB to reflect the current location if necessary.
            self._db.update_file_path(archive_id, target_abs)
            return RestoreOutcome(
                source_path=source_path,
                archive_id=archive_id,
                target_path=target_abs,
                status="aligned",
                message="文件已在正确位置，已同步数据库路径",
                history_id=history_record.get("history_id") if history_record else None,
            )

        if dry_run:
            return RestoreOutcome(
                source_path=source_path,
                archive_id=archive_id,
                target_path=target_abs,
                status="planned",
                message=f"计划移动到 {target_abs}",
                history_id=history_record.get("history_id") if history_record else None,
            )

        target_dir = os.path.dirname(target_abs)
        if self._create_dirs:
            os.makedirs(target_dir, exist_ok=True)

        if os.path.exists(target_abs):
            return RestoreOutcome(
                source_path=source_path,
                archive_id=archive_id,
                target_path=target_abs,
                status="skipped",
                message="目标路径已存在同名文件，未执行移动",
                history_id=history_record.get("history_id") if history_record else None,
            )

        try:
            shutil.move(source_abs, target_abs)
            self._db.update_file_path(archive_id, target_abs)
            logger.info(f"恢复路径成功: {source_abs} -> {target_abs} (archive_id={archive_id})")
            return RestoreOutcome(
                source_path=source_path,
                archive_id=archive_id,
                target_path=target_abs,
                status="moved",
                message="文件已移动并更新数据库",
                history_id=history_record.get("history_id") if history_record else None,
            )
        except Exception as exc:  # pragma: no cover - 防止极端路径错误导致测试失败
            logger.error(f"移动文件失败: {source_abs} -> {target_abs}: {exc}")
            return RestoreOutcome(
                source_path=source_path,
                archive_id=archive_id,
                target_path=target_abs,
                status="error",
                message=str(exc),
                history_id=history_record.get("history_id") if history_record else None,
            )

    def _lookup_via_archive_info(self, source_abs: str) -> Optional[LookupResult]:
        archive_id: Optional[str] = None

        comment = ArchiveIDHandler.get_archive_comment(source_abs)
        if comment:
            archive_id = ArchiveIDHandler.extract_id_from_comment(comment)

        if not archive_id:
            archive_id = self._db.get_archive_id_by_path(source_abs)
        if not archive_id:
            return None

        info_record = self._db.get_archive_info(archive_id)
        return LookupResult(
            archive_id=archive_id,
            source=LOOKUP_ARCHIVE_INFO,
            info_record=info_record,
        )

    def _lookup_via_archive_history(self, source_path: str, filename: str) -> Optional[LookupResult | RestoreOutcome]:
        history_records = self._db.find_history_by_new_name(filename)
        if not history_records:
            return None

        archive_ids = {record["archive_id"] for record in history_records}
        if len(archive_ids) > 1:
            return RestoreOutcome(
                source_path=source_path,
                archive_id=None,
                target_path=None,
                status="ambiguous",
                message="找到多个归档ID，无法确定唯一目标",
            )

        record = history_records[0]
        archive_id = record["archive_id"]
        return LookupResult(
            archive_id=archive_id,
            source=LOOKUP_ARCHIVE_HISTORY,
            history_record=record,
        )

    def _iter_files(
        self,
        source_dir: str | os.PathLike[str],
        *,
        recursive: bool,
        extensions: Sequence[str] | None,
    ) -> Iterable[str]:
        base = Path(source_dir)
        if not base.exists():
            logger.warning(f"源目录不存在: {base}")
            return []

        if recursive:
            iterator = base.rglob("*")
        else:
            iterator = base.glob("*")

        for path in iterator:
            if path.is_file():
                if extensions is None or path.suffix.lower() in extensions:
                    yield str(path)

    def _resolve_target_path(self, record: Dict[str, object], archive_id: str) -> Optional[str]:
        metadata = record.get("metadata")
        if isinstance(metadata, dict):
            current_op = metadata.get("current_operation")
            if isinstance(current_op, dict):
                candidate = current_op.get("file_path")
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()

            basic_info = metadata.get("basic_info")
            if isinstance(basic_info, dict):
                candidate = basic_info.get("file_path")
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()

        info = self._db.get_archive_info(archive_id)
        if info and info.get("file_path"):
            return str(info["file_path"])
        return None


__all__ = [
    "PathRestoreManager",
    "RestoreOutcome",
    "SUPPORTED_EXTENSIONS",
    "RESTORE_LOOKUP_PIPELINE",
    "configure_lookup_pipeline",
    "LOOKUP_ARCHIVE_INFO",
    "LOOKUP_ARCHIVE_HISTORY",
]
