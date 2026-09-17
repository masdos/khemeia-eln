import sqlite3
from collections.abc import Sequence


def create(
    connection: sqlite3.Connection,
    project_id: int,
    title: str,
    content_markdown: str = "",
) -> int:
    """Create a report record and return its identifier."""
    cursor = connection.execute(
        "INSERT INTO reports (project_id, title, content_markdown)"
        " VALUES (?, ?, ?)",
        (project_id, title, content_markdown),
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
        "SELECT reports.id, reports.project_id, reports.title, "
        "reports.content_markdown, reports.created_at, reports.modified_at "
        "FROM reports "
        "INNER JOIN experiment_reports ON experiment_reports.report_id = reports.id "
        "WHERE experiment_reports.experiment_id = ?",
        (experiment_id,),
    )
    return cursor.fetchall()


def get_by_project(
    connection: sqlite3.Connection,
    project_id: int,
) -> Sequence[sqlite3.Row]:
    """Return reports belonging to a project."""
    cursor = connection.execute(
        "SELECT id, project_id, title, content_markdown, created_at, modified_at "
        "FROM reports WHERE project_id = ?",
        (project_id,),
    )
    return cursor.fetchall()


def get_by_id(
    connection: sqlite3.Connection,
    report_id: int,
) -> sqlite3.Row | None:
    """Return a report by identifier, or None when it does not exist."""
    cursor = connection.execute(
        "SELECT id, project_id, title, content_markdown, created_at, modified_at "
        "FROM reports WHERE id = ?",
        (report_id,),
    )
    return cursor.fetchone()
