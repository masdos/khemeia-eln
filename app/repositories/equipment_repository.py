import sqlite3
from collections.abc import Sequence


class EquipmentHasExperimentsError(ValueError):
    """Raised when trying to delete equipment that is used in experiments."""


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


def unlink_from_experiment(
    connection: sqlite3.Connection,
    experiment_id: int,
    equipment_id: int,
) -> None:
    connection.execute(
        "DELETE FROM experiment_equipment WHERE experiment_id = ? AND equipment_id = ?",
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


def get_experiment_history(
    connection: sqlite3.Connection,
    equipment_id: int,
) -> Sequence[sqlite3.Row]:
    cursor = connection.execute(
        "SELECT e.id, e.title, e.state, e.created_at "
        "FROM experiment_equipment ee "
        "JOIN experiments e ON e.id = ee.experiment_id "
        "WHERE ee.equipment_id = ? "
        "ORDER BY e.created_at DESC",
        (equipment_id,),
    )
    return cursor.fetchall()


def delete(connection: sqlite3.Connection, equipment_id: int) -> None:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM experiment_equipment WHERE equipment_id = ?",
        (equipment_id,),
    ).fetchone()
    if row["count"] > 0:
        raise EquipmentHasExperimentsError(
            "Equipment cannot be deleted while experiments reference it"
        )

    connection.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
    connection.commit()
