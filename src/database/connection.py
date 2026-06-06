import sqlite3
from pathlib import Path

DEFAULT_DATABASE_PATH = Path("data/database.db")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

_connection: sqlite3.Connection | None = None


def get_connection(database_path: str | Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enabled."""
    if database_path is None:
        return _get_default_connection()

    return _create_connection(database_path)


def close_connection(connection: sqlite3.Connection | None = None) -> None:
    """Close a SQLite connection or the shared default connection."""
    global _connection

    if connection is not None:
        connection.close()
        return

    if _connection is not None:
        _connection.close()
        _connection = None


def _get_default_connection() -> sqlite3.Connection:
    global _connection

    if _connection is None:
        _connection = _create_connection(DEFAULT_DATABASE_PATH)

    return _connection


def _create_connection(database_path: str | Path) -> sqlite3.Connection:
    if database_path == ":memory:":
        connection = _connect(database_path)
        _apply_schema(connection)
        return connection

    path = Path(database_path)
    database_missing = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = _connect(path)
    if database_missing:
        _apply_schema(connection)

    return connection


def _connect(database_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _apply_schema(connection: sqlite3.Connection) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    connection.executescript(schema_sql)
    connection.commit()
