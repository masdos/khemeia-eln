import sqlite3
from collections.abc import Sequence

VALID_STATES = {"Running", "Success", "Fail"}


class ExperimentReferenceNotFoundError(ValueError):
    """Raised when creating an experiment referencing a missing project or protocol."""


class InvalidExperimentStateError(ValueError):
    """Raised when setting an experiment state outside Running, Success, Fail."""


def create(
    connection: sqlite3.Connection,
    project_id: int,
    protocol_id: int,
    title: str,
    state: str = "Running",
    reaction_onset: str | None = None,
    workup: str | None = None,
    purification: str | None = None,
    notes: str | None = None,
) -> int:
    _require_valid_state(state)
    _require_existing_references(connection, project_id, protocol_id)

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
    project_id: int | None = None,
    search_text: str | None = None,
) -> Sequence[sqlite3.Row]:
    query = "SELECT * FROM experiments WHERE 1=1"
    params: list = []

    if state is not None:
        query += " AND state = ?"
        params.append(state)

    if project_id is not None:
        query += " AND project_id = ?"
        params.append(project_id)

    if search_text is not None and search_text.strip():
        term = f"%{search_text.strip()}%"
        query += " AND (title LIKE ? OR notes LIKE ?)"
        params.extend([term, term])

    query += " ORDER BY id DESC"
    cursor = connection.execute(query, params)
    return cursor.fetchall()


def update(
    connection: sqlite3.Connection,
    experiment_id: int,
    **fields: object,
) -> sqlite3.Row | None:
    if "state" in fields:
        _require_valid_state(fields["state"])

    allowed = {
        "title",
        "state",
        "reaction_onset",
        "workup",
        "purification",
        "notes",
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


def _require_valid_state(state: object) -> None:
    if state not in VALID_STATES:
        raise InvalidExperimentStateError(
            f"Experiment state must be one of {sorted(VALID_STATES)}"
        )


def _require_existing_references(
    connection: sqlite3.Connection, project_id: int, protocol_id: int
) -> None:
    project = connection.execute(
        "SELECT 1 FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    if project is None:
        raise ExperimentReferenceNotFoundError(
            f"Project with id {project_id} does not exist"
        )

    protocol = connection.execute(
        "SELECT 1 FROM protocols WHERE id = ?", (protocol_id,)
    ).fetchone()
    if protocol is None:
        raise ExperimentReferenceNotFoundError(
            f"Protocol with id {protocol_id} does not exist"
        )
