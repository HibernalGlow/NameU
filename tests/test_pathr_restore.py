import json
import shutil
import sqlite3
import uuid

import pytest

from nameset.database import ArchiveDatabase
from typer.testing import CliRunner

from pathr import PathRestoreManager
from pathr.cli import app as pathr_app


@pytest.fixture
def make_archive(tmp_path):
    def _make_archive(database_name: str = "archives.db"):
        db_path = tmp_path / database_name
        correct_dir = tmp_path / f"correct_{database_name}"
        misplaced_dir = tmp_path / f"misplaced_{database_name}"
        correct_dir.mkdir(parents=True, exist_ok=True)
        misplaced_dir.mkdir(parents=True, exist_ok=True)

        target_name = "restored_archive.zip"
        final_path = correct_dir / target_name
        final_path.write_bytes(b"PK\x03\x04dummy-zip-content")

        archive_id = f"test-{uuid.uuid4().hex[:12]}"
        database = ArchiveDatabase(str(db_path))
        created = database.create_archive_record(archive_id, str(final_path), target_name)
        assert created, "Failed to create archive record"

        metadata = {
            "current_operation": {
                "file_path": str(final_path),
                "operation_type": "rename",
                "source": "test",
            }
        }

        with sqlite3.connect(database.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                    INSERT INTO archive_history (archive_id, old_name, new_name, reason, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    archive_id,
                    None,
                    target_name,
                    "unit-test",
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )
            conn.commit()

        return {
            "db_path": db_path,
            "archive_id": archive_id,
            "final_path": final_path,
            "misplaced_dir": misplaced_dir,
            "misplaced_path": misplaced_dir / target_name,
        }

    return _make_archive


def test_restore_file_moves_to_recorded_path(make_archive):
    setup = make_archive("move.db")
    shutil.move(setup["final_path"], setup["misplaced_path"])
    assert setup["misplaced_path"].exists()

    with PathRestoreManager(str(setup["db_path"])) as restorer:
        outcome = restorer.restore_file(str(setup["misplaced_path"]), dry_run=False)

    assert outcome.status == "moved"
    assert outcome.target_path == str(setup["final_path"])
    assert not setup["misplaced_path"].exists()
    assert setup["final_path"].exists()

    database = ArchiveDatabase(str(setup["db_path"]))
    info = database.get_archive_info(outcome.archive_id)
    assert info is not None
    assert info["file_path"] == str(setup["final_path"])


def test_restore_file_dry_run(make_archive):
    setup = make_archive("dryrun.db")
    shutil.move(setup["final_path"], setup["misplaced_path"])

    with PathRestoreManager(str(setup["db_path"])) as restorer:
        outcome = restorer.restore_file(str(setup["misplaced_path"]), dry_run=True)

    assert outcome.status == "planned"
    assert setup["misplaced_path"].exists()
    assert outcome.target_path == str(setup["final_path"])


def test_cli_restore_interactive(make_archive):
    setup = make_archive("cli.db")
    shutil.move(setup["final_path"], setup["misplaced_path"])

    runner = CliRunner()
    result = runner.invoke(
        pathr_app,
        [
            "restore",
            str(setup["misplaced_dir"]),
            "--db",
            str(setup["db_path"]),
            "--interactive",
        ],
        input="\n\n",
    )

    assert result.exit_code == 0
    assert not setup["misplaced_path"].exists()
    assert setup["final_path"].exists()
