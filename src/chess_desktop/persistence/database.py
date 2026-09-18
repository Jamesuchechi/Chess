"""SQLite database connection and schema management."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import QStandardPaths


class DatabaseManager:
    """Manages SQLite database connections, schema migrations, and PRAGMAs."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            base_dir = Path(
                QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            )
            base_dir.mkdir(parents=True, exist_ok=True)
            self._db_path = str(base_dir / "chess.db")
        else:
            self._db_path = str(db_path)
            if self._db_path != ":memory:":
                parent = Path(self._db_path).parent
                parent.mkdir(parents=True, exist_ok=True)

        self._memory_conn: sqlite3.Connection | None = None
        if self._db_path == ":memory:":
            self._memory_conn = self._create_connection()

        self.initialize_schema()

    @property
    def db_path(self) -> str:
        """Database file path or :memory: identifier."""
        return self._db_path

    def _create_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        if self._db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a managed connection with commit/rollback."""
        if self._memory_conn is not None:
            conn = self._memory_conn
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        else:
            conn = self._create_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def initialize_schema(self) -> None:
        """Create tables and indices if they do not already exist."""
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    white_name TEXT NOT NULL,
                    black_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT NOT NULL,
                    fen TEXT NOT NULL,
                    pgn TEXT NOT NULL,
                    moves_uci TEXT NOT NULL,
                    move_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_games_updated_at ON games (updated_at DESC);
                """
            )

    def close(self) -> None:
        """Close persistent resources (relevant for in-memory database)."""
        if self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None
