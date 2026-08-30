import sqlite3
from collections.abc import Sequence


def create(
    connection: sqlite3.Connection,
    name: str,
    description: str = "",
) -> int:
    cursor = connection.execute(
        "INSERT INTO equipment (name, description) VALUES (?, ?)",
        (name, description),
    )
    connection.commit()
    return cursor.lastrowid


def get_by_id(connection: sqlite3.Connection, equipment_id: int) -> sqlite3.Row | None:
    cursor = connection.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,))
    return cursor.fetchone()


def get_all(connection: sqlite3.Connection) -> Sequence[sqlite3.Row]:
    cursor = connection.execute("SELECT * FROM equipment ORDER BY id DESC")
    return cursor.fetchall()


def update(
    connection: sqlite3.Connection,
    equipment_id: int,
    **fields: object,
) -> sqlite3.Row | None:
    allowed = {"name", "description"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_by_id(connection, equipment_id)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [equipment_id]

    connection.execute(
        f"UPDATE equipment SET {set_clause}, "
        "modified_at = CURRENT_TIMESTAMP WHERE id = ?",
        values,
    )
    connection.commit()
    return get_by_id(connection, equipment_id)


def link_to_experiment(
    connection: sqlite3.Connection,
    experiment_id: int,
    equipment_id: int,
) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO experiment_equipment "
        "(experiment_id, equipment_id) VALUES (?, ?)",
        (experiment_id, equipment_id),
    )
    connection.commit()


def get_by_experiment(
    connection: sqlite3.Connection,
    experiment_id: int,
) -> Sequence[sqlite3.Row]:
    cursor = connection.execute(
        "SELECT e.* "
        "FROM experiment_equipment ee "
        "JOIN equipment e ON e.id = ee.equipment_id "
        "WHERE ee.experiment_id = ? "
        "ORDER BY e.name",
        (experiment_id,),
    )
    return cursor.fetchall()
