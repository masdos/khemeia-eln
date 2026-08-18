import sqlite3

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.experiment_repository import create as create_experiment
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
    yield conn
    close_connection(conn)


def _insert_project(connection: sqlite3.Connection, name: str = "Project") -> int:
    cursor = connection.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    connection.commit()
    return cursor.lastrowid


def _insert_protocol(
    connection: sqlite3.Connection, name: str = "Protocol"
) -> int:
    cursor = connection.execute(
        "INSERT INTO protocols (name, content_markdown) VALUES (?, '# Content')",
        (name,),
    )
    connection.commit()
    return cursor.lastrowid


def _insert_experiment(connection: sqlite3.Connection, title: str) -> int:
    project_id = _insert_project(connection)
    protocol_id = _insert_protocol(connection)
    return create_experiment(
        connection,
        project_id=project_id,
        protocol_id=protocol_id,
        title=title,
    )


class TestCreate:
    def test_creates_reagent_and_returns_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        reagent_id = create(connection, name="Sodium Chloride")

        # then
        row = connection.execute(
            "SELECT id, name, in_stock FROM reagents WHERE id = ?", (reagent_id,)
        ).fetchone()
        assert row is not None
        assert row["name"] == "Sodium Chloride"
        assert row["in_stock"] == 1

    def test_creates_reagent_with_all_fields(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        reagent_id = create(
            connection,
            name="Acetone",
            cas_number="67-64-1",
            smiles="CC(=O)C",
            in_stock=False,
            lot_number="LOT-42",
            supplier="Sigma-Aldrich",
            expiry_date="2026-12-31",
            state="liquid",
            purity=99.8,
        )

        # then
        row = get_by_id(connection, reagent_id)
        assert row is not None
        assert row["cas_number"] == "67-64-1"
        assert row["smiles"] == "CC(=O)C"
        assert row["in_stock"] == 0
        assert row["lot_number"] == "LOT-42"
        assert row["supplier"] == "Sigma-Aldrich"
        assert row["expiry_date"] == "2026-12-31"
        assert row["state"] == "liquid"
        assert row["purity"] == 99.8

    def test_creates_reagent_with_ghs_flags(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        reagent_id = create(
            connection,
            name="Diethyl Ether",
            is_flammable=True,
            is_environmental_hazard=True,
        )

        # then
        row = get_by_id(connection, reagent_id)
        assert row is not None
        assert row["is_flammable"] == 1
        assert row["is_environmental_hazard"] == 1
        assert row["is_explosive"] == 0


class TestGetById:
    def test_returns_row_for_existing_reagent(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="Find me")

        # when
        row = get_by_id(connection, reagent_id)

        # then
        assert row is not None
        assert row["name"] == "Find me"

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
        assert row is not None
        assert row["name"] == "New Name"

    def test_updates_stock_and_state(self, connection: sqlite3.Connection) -> None:
        # given
        reagent_id = create(connection, name="Reagent")

        # when
        row = update(connection, reagent_id, in_stock=False, state="gas")

        # then
        assert row is not None
        assert row["in_stock"] == 0
        assert row["state"] == "gas"

    def test_ignores_unknown_fields(self, connection: sqlite3.Connection) -> None:
        # given
        reagent_id = create(connection, name="Stable")

        # when
        row = update(connection, reagent_id, name="Still Stable", nonexistent="boom")

        # then
        assert row is not None
        assert row["name"] == "Still Stable"

    def test_keeps_other_fields_unchanged_when_updating_name(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="Original", cas_number="50-00-0")

        # when
        row = update(connection, reagent_id, name="Updated")

        # then
        assert row is not None
        assert row["name"] == "Updated"
        assert row["cas_number"] == "50-00-0"

    def test_noop_when_no_valid_fields(self, connection: sqlite3.Connection) -> None:
        # given
        reagent_id = create(connection, name="No Change")

        # when
        row = update(connection, reagent_id)

        # then
        assert row is not None
        assert row["name"] == "No Change"


class TestLinkToExperiment:
    def test_links_reagent_to_experiment_with_amount(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Synthesis")
        reagent_id = create(connection, name="Ethanol")

        # when
        link_to_experiment(
            connection, experiment_id, reagent_id, amount=50.0, unit="mL"
        )

        # then
        row = connection.execute(
            "SELECT experiment_id, reagent_id, amount_used, unit "
            "FROM experiment_reagents",
        ).fetchone()
        assert row is not None
        assert row["experiment_id"] == experiment_id
        assert row["reagent_id"] == reagent_id
        assert row["amount_used"] == 50.0
        assert row["unit"] == "mL"

    def test_links_same_reagent_to_multiple_experiments(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_a = _insert_experiment(connection, title="Exp A")
        experiment_b = _insert_experiment(connection, title="Exp B")
        reagent_id = create(connection, name="Methanol")

        # when
        link_to_experiment(connection, experiment_a, reagent_id, amount=10.0, unit="mL")
        link_to_experiment(connection, experiment_b, reagent_id, amount=20.0, unit="mL")

        # then
        rows = connection.execute(
            "SELECT experiment_id FROM experiment_reagents"
        ).fetchall()
        assert len(rows) == 2

    def test_relinking_replaces_amount_and_unit(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Synthesis")
        reagent_id = create(connection, name="Ethanol")
        link_to_experiment(
            connection, experiment_id, reagent_id, amount=50.0, unit="mL"
        )

        # when
        link_to_experiment(connection, experiment_id, reagent_id, amount=75.0, unit="L")

        # then
        row = connection.execute(
            "SELECT amount_used, unit FROM experiment_reagents",
        ).fetchone()
        assert row is not None
        assert row["amount_used"] == 75.0
        assert row["unit"] == "L"


class TestGetByExperiment:
    def test_returns_linked_reagents_with_amount_and_unit(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Synthesis")
        reagent_a = create(connection, name="Ethanol")
        reagent_b = create(connection, name="Acetone")
        link_to_experiment(connection, experiment_id, reagent_a, amount=10.0, unit="mL")
        link_to_experiment(connection, experiment_id, reagent_b, amount=5.0, unit="g")

        # when
        rows = get_by_experiment(connection, experiment_id)

        # then
        assert len(rows) == 2
        assert {row["name"] for row in rows} == {"Ethanol", "Acetone"}
        assert {row["amount_used"] for row in rows} == {10.0, 5.0}

    def test_returns_empty_list_when_no_reagents_linked(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="No Reagents")

        # when
        rows = get_by_experiment(connection, experiment_id)

        # then
        assert len(rows) == 0


class TestGetExperimentHistory:
    def test_returns_experiments_where_reagent_was_used(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_a = _insert_experiment(connection, title="Exp A")
        experiment_b = _insert_experiment(connection, title="Exp B")
        reagent_id = create(connection, name="Sodium Hydroxide")
        link_to_experiment(connection, experiment_a, reagent_id, amount=2.0, unit="g")
        link_to_experiment(connection, experiment_b, reagent_id, amount=3.0, unit="g")

        # when
        rows = get_experiment_history(connection, reagent_id)

        # then
        assert len(rows) == 2
        assert {row["title"] for row in rows} == {"Exp A", "Exp B"}
        assert {row["amount_used"] for row in rows} == {2.0, 3.0}

    def test_returns_empty_list_when_reagent_never_used(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        reagent_id = create(connection, name="Unused")

        # when
        rows = get_experiment_history(connection, reagent_id)

        # then
        assert len(rows) == 0

    def test_does_not_include_experiments_using_other_reagents(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Exp A")
        reagent_a = create(connection, name="Reagent A")
        reagent_b = create(connection, name="Reagent B")
        link_to_experiment(connection, experiment_id, reagent_a, amount=1.0, unit="g")
        link_to_experiment(connection, experiment_id, reagent_b, amount=2.0, unit="g")

        # when
        rows = get_experiment_history(connection, reagent_a)

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "Exp A"
