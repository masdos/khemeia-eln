import sqlite3

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.equipment_repository import (
    create,
    get_all,
    get_by_experiment,
    get_by_id,
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
    def test_creates_equipment_and_returns_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        equipment_id = create(connection, name="Rotary Evaporator")

        # then
        row = connection.execute(
            "SELECT id, name, description FROM equipment WHERE id = ?",
            (equipment_id,),
        ).fetchone()
        assert row["name"] == "Rotary Evaporator"
        assert row["description"] == ""

    def test_creates_equipment_with_description(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        equipment_id = create(
            connection,
            name="Analytical Balance",
            description="Precision 0.1 mg",
        )

        # then
        row = get_by_id(connection, equipment_id)
        assert row is not None
        assert row["name"] == "Analytical Balance"
        assert row["description"] == "Precision 0.1 mg"


class TestGetById:
    def test_returns_row_for_existing_equipment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        equipment_id = create(connection, name="Centrifuge")

        # when
        row = get_by_id(connection, equipment_id)

        # then
        assert row is not None
        assert row["name"] == "Centrifuge"

    def test_returns_none_when_equipment_does_not_exist(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        row = get_by_id(connection, 999)

        # then
        assert row is None


class TestGetAll:
    def test_returns_all_equipment_ordered_by_id_desc(
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

    def test_returns_empty_list_when_no_equipment(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        rows = get_all(connection)

        # then
        assert len(rows) == 0


class TestUpdate:
    def test_updates_name(self, connection: sqlite3.Connection) -> None:
        # given
        equipment_id = create(connection, name="Old Name")

        # when
        row = update(connection, equipment_id, name="New Name")

        # then
        assert row["name"] == "New Name"

    def test_updates_description(self, connection: sqlite3.Connection) -> None:
        # given
        equipment_id = create(connection, name="Device", description="Old")

        # when
        row = update(connection, equipment_id, description="Updated description")

        # then
        assert row["description"] == "Updated description"

    def test_updates_multiple_fields(self, connection: sqlite3.Connection) -> None:
        # given
        equipment_id = create(connection, name="Original", description="Old desc")

        # when
        row = update(
            connection,
            equipment_id,
            name="Updated Name",
            description="New desc",
        )

        # then
        assert row["name"] == "Updated Name"
        assert row["description"] == "New desc"

    def test_ignores_unknown_fields(self, connection: sqlite3.Connection) -> None:
        # given
        equipment_id = create(connection, name="Stable")

        # when
        row = update(connection, equipment_id, name="Still Stable", nonexistent="boom")

        # then
        assert row["name"] == "Still Stable"

    def test_keeps_other_fields_unchanged_when_updating_name(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        equipment_id = create(connection, name="Original", description="Keep me")

        # when
        row = update(connection, equipment_id, name="Updated")

        # then
        assert row["name"] == "Updated"
        assert row["description"] == "Keep me"

    def test_noop_when_no_valid_fields(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        equipment_id = create(connection, name="No Change")

        # when
        row = update(connection, equipment_id)

        # then
        assert row["name"] == "No Change"


class TestLinkToExperiment:
    def test_links_equipment_to_experiment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        equipment_id = create(connection, name="Hot Plate")

        # when
        link_to_experiment(connection, experiment_id=1, equipment_id=equipment_id)

        # then
        row = connection.execute(
            "SELECT experiment_id, equipment_id "
            "FROM experiment_equipment "
            "WHERE experiment_id = 1 AND equipment_id = ?",
            (equipment_id,),
        ).fetchone()
        assert row is not None

    def test_replaces_existing_link_on_duplicate(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        equipment_id = create(connection, name="PH Meter")
        link_to_experiment(connection, experiment_id=1, equipment_id=equipment_id)

        # when
        link_to_experiment(connection, experiment_id=1, equipment_id=equipment_id)

        # then
        cursor = connection.execute(
            "SELECT COUNT(*) AS cnt FROM experiment_equipment "
            "WHERE experiment_id = 1 AND equipment_id = ?",
            (equipment_id,),
        )
        assert cursor.fetchone()["cnt"] == 1


class TestGetByExperiment:
    def test_returns_equipment_linked_to_experiment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        e1 = create(connection, name="Equipment A")
        e2 = create(connection, name="Equipment B")
        link_to_experiment(connection, experiment_id=1, equipment_id=e1)
        link_to_experiment(connection, experiment_id=1, equipment_id=e2)

        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 2
        names = [r["name"] for r in rows]
        assert "Equipment A" in names
        assert "Equipment B" in names

    def test_returns_empty_list_when_no_equipment_linked(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 0

    def test_does_not_return_equipment_from_other_experiments(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        equipment_id = create(connection, name="Only in Exp B")
        link_to_experiment(connection, experiment_id=2, equipment_id=equipment_id)

        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 0
