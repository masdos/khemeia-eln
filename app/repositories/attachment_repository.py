import sqlite3
from collections.abc import Sequence


def create(
    connection: sqlite3.Connection,
    experiment_id: int,
    file_name: str,
    stored_name: str,
) -> int:
    cursor = connection.execute(
        "INSERT INTO attachments (experiment_id, file_name, stored_name) "
        "VALUES (?, ?, ?)",
        (experiment_id, file_name, stored_name),
    )
    connection.commit()
    return cursor.lastrowid


def get_by_experiment(
    connection: sqlite3.Connection,
    experiment_id: int,
) -> Sequence[sqlite3.Row]:
    cursor = connection.execute(
        "SELECT id, experiment_id, file_name, stored_name "
        "FROM attachments WHERE experiment_id = ?",
        (experiment_id,),
    )
    return cursor.fetchall()


def delete(
    connection: sqlite3.Connection,
    attachment_id: int,
) -> None:
    connection.execute(
        "DELETE FROM attachments WHERE id = ?",
        (attachment_id,),
    )
    connection.commit()
