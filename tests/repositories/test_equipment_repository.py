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
from app.repositories.experiment_repository import create as create_experiment


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
        assert row is not None
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
        equipment_id = create(connection, name="Find me")

        # when
        row = get_by_id(connection, equipment_id)

        # then
        assert row is not None
        assert row["name"] == "Find me"

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
        assert row is not None
        assert row["name"] == "New Name"

    def test_updates_description(self, connection: sqlite3.Connection) -> None:
        # given
        equipment_id = create(connection, name="Balance", description="Old")

        # when
        row = update(connection, equipment_id, description="Updated description")

        # then
        assert row is not None
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
        assert row is not None
        assert row["name"] == "Updated Name"
        assert row["description"] == "New desc"

    def test_ignores_unknown_fields(self, connection: sqlite3.Connection) -> None:
        # given
        equipment_id = create(connection, name="Stable")

        # when
        row = update(connection, equipment_id, name="Still Stable", nonexistent="boom")

        # then
        assert row is not None
        assert row["name"] == "Still Stable"

    def test_keeps_other_fields_unchanged_when_updating_name(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        equipment_id = create(connection, name="Original", description="Keep me")

        # when
        row = update(connection, equipment_id, name="Updated")

        # then
        assert row is not None
        assert row["name"] == "Updated"
        assert row["description"] == "Keep me"

    def test_noop_when_no_valid_fields(self, connection: sqlite3.Connection) -> None:
        # given
        equipment_id = create(connection, name="No Change")

        # when
        row = update(connection, equipment_id)

        # then
        assert row is not None
        assert row["name"] == "No Change"


class TestLinkToExperiment:
    def test_links_equipment_to_experiment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Synthesis")
        equipment_id = create(connection, name="Stirrer")

        # when
        link_to_experiment(connection, experiment_id, equipment_id)

        # then
        row = connection.execute(
            "SELECT experiment_id, equipment_id FROM experiment_equipment",
        ).fetchone()
        assert row is not None
        assert row["experiment_id"] == experiment_id
        assert row["equipment_id"] == equipment_id

    def test_links_same_equipment_to_multiple_experiments(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_a = _insert_experiment(connection, title="Exp A")
        experiment_b = _insert_experiment(connection, title="Exp B")
        equipment_id = create(connection, name="Oven")

        # when
        link_to_experiment(connection, experiment_a, equipment_id)
        link_to_experiment(connection, experiment_b, equipment_id)

        # then
        rows = connection.execute(
            "SELECT experiment_id FROM experiment_equipment"
        ).fetchall()
        assert len(rows) == 2


class TestGetByExperiment:
    def test_returns_linked_equipment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Synthesis")
        equipment_a = create(connection, name="Balance")
        equipment_b = create(connection, name="Stirrer")
        link_to_experiment(connection, experiment_id, equipment_a)
        link_to_experiment(connection, experiment_id, equipment_b)

        # when
        rows = get_by_experiment(connection, experiment_id)

        # then
        assert len(rows) == 2
        assert {row["name"] for row in rows} == {"Balance", "Stirrer"}

    def test_returns_empty_list_when_no_equipment_linked(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="No Equipment")

        # when
        rows = get_by_experiment(connection, experiment_id)

        # then
        assert len(rows) == 0