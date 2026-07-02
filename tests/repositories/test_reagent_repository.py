import sqlite3
from datetime import date

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.reagent_repository import (
    create,
    get_all,
    get_by_experiment,
    get_by_id,
    get_experiment_history,
    link_to_experiment,
    update,
)


@pytest.fixture(name="connection")
def connection_fixture() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    conn.execute("INSERT INTO projects (id, name) VALUES (1, 'Test Project')")
    conn.execute(
        "INSERT INTO experiments (id, project_id, title) VALUES (1, 1, 'Exp A')"
    )
    conn.execute(
        "INSERT INTO experiments (id, project_id, title) VALUES (2, 1, 'Exp B')"
    )
    conn.commit()
    yield conn
    close_connection(conn)


class TestCreate:
    def test_creates_reagent_and_returns_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        reagent_id = create(connection, name="Acetone")

        # then
        row = connection.execute(
            "SELECT id, name, in_stock FROM reagents WHERE id = ?",
            (reagent_id,),
        ).fetchone()
        assert row["name"] == "Acetone"
        assert row["in_stock"] == 1

    def test_creates_reagent_with_all_fields(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        reagent_id = create(
            connection,
            name="Sulfuric Acid",
            cas_number="7664-93-9",
            smiles="OS(=O)(=O)O",
            in_stock=True,
            lot_number="LOT-001",
            supplier="Sigma-Aldrich",
            expiry_date=date(2026, 12, 31),
            state="Liquid",
            purity=0.98,
            is_corrosive=True,
            is_acute_toxic=True,
        )

        # then
        row = get_by_id(connection, reagent_id)
        assert row is not None
        assert row["name"] == "Sulfuric Acid"
        assert row["cas_number"] == "7664-93-9"
        assert row["smiles"] == "OS(=O)(=O)O"
        assert row["in_stock"] == 1
        assert row["lot_number"] == "LOT-001"
        assert row["supplier"] == "Sigma-Aldrich"
        assert row["expiry_date"] == "2026-12-31"
        assert row["state"] == "Liquid"
        assert row["purity"] == 0.98
        assert row["is_corrosive"] == 1
        assert row["is_acute_toxic"] == 1
        assert row["is_explosive"] == 0

    def test_creates_reagent_out_of_stock(self, connection: sqlite3.Connection) -> None:
        # given / when
        reagent_id = create(connection, name="Used Up", in_stock=False)

        # then
        row = get_by_id(connection, reagent_id)
        assert row["in_stock"] == 0

    def test_creates_reagent_with_ghs_flags(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        reagent_id = create(
            connection,
            name="Hazardous Mix",
            is_explosive=True,
            is_flammable=True,
            is_oxidizer=True,
            is_gas_under_pressure=True,
            is_harmful_irritant=True,
            is_health_hazard=True,
            is_environmental_hazard=True,
        )

        # then
        row = get_by_id(connection, reagent_id)
        assert row["is_explosive"] == 1
        assert row["is_flammable"] == 1
        assert row["is_oxidizer"] == 1
        assert row["is_gas_under_pressure"] == 1
        assert row["is_harmful_irritant"] == 1
        assert row["is_health_hazard"] == 1
        assert row["is_environmental_hazard"] == 1


class TestGetById:
    def test_returns_row_for_existing_reagent(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="Ethanol")

        # when
        row = get_by_id(connection, reagent_id)

        # then
        assert row is not None
        assert row["name"] == "Ethanol"

    def test_returns_none_when_reagent_does_not_exist(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        row = get_by_id(connection, 999)

        # then
        assert row is None


class TestGetAll:
    def test_returns_all_reagents_ordered_by_id_desc(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        id_a = create(connection, name="Alpha")
        id_b = create(connection, name="Beta")

        # when
        rows = get_all(connection)

        # then
        assert len(rows) == 2
        assert rows[0]["id"] == id_b
        assert rows[1]["id"] == id_a

    def test_returns_empty_list_when_no_reagents(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        rows = get_all(connection)

        # then
        assert len(rows) == 0


class TestUpdate:
    def test_updates_name(self, connection: sqlite3.Connection) -> None:
        # given
        reagent_id = create(connection, name="Old Name")

        # when
        row = update(connection, reagent_id, name="New Name")

        # then
        assert row["name"] == "New Name"

    def test_updates_multiple_fields(self, connection: sqlite3.Connection) -> None:
        # given
        reagent_id = create(connection, name="Reagent", supplier="Old Supplier")

        # when
        row = update(
            connection,
            reagent_id,
            supplier="New Supplier",
            in_stock=False,
        )

        # then
        assert row["supplier"] == "New Supplier"
        assert row["in_stock"] == 0

    def test_ignores_unknown_fields(self, connection: sqlite3.Connection) -> None:
        # given
        reagent_id = create(connection, name="Stable")

        # when
        row = update(connection, reagent_id, name="Still Stable", nonexistent="boom")

        # then
        assert row["name"] == "Still Stable"

    def test_keeps_other_fields_unchanged_when_updating_name(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="Original", supplier="Original Supplier")

        # when
        row = update(connection, reagent_id, name="Updated")

        # then
        assert row["name"] == "Updated"
        assert row["supplier"] == "Original Supplier"

    def test_noop_when_no_valid_fields(self, connection: sqlite3.Connection) -> None:
        # given
        reagent_id = create(connection, name="No Change")

        # when
        row = update(connection, reagent_id)

        # then
        assert row["name"] == "No Change"


class TestLinkToExperiment:
    def test_links_reagent_to_experiment(self, connection: sqlite3.Connection) -> None:
        # given
        reagent_id = create(connection, name="NaOH")

        # when
        link_to_experiment(
            connection, experiment_id=1, reagent_id=reagent_id, amount=5.0, unit="mL"
        )

        # then
        row = connection.execute(
            "SELECT experiment_id, reagent_id, amount_used, unit "
            "FROM experiment_reagents WHERE experiment_id = 1 AND reagent_id = ?",
            (reagent_id,),
        ).fetchone()
        assert row is not None
        assert row["amount_used"] == 5.0
        assert row["unit"] == "mL"

    def test_replaces_existing_link_on_duplicate(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="HCl")
        link_to_experiment(
            connection, experiment_id=1, reagent_id=reagent_id, amount=2.0, unit="L"
        )

        # when
        link_to_experiment(
            connection, experiment_id=1, reagent_id=reagent_id, amount=3.5, unit="L"
        )

        # then
        row = connection.execute(
            "SELECT amount_used FROM experiment_reagents "
            "WHERE experiment_id = 1 AND reagent_id = ?",
            (reagent_id,),
        ).fetchone()
        assert row["amount_used"] == 3.5


class TestGetByExperiment:
    def test_returns_reagents_linked_to_experiment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        r1 = create(connection, name="Reagent A")
        r2 = create(connection, name="Reagent B")
        link_to_experiment(
            connection, experiment_id=1, reagent_id=r1, amount=1.0, unit="g"
        )
        link_to_experiment(
            connection, experiment_id=1, reagent_id=r2, amount=2.0, unit="mL"
        )

        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 2
        names = [r["name"] for r in rows]
        assert "Reagent A" in names
        assert "Reagent B" in names
        assert rows[0]["amount_used"] == 1.0 or rows[0]["amount_used"] == 2.0

    def test_returns_empty_list_when_no_reagents_linked(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 0

    def test_does_not_return_reagents_from_other_experiments(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="Only in Exp B")
        link_to_experiment(
            connection, experiment_id=2, reagent_id=reagent_id, amount=1.0, unit="g"
        )

        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 0


class TestGetExperimentHistory:
    def test_returns_experiments_where_reagent_was_used(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="Shared Reagent")
        link_to_experiment(
            connection, experiment_id=1, reagent_id=reagent_id, amount=1.0, unit="g"
        )
        link_to_experiment(
            connection, experiment_id=2, reagent_id=reagent_id, amount=2.5, unit="g"
        )

        # when
        rows = get_experiment_history(connection, reagent_id)

        # then
        assert len(rows) == 2
        titles = [r["title"] for r in rows]
        assert "Exp A" in titles
        assert "Exp B" in titles

    def test_returns_experiment_with_amount_and_unit(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="Measured")
        link_to_experiment(
            connection, experiment_id=1, reagent_id=reagent_id, amount=10.0, unit="mg"
        )

        # when
        rows = get_experiment_history(connection, reagent_id)

        # then
        assert len(rows) == 1
        assert rows[0]["amount_used"] == 10.0
        assert rows[0]["unit"] == "mg"
        assert rows[0]["title"] == "Exp A"

    def test_returns_empty_list_when_reagent_never_used(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="Unused Reagent")

        # when
        rows = get_experiment_history(connection, reagent_id)

        # then
        assert len(rows) == 0
