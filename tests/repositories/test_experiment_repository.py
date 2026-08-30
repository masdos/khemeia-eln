import sqlite3

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.experiment_repository import (
    ExperimentReferenceNotFoundError,
    InvalidExperimentStateError,
    create,
    get_all,
    get_by_id,
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


def _insert_protocol(connection: sqlite3.Connection, name: str = "Protocol") -> int:
    cursor = connection.execute(
        "INSERT INTO protocols (name, content_markdown) VALUES (?, '# Content')",
        (name,),
    )
    connection.commit()
    return cursor.lastrowid


class TestCreate:
    def test_creates_experiment_and_returns_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)

        # when
        experiment_id = create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Synthesis",
        )

        # then
        row = connection.execute(
            "SELECT id, project_id, protocol_id, title, state "
            "FROM experiments WHERE id = ?",
            (experiment_id,),
        ).fetchone()
        assert row is not None
        assert row["project_id"] == project_id
        assert row["protocol_id"] == protocol_id
        assert row["title"] == "Synthesis"
        assert row["state"] == "Running"

    def test_creates_experiment_with_all_optional_fields(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)

        # when
        experiment_id = create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Full Experiment",
            state="Success",
            reaction_onset="Mild exotherm at 60 C",
            workup="Extracted with DCM",
            purification="Column chromatography",
            notes="Yield 85%",
        )

        # then
        row = get_by_id(connection, experiment_id)
        assert row is not None
        assert row["title"] == "Full Experiment"
        assert row["state"] == "Success"
        assert row["reaction_onset"] == "Mild exotherm at 60 C"
        assert row["workup"] == "Extracted with DCM"
        assert row["purification"] == "Column chromatography"
        assert row["notes"] == "Yield 85%"

    def test_rejects_creation_when_project_does_not_exist(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        protocol_id = _insert_protocol(connection)

        # when / then
        with pytest.raises(ExperimentReferenceNotFoundError):
            create(connection, project_id=999, protocol_id=protocol_id, title="Orphan")

    def test_rejects_creation_when_protocol_does_not_exist(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)

        # when / then
        with pytest.raises(ExperimentReferenceNotFoundError):
            create(connection, project_id=project_id, protocol_id=999, title="Orphan")

    def test_rejects_creation_with_invalid_state(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)

        # when / then
        with pytest.raises(InvalidExperimentStateError):
            create(
                connection,
                project_id=project_id,
                protocol_id=protocol_id,
                title="Bad State",
                state="Paused",
            )


class TestGetById:
    def test_returns_row_for_existing_experiment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        experiment_id = create(
            connection, project_id=project_id, protocol_id=protocol_id, title="Find me"
        )

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
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        id_a = create(
            connection, project_id=project_id, protocol_id=protocol_id, title="Alpha"
        )
        id_b = create(
            connection, project_id=project_id, protocol_id=protocol_id, title="Beta"
        )

        # when
        rows = get_all(connection)

        # then
        assert len(rows) == 2
        assert rows[0]["id"] == id_b
        assert rows[1]["id"] == id_a

    def test_returns_empty_list_when_no_experiments(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        rows = get_all(connection)

        # then
        assert len(rows) == 0

    def test_filters_by_state(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Running one",
            state="Running",
        )
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Failed one",
            state="Fail",
        )

        # when
        rows = get_all(connection, state="Running")

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "Running one"

    def test_filters_by_project_id(self, connection: sqlite3.Connection) -> None:
        # given
        project_a = _insert_project(connection, name="Project A")
        project_b = _insert_project(connection, name="Project B")
        protocol_id = _insert_protocol(connection)
        create(connection, project_id=project_a, protocol_id=protocol_id, title="In A")
        create(connection, project_id=project_b, protocol_id=protocol_id, title="In B")

        # when
        rows = get_all(connection, project_id=project_a)

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "In A"

    def test_filters_by_search_text_in_title(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Grignard Reaction",
        )
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Titration",
        )

        # when
        rows = get_all(connection, search_text="Grignard")

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "Grignard Reaction"

    def test_filters_by_search_text_in_notes(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Reaction",
            notes="Obtained a white crystalline solid",
        )
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Other",
            notes="Nothing special",
        )

        # when
        rows = get_all(connection, search_text="crystalline")

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "Reaction"

    def test_search_text_is_case_insensitive(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Grignard Reaction",
        )
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Titration",
        )

        # when
        rows = get_all(connection, search_text="grignard")

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "Grignard Reaction"

    def test_ignores_whitespace_only_search_text(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="All visible",
        )

        # when
        rows = get_all(connection, search_text="   ")

        # then
        assert len(rows) == 1

    def test_returns_empty_list_when_no_text_matches(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Something",
        )

        # when
        rows = get_all(connection, search_text="Nonexistent")

        # then
        assert len(rows) == 0

    def test_combines_state_project_and_text_filters(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_a = _insert_project(connection, name="Project A")
        project_b = _insert_project(connection, name="Project B")
        protocol_id = _insert_protocol(connection)
        create(
            connection,
            project_id=project_a,
            protocol_id=protocol_id,
            title="Grignard Reaction",
            state="Running",
        )
        create(
            connection,
            project_id=project_a,
            protocol_id=protocol_id,
            title="Grignard done",
            state="Success",
        )
        create(
            connection,
            project_id=project_b,
            protocol_id=protocol_id,
            title="Grignard Other",
            state="Running",
        )

        # when
        rows = get_all(
            connection, state="Running", project_id=project_a, search_text="Grignard"
        )

        # then
        assert len(rows) == 1
        assert rows[0]["title"] == "Grignard Reaction"


class TestUpdate:
    def test_updates_title(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        experiment_id = create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Old Title",
        )

        # when
        row = update(connection, experiment_id, title="New Title")

        # then
        assert row is not None
        assert row["title"] == "New Title"

    def test_updates_state(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        experiment_id = create(
            connection, project_id=project_id, protocol_id=protocol_id, title="Reaction"
        )

        # when
        row = update(connection, experiment_id, state="Success")

        # then
        assert row is not None
        assert row["state"] == "Success"

    def test_updates_multiple_fields(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        experiment_id = create(
            connection, project_id=project_id, protocol_id=protocol_id, title="Original"
        )

        # when
        row = update(
            connection,
            experiment_id,
            title="Updated",
            state="Fail",
            notes="Yield 60%",
        )

        # then
        assert row is not None
        assert row["title"] == "Updated"
        assert row["state"] == "Fail"
        assert row["notes"] == "Yield 60%"

    def test_ignores_unknown_fields(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        experiment_id = create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Stable",
        )

        # when
        row = update(
            connection, experiment_id, title="Still Stable", nonexistent="boom"
        )

        # then
        assert row is not None
        assert row["title"] == "Still Stable"

    def test_keeps_other_fields_unchanged_when_updating_title(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        experiment_id = create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="Original",
            notes="Keep me",
        )

        # when
        row = update(connection, experiment_id, title="Updated")

        # then
        assert row is not None
        assert row["title"] == "Updated"
        assert row["notes"] == "Keep me"

    def test_noop_when_no_valid_fields(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        experiment_id = create(
            connection,
            project_id=project_id,
            protocol_id=protocol_id,
            title="No Change",
        )

        # when
        row = update(connection, experiment_id)

        # then
        assert row is not None
        assert row["title"] == "No Change"

    def test_rejects_invalid_state(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = _insert_project(connection)
        protocol_id = _insert_protocol(connection)
        experiment_id = create(
            connection, project_id=project_id, protocol_id=protocol_id, title="Reaction"
        )

        # when / then
        with pytest.raises(InvalidExperimentStateError):
            update(connection, experiment_id, state="Paused")
