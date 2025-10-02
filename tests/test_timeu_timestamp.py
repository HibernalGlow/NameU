import os
import zipfile

import orjson
import pytest

from nameset.id_handler import ArchiveIDHandler
from timeu.__main__ import TimestampManager


@pytest.fixture(autouse=True)
def clear_comment_cache():
    ArchiveIDHandler.clear_comment_cache()
    yield
    ArchiveIDHandler.clear_comment_cache()


def test_save_timestamps_records_archive_id(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    archive_path = data_dir / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("dummy.txt", "content")

    monkeypatch.setattr(
        "nameset.id_handler.ArchiveIDHandler.get_archive_comment",
        lambda path: '{"id": "UUID-123"}',
    )
    monkeypatch.setattr(
        "nameset.id_handler.ArchiveIDHandler.extract_id_from_comment",
        lambda comment: "UUID-123",
    )

    manager = TimestampManager(backup_dir=str(backup_dir))
    manager.save_timestamps(str(data_dir), version_name="unit")

    backup_file = backup_dir / "timestamps_unit.json"
    assert backup_file.exists()

    timestamps = orjson.loads(backup_file.read_bytes())

    record = timestamps[str(archive_path)]
    assert record["archive_id"] == "UUID-123"
    assert "access_time" in record and "mod_time" in record


def test_save_timestamps_ignores_non_archives(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    regular_file = data_dir / "note.txt"
    regular_file.write_text("hello")

    marker = {}

    def fake_get_comment(path: str):
        marker["called"] = True
        return None

    monkeypatch.setattr(
        "nameset.id_handler.ArchiveIDHandler.get_archive_comment",
        fake_get_comment,
    )

    manager = TimestampManager(backup_dir=str(backup_dir))
    manager.save_timestamps(str(data_dir), version_name="plain")

    backup_file = backup_dir / "timestamps_plain.json"
    assert backup_file.exists()

    timestamps = orjson.loads(backup_file.read_bytes())
    record = timestamps[str(regular_file)]
    assert "archive_id" not in record
    assert "called" not in marker
