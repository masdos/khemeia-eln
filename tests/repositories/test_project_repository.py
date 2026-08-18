import sqlite3

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.project_repository import (
    ProjectHasExperimentsError,
    create,
    delete,
    get_all,
    get_by_id,
    update,
)


@pytest.fixture(name="connection")
def connection_fixture() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    yield conn
    close_connection(conn)


class TestCreate:
    def test_creates_project_and_returns_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        project_id = create(connection, name="Synthesis of Aspirin")

        # then
        row = connection.execute(
            "SELECT id, name, description FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        assert row is not None
        assert row["name"] == "Synthesis of Aspirin"
        assert row["description"] == ""

    def test_creates_project_with_description(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        project_id = create(
            connection,
            name="Crystal Growth",
            description="Series of crystallisation experiments",
        )

        # then
        row = get_by_id(connection, project_id)
        assert row is not None
        assert row["name"] == "Crystal Growth"
        assert row["description"] == "Series of crystallisation experiments"


class TestGetById:
    def test_returns_row_for_existing_project(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = create(connection, name="Find me")

        # when
        row = get_by_id(connection, project_id)

        # then
        assert row is not None
        assert row["name"] == "Find me"

    def test_returns_none_when_project_does_not_exist(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        row = get_by_id(connection, 999)

        # then
        assert row is None


class TestGetAll:
    def test_returns_all_projects_ordered_by_id_desc(
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

    def test_returns_empty_list_when_no_projects(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        rows = get_all(connection)

        # then
        assert len(rows) == 0

    def test_filters_by_search_text_in_name(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, name="Polymer Synthesis")
        create(connection, name="Water Analysis")

        # when
        rows = get_all(connection, search_text="Polymer")

        # then
        assert len(rows) == 1
        assert rows[0]["name"] == "Polymer Synthesis"

    def test_search_text_is_case_insensitive(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, name="Catalyst Screening")
        create(connection, name="Workup Studies")

        # when
        rows = get_all(connection, search_text="catalyst")

        # then
        assert len(rows) == 1
        assert rows[0]["name"] == "Catalyst Screening"

    def test_ignores_whitespace_only_search_text(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, name="All projects visible")

        # when
        rows = get_all(connection, search_text="   ")

        # then
        assert len(rows) == 1

    def test_returns_empty_list_when_no_name_matches(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, name="Something")

        # when
        rows = get_all(connection, search_text="Nonexistent")

        # then
        assert len(rows) == 0


class TestUpdate:
    def test_updates_name(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = create(connection, name="Old Name")

        # when
        row = update(connection, project_id, name="New Name")

        # then
        assert row is not None
        assert row["name"] == "New Name"

    def test_updates_description(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = create(connection, name="Project", description="Old")

        # when
        row = update(connection, project_id, description="Updated description")

        # then
        assert row is not None
        assert row["description"] == "Updated description"

    def test_updates_multiple_fields(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = create(connection, name="Original", description="Old desc")

        # when
        row = update(
            connection,
            project_id,
            name="Updated Name",
            description="New desc",
        )

        # then
        assert row is not None
        assert row["name"] == "Updated Name"
        assert row["description"] == "New desc"

    def test_ignores_unknown_fields(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = create(connection, name="Stable")

        # when
        row = update(connection, project_id, name="Still Stable", nonexistent="boom")

        # then
        assert row is not None
        assert row["name"] == "Still Stable"

    def test_keeps_other_fields_unchanged_when_updating_name(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = create(connection, name="Original", description="Keep me")

        # when
        row = update(connection, project_id, name="Updated")

        # then
        assert row is not None
        assert row["name"] == "Updated"
        assert row["description"] == "Keep me"

    def test_noop_when_no_valid_fields(self, connection: sqlite3.Connection) -> None:
        # given
        project_id = create(connection, name="No Change")

        # when
        row = update(connection, project_id)

        # then
        assert row is not None
        assert row["name"] == "No Change"


class TestDelete:
    def test_deletes_project_without_experiments(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = create(connection, name="Disposable")

        # when
        delete(connection, project_id)

        # then
        assert get_by_id(connection, project_id) is None

    def test_rejects_deletion_when_experiments_reference_project(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = create(connection, name="Protected")
        protocol_id = connection.execute(
            "INSERT INTO protocols (id, name, content_markdown) "
            "VALUES (1, 'Standard', '# Protocol')"
        ).lastrowid
        connection.execute(
            "INSERT INTO experiments (project_id, protocol_id, title, state) "
            "VALUES (?, ?, 'Linked experiment', 'Running')",
            (project_id, protocol_id),
        )
        connection.commit()

        # when / then
        with pytest.raises(ProjectHasExperimentsError):
            delete(connection, project_id)

    def test_does_not_delete_project_when_deletion_is_rejected(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        project_id = create(connection, name="Still Here")
        protocol_id = connection.execute(
            "INSERT INTO protocols (id, name, content_markdown) "
            "VALUES (1, 'Standard', '# Protocol')"
        ).lastrowid
        connection.execute(
            "INSERT INTO experiments (project_id, protocol_id, title, state) "
            "VALUES (?, ?, 'Linked experiment', 'Running')",
            (project_id, protocol_id),
        )
        connection.commit()

        # when / then
        with pytest.raises(ProjectHasExperimentsError):
            delete(connection, project_id)

        assert get_by_id(connection, project_id) is not None
