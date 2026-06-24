import sqlite3
from collections.abc import Sequence


def create(
    connection: sqlite3.Connection,
    project_id: int,
    title: str,
    protocol_id: int | None = None,
    state: str = "Running",
    reaction_onset: str = "",
    workup: str = "",
    purification: str = "",
    notes: str = "",
) -> int:
    cursor = connection.execute(
        "INSERT INTO experiments "
        "(project_id, protocol_id, title, state, "
        "reaction_onset, workup, purification, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            project_id,
            protocol_id,
            title,
            state,
            reaction_onset,
            workup,
            purification,
            notes,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def get_by_id(connection: sqlite3.Connection, experiment_id: int) -> sqlite3.Row | None:
    cursor = connection.execute(
        "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
    )
    return cursor.fetchone()


def get_all(
    connection: sqlite3.Connection,
    state: str | None = None,
    search_text: str | None = None,
) -> Sequence[sqlite3.Row]:
    query = "SELECT * FROM experiments WHERE 1=1"
    params: list = []

    if state is not None:
        query += " AND state = ?"
        params.append(state)

    if search_text is not None and search_text.strip():
        query += " AND (title LIKE ? OR notes LIKE ?)"
        like_pattern = f"%{search_text.strip()}%"
        params.extend([like_pattern, like_pattern])

    query += " ORDER BY id DESC"
    cursor = connection.execute(query, params)
    return cursor.fetchall()


def update(
    connection: sqlite3.Connection,
    experiment_id: int,
    **fields: object,
) -> sqlite3.Row | None:
    allowed = {
        "project_id",
        "protocol_id",
        "title",
        "state",
        "reaction_onset",
        "workup",
        "purification",
        "notes",
        "hash_sha256",
        "is_locked",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_by_id(connection, experiment_id)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [experiment_id]

    connection.execute(
        f"UPDATE experiments SET {set_clause}, "
        "modified_at = CURRENT_TIMESTAMP WHERE id = ?",
        values,
    )
    connection.commit()
    return get_by_id(connection, experiment_id)
