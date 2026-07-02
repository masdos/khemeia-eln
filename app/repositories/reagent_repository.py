import sqlite3
from collections.abc import Sequence
from datetime import date


def create(
    connection: sqlite3.Connection,
    name: str,
    cas_number: str = "",
    smiles: str = "",
    in_stock: bool = True,
    lot_number: str = "",
    supplier: str = "",
    expiry_date: date | None = None,
    state: str = "",
    purity: float | None = None,
    is_explosive: bool = False,
    is_flammable: bool = False,
    is_oxidizer: bool = False,
    is_gas_under_pressure: bool = False,
    is_corrosive: bool = False,
    is_acute_toxic: bool = False,
    is_harmful_irritant: bool = False,
    is_health_hazard: bool = False,
    is_environmental_hazard: bool = False,
) -> int:
    cursor = connection.execute(
        "INSERT INTO reagents "
        "(name, cas_number, smiles, in_stock, lot_number, supplier, "
        "expiry_date, state, purity, "
        "is_explosive, is_flammable, is_oxidizer, "
        "is_gas_under_pressure, is_corrosive, is_acute_toxic, "
        "is_harmful_irritant, is_health_hazard, is_environmental_hazard) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            name,
            cas_number,
            smiles,
            int(in_stock),
            lot_number,
            supplier,
            expiry_date,
            state,
            purity,
            int(is_explosive),
            int(is_flammable),
            int(is_oxidizer),
            int(is_gas_under_pressure),
            int(is_corrosive),
            int(is_acute_toxic),
            int(is_harmful_irritant),
            int(is_health_hazard),
            int(is_environmental_hazard),
        ),
    )
    connection.commit()
    return cursor.lastrowid


def get_by_id(connection: sqlite3.Connection, reagent_id: int) -> sqlite3.Row | None:
    cursor = connection.execute("SELECT * FROM reagents WHERE id = ?", (reagent_id,))
    return cursor.fetchone()


def get_all(connection: sqlite3.Connection) -> Sequence[sqlite3.Row]:
    cursor = connection.execute("SELECT * FROM reagents ORDER BY id DESC")
    return cursor.fetchall()


def update(
    connection: sqlite3.Connection,
    reagent_id: int,
    **fields: object,
) -> sqlite3.Row | None:
    allowed = {
        "name",
        "cas_number",
        "smiles",
        "in_stock",
        "lot_number",
        "supplier",
        "expiry_date",
        "state",
        "purity",
        "is_explosive",
        "is_flammable",
        "is_oxidizer",
        "is_gas_under_pressure",
        "is_corrosive",
        "is_acute_toxic",
        "is_harmful_irritant",
        "is_health_hazard",
        "is_environmental_hazard",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_by_id(connection, reagent_id)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [reagent_id]

    connection.execute(
        f"UPDATE reagents SET {set_clause}, "
        "modified_at = CURRENT_TIMESTAMP WHERE id = ?",
        values,
    )
    connection.commit()
    return get_by_id(connection, reagent_id)


def link_to_experiment(
    connection: sqlite3.Connection,
    experiment_id: int,
    reagent_id: int,
    amount: float,
    unit: str,
) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO experiment_reagents "
        "(experiment_id, reagent_id, amount_used, unit) "
        "VALUES (?, ?, ?, ?)",
        (experiment_id, reagent_id, amount, unit),
    )
    connection.commit()


def get_by_experiment(
    connection: sqlite3.Connection,
    experiment_id: int,
) -> Sequence[sqlite3.Row]:
    cursor = connection.execute(
        "SELECT r.*, er.amount_used, er.unit "
        "FROM experiment_reagents er "
        "JOIN reagents r ON r.id = er.reagent_id "
        "WHERE er.experiment_id = ? "
        "ORDER BY r.name",
        (experiment_id,),
    )
    return cursor.fetchall()


def get_experiment_history(
    connection: sqlite3.Connection,
    reagent_id: int,
) -> Sequence[sqlite3.Row]:
    cursor = connection.execute(
        "SELECT e.id, e.title, e.state, e.created_at, "
        "er.amount_used, er.unit "
        "FROM experiment_reagents er "
        "JOIN experiments e ON e.id = er.experiment_id "
        "WHERE er.reagent_id = ? "
        "ORDER BY e.created_at DESC",
        (reagent_id,),
    )
    return cursor.fetchall()
