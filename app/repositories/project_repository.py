import sqlite3
from collections.abc import Sequence


class ProjectHasExperimentsError(ValueError):
    """Raised when trying to delete a project that still has experiments."""


def create(
    connection: sqlite3.Connection,
    name: str,
    description: str = "",
) -> int:
    cursor = connection.execute(
        "INSERT INTO projects (name, description) VALUES (?, ?)",
        (name, description),
    )
    connection.commit()
    return cursor.lastrowid


def get_by_id(connection: sqlite3.Connection, project_id: int) -> sqlite3.Row | None:
    cursor = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    return cursor.fetchone()


def get_all(
    connection: sqlite3.Connection,
    search_text: str | None = None,
) -> Sequence[sqlite3.Row]:
    query = "SELECT * FROM projects WHERE 1=1"
    params: list = []

    if search_text is not None and search_text.strip():
        query += " AND name LIKE ?"
        params.append(f"%{search_text.strip()}%")

    query += " ORDER BY id DESC"
    cursor = connection.execute(query, params)
    return cursor.fetchall()


def update(
    connection: sqlite3.Connection,
    project_id: int,
    **fields: object,
) -> sqlite3.Row | None:
    allowed = {"name", "description"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_by_id(connection, project_id)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [project_id]

    connection.execute(
        f"UPDATE projects SET {set_clause}, "
        "modified_at = CURRENT_TIMESTAMP WHERE id = ?",
        values,
    )
    connection.commit()
    return get_by_id(connection, project_id)


def delete(connection: sqlite3.Connection, project_id: int) -> None:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM experiments WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    if row["count"] > 0:
        raise ProjectHasExperimentsError(
            "Project cannot be deleted while experiments reference it"
        )

    connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    connection.commit()
