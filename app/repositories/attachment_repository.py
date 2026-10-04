import sqlite3
from collections.abc import Sequence

from app.repositories import experiment_repository


def create(
    connection: sqlite3.Connection,
    experiment_id: int,
    file_name: str,
    stored_name: str,
    extension: str,
    description: str | None = None,
) -> int:
    normalized = description.strip() if description and description.strip() else None
    cursor = connection.execute(
        "INSERT INTO attachments "
        "(experiment_id, file_name, stored_name, extension, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (experiment_id, file_name, stored_name, extension, normalized),
    )
    experiment_repository.touch(connection, experiment_id)
    connection.commit()
    return cursor.lastrowid


def get_by_experiment(
    connection: sqlite3.Connection,
    experiment_id: int,
) -> Sequence[sqlite3.Row]:
    cursor = connection.execute(
        "SELECT id, experiment_id, file_name, stored_name, extension, description "
        "FROM attachments WHERE experiment_id = ?",
        (experiment_id,),
    )
    return cursor.fetchall()


def update_description(
    connection: sqlite3.Connection,
    attachment_id: int,
    experiment_id: int,
    description: str | None,
) -> None:
    normalized = description.strip() if description and description.strip() else None
    connection.execute(
        "UPDATE attachments SET description = ? WHERE id = ?",
        (normalized, attachment_id),
    )
    experiment_repository.touch(connection, experiment_id)
    connection.commit()


def delete(
    connection: sqlite3.Connection,
    attachment_id: int,
    experiment_id: int,
) -> None:
    connection.execute(
        "DELETE FROM attachments WHERE id = ?",
        (attachment_id,),
    )
    experiment_repository.touch(connection, experiment_id)
    connection.commit()
