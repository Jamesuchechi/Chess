"""Tests for SQLite database initialization and schema management."""

import tempfile
from pathlib import Path

from chess_desktop.persistence.database import DatabaseManager


def test_database_in_memory_initialization() -> None:
    """Verify in-memory database initializes schema and persists while manager is alive."""
    db = DatabaseManager(":memory:")
    with db.connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='games';"
        ).fetchall()
        assert len(tables) == 1
        assert tables[0]["name"] == "games"
    db.close()


def test_database_file_initialization() -> None:
    """Verify file-backed database creates file, directory, and sets WAL mode."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "sub_dir" / "test.db"
        db = DatabaseManager(db_path)
        assert db_path.exists()

        with db.connection() as conn:
            mode = conn.execute("PRAGMA journal_mode;").fetchone()
            assert mode[0].lower() == "wal"

            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='games';"
            ).fetchall()
            assert len(tables) == 1
        db.close()
