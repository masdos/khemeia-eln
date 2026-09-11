import sqlite3
from collections.abc import Sequence


def create(
    connection: sqlite3.Connection,
    file_name: str,
    stored_name: str,
    extension: str,
) -> int:
    """Create a report record and return its identifier."""
    cursor = connection.execute(
        "INSERT INTO reports (file_name, stored_name, extension) VALUES (?, ?, ?)",
        (file_name, stored_name, extension),
    )
    connection.commit()
    return cursor.lastrowid


def link_to_experiments(
    connection: sqlite3.Connection,
    report_id: int,
    experiment_ids: Sequence[int],
) -> None:
    """Link a report to the supplied experiments."""
    connection.executemany(
        "INSERT INTO experiment_reports (experiment_id, report_id) VALUES (?, ?)",
        [(experiment_id, report_id) for experiment_id in experiment_ids],
    )
    connection.commit()


def get_by_experiment(
    connection: sqlite3.Connection,
    experiment_id: int,
) -> Sequence[sqlite3.Row]:
    """Return reports linked to an experiment."""
    cursor = connection.execute(
        "SELECT reports.id, reports.file_name, reports.stored_name, reports.extension "
        "FROM reports "
        "INNER JOIN experiment_reports ON experiment_reports.report_id = reports.id "
        "WHERE experiment_reports.experiment_id = ?",
        (experiment_id,),
    )
    return cursor.fetchall()


def get_by_id(
    connection: sqlite3.Connection,
    report_id: int,
) -> sqlite3.Row | None:
    """Return a report by identifier, or None when it does not exist."""
    cursor = connection.execute(
        "SELECT id, file_name, stored_name, extension FROM reports WHERE id = ?",
        (report_id,),
    )
    return cursor.fetchone()
