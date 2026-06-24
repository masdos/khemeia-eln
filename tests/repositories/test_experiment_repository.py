import sqlite3

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.experiment_repository import (
    create,
    get_all,
    get_by_id,
    update,
)


@pytest.fixture(name="connection")
def connection_fixture() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    conn.execute("INSERT INTO projects (id, name) VALUES (1, 'Test Project')")
    conn.commit()
    yield conn
    close_connection(conn)


class TestCreate:
    def test_creates_experiment_and_returns_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        experiment_id = create(
            connection,
            project_id=1,
            title="Synthesis of Compound X",
        )

        # then
        row = connection.execute(
            "SELECT id, project_id, title, state FROM experiments WHERE id = ?",
            (experiment_id,),
        ).fetchone()
        assert row["title"] == "Synthesis of Compound X"
        assert row["state"] == "Running"

    def test_creates_experiment_with_all_fields(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        experiment_id = create(
            connection,
            project_id=1,
            title="Test",
            state="Success",
            reaction_onset="Exothermic",
            workup="Filtration",
            purification="Recrystallization",
            notes="Keep records",
        )

        # then
        row = get_by_id(connection, experiment_id)
        assert row is not None
        assert row["state"] == "Success"
        assert row["reaction_onset"] == "Exothermic"
        assert row["workup"] == "Filtration"
        assert row["purification"] == "Recrystallization"
        assert row["notes"] == "Keep records"


class TestGetById:
    def test_returns_row_for_existing_experiment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = create(connection, project_id=1, title="Find me")

        # when
        row = get_by_id(connection, experiment_id)

        # then
        assert row is not None
        assert row["title"] == "Find me"

    def test_returns_none_when_experiment_does_not_exist(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        row = get_by_id(connection, 999)

        # then
        assert row is None


class TestGetAll:
    def test_returns_all_experiments_ordered_by_id_desc(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, project_id=1, title="Alpha")
        create(connection, project_id=1, title="Beta")

        # when
        rows = get_all(connection)

        # then
        assert len(rows) == 2
        assert rows[0]["title"] == "Beta"
        assert rows[1]["title"] == "Alpha"

    def test_filters_by_state(self, connection: sqlite3.Connection) -> None:
        # given
        create(connection, project_id=1, title="Running Exp", state="Running")
        create(connection, project_id=1, title="Success Exp", state="Success")
        create(connection, project_id=1, title="Fail Exp", state="Fail")

        # when
        rows = get_all(connection, state="Success")

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "Success Exp"

    def test_filters_by_search_text_in_title(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, project_id=1, title="Synthesis of Aspirin")
        create(connection, project_id=1, title="Purification of Water")

        # when
        rows = get_all(connection, search_text="Aspirin")

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "Synthesis of Aspirin"

    def test_filters_by_search_text_in_notes(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, project_id=1, title="Exp A", notes="Handle with care")
        create(connection, project_id=1, title="Exp B", notes="No special care needed")

        # when
        rows = get_all(connection, search_text="Handle")

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "Exp A"

    def test_returns_empty_list_when_no_match(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, project_id=1, title="Something")

        # when
        rows = get_all(connection, state="Fail")

        # then
        assert len(rows) == 0

    def test_ignores_whitespace_only_search_text(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, project_id=1, title="All experiments")

        # when
        rows = get_all(connection, search_text="   ")

        # then
        assert len(rows) == 1


class TestUpdate:
    def test_updates_title(self, connection: sqlite3.Connection) -> None:
        # given
        experiment_id = create(connection, project_id=1, title="Old Title")

        # when
        row = update(connection, experiment_id, title="New Title")

        # then
        assert row is not None
        assert row["title"] == "New Title"

    def test_updates_state(self, connection: sqlite3.Connection) -> None:
        # given
        experiment_id = create(
            connection, project_id=1, title="Lockable", state="Running"
        )

        # when
        row = update(connection, experiment_id, state="Success", is_locked=1)

        # then
        assert row["state"] == "Success"
        assert row["is_locked"] == 1

    def test_ignores_unknown_fields(self, connection: sqlite3.Connection) -> None:
        # given
        experiment_id = create(connection, project_id=1, title="Stable")

        # when
        row = update(
            connection, experiment_id, title="Still Stable", nonexistent_field="boom"
        )

        # then
        assert row["title"] == "Still Stable"

    def test_keeps_other_fields_unchanged_when_updating_title(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = create(
            connection, project_id=1, title="Original", notes="Initial notes"
        )

        # when
        row = update(connection, experiment_id, title="Updated")

        # then
        assert row["title"] == "Updated"
        assert row["notes"] == "Initial notes"
        assert row["project_id"] == 1
