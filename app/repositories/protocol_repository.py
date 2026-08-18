import sqlite3
from collections.abc import Sequence


class ProtocolHasExperimentsError(ValueError):
    """Raised when trying to delete a protocol that still has experiments."""


def create(
    connection: sqlite3.Connection,
    name: str,
    content_markdown: str,
) -> int:
    cursor = connection.execute(
        "INSERT INTO protocols (name, content_markdown) VALUES (?, ?)",
        (name, content_markdown),
    )
    connection.commit()
    return cursor.lastrowid


def get_by_id(connection: sqlite3.Connection, protocol_id: int) -> sqlite3.Row | None:
    cursor = connection.execute("SELECT * FROM protocols WHERE id = ?", (protocol_id,))
    return cursor.fetchone()


def get_all(
    connection: sqlite3.Connection,
    search_text: str | None = None,
) -> Sequence[sqlite3.Row]:
    query = "SELECT * FROM protocols WHERE 1=1"
    params: list = []

    if search_text is not None and search_text.strip():
        term = f"%{search_text.strip()}%"
        query += " AND (name LIKE ? OR content_markdown LIKE ?)"
        params.extend([term, term])

    query += " ORDER BY id DESC"
    cursor = connection.execute(query, params)
    return cursor.fetchall()


def update(
    connection: sqlite3.Connection,
    protocol_id: int,
    **fields: object,
) -> sqlite3.Row | None:
    allowed = {"name", "content_markdown"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_by_id(connection, protocol_id)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [protocol_id]

    connection.execute(
        f"UPDATE protocols SET {set_clause}, "
        "modified_at = CURRENT_TIMESTAMP WHERE id = ?",
        values,
    )
    connection.commit()
    return get_by_id(connection, protocol_id)


def delete(connection: sqlite3.Connection, protocol_id: int) -> None:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM experiments WHERE protocol_id = ?",
        (protocol_id,),
    ).fetchone()
    if row["count"] > 0:
        raise ProtocolHasExperimentsError(
            "Protocol cannot be deleted while experiments reference it"
        )

    connection.execute("DELETE FROM protocols WHERE id = ?", (protocol_id,))
    connection.commit()
