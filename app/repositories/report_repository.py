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
        "SELECT r.*, p.name AS project_name "
        "FROM reports r LEFT JOIN projects p ON p.id = r.project_id "
        "WHERE r.id = ?",
        (report_id,),
    )
    return cursor.fetchone()


def get_all(
    connection: sqlite3.Connection,
    project_id: int | None = None,
    search_text: str | None = None,
) -> Sequence[sqlite3.Row]:
    """Return reports with project names, optionally filtered."""
    query = (
        "SELECT r.*, p.name AS project_name "
        "FROM reports r LEFT JOIN projects p ON p.id = r.project_id "
        "WHERE 1=1"
    )
    params: list = []

    if project_id is not None:
        query += " AND r.project_id = ?"
        params.append(project_id)

    if search_text is not None and search_text.strip():
        query += " AND r.title LIKE ?"
        params.append(f"%{search_text.strip()}%")

    query += " ORDER BY r.id DESC"
    cursor = connection.execute(query, params)
    return cursor.fetchall()


def update(
    connection: sqlite3.Connection,
    report_id: int,
    **fields: object,
) -> sqlite3.Row | None:
    """Update report fields and return the updated row, or None when missing."""
    allowed = {"title", "content_markdown"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_by_id(connection, report_id)

    set_clause = ", ".join(f"{column} = ?" for column in updates)
    params = list(updates.values())
    params.append(report_id)
    connection.execute(
        f"UPDATE reports SET {set_clause}, modified_at = CURRENT_TIMESTAMP"
        " WHERE id = ?",
        params,
    )
    connection.commit()
    return get_by_id(connection, report_id)


def delete(connection: sqlite3.Connection, report_id: int) -> None:
    """Delete a report; experiment links cascade via foreign keys."""
    connection.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    connection.commit()
