import sqlite3

from database.connection import close_connection, get_connection


def test_returns_valid_sqlite_connection_for_memory_database() -> None:
    # given
    connection = get_connection(":memory:")

    # when
    result = connection.execute("SELECT 1").fetchone()

    # then
    assert isinstance(connection, sqlite3.Connection)
    assert result[0] == 1

    close_connection(connection)


def test_applies_schema_to_memory_database() -> None:
    # given
    connection = get_connection(":memory:")
    expected_tables = {
        "projects",
        "protocols",
        "experiments",
        "reagents",
        "equipment",
        "experiment_reagents",
        "experiment_equipment",
        "attachments",
    }

    # when
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()

    # then
    table_names = {row["name"] for row in rows}
    assert expected_tables.issubset(table_names)

    close_connection(connection)


def test_applies_schema_when_database_file_does_not_exist(tmp_path) -> None:
    # given
    database_path = tmp_path / "database.db"

    # when
    connection = get_connection(database_path)

    # then
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        ("experiments",),
    ).fetchone()
    assert row["name"] == "experiments"

    close_connection(connection)
