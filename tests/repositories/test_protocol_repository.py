import sqlite3

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.protocol_repository import (
    ProtocolHasExperimentsError,
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
    def test_creates_protocol_and_returns_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        protocol_id = create(
            connection, name="Standard Workup", content_markdown="# Workup"
        )

        # then
        row = connection.execute(
            "SELECT id, name, content_markdown FROM protocols WHERE id = ?",
            (protocol_id,),
        ).fetchone()
        assert row is not None
        assert row["name"] == "Standard Workup"
        assert row["content_markdown"] == "# Workup"

    def test_creates_protocol_with_long_markdown(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        content = "## Step 1\n\nMix reagents and stir for 30 minutes."
        protocol_id = create(
            connection, name="Multi-step Synthesis", content_markdown=content
        )

        # then
        row = get_by_id(connection, protocol_id)
        assert row is not None
        assert row["name"] == "Multi-step Synthesis"
        assert row["content_markdown"] == content


class TestGetById:
    def test_returns_row_for_existing_protocol(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        protocol_id = create(connection, name="Find me", content_markdown="# Find")

        # when
        row = get_by_id(connection, protocol_id)

        # then
        assert row is not None
        assert row["name"] == "Find me"

    def test_returns_none_when_protocol_does_not_exist(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        row = get_by_id(connection, 999)

        # then
        assert row is None


class TestGetAll:
    def test_returns_all_protocols_ordered_by_id_desc(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        id_a = create(connection, name="Alpha", content_markdown="# Alpha")
        id_b = create(connection, name="Beta", content_markdown="# Beta")

        # when
        rows = get_all(connection)

        # then
        assert len(rows) == 2
        assert rows[0]["id"] == id_b
        assert rows[1]["id"] == id_a

    def test_returns_empty_list_when_no_protocols(
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
        create(connection, name="Crystallisation", content_markdown="# Crystallisation")
        create(connection, name="Distillation", content_markdown="# Distillation")

        # when
        rows = get_all(connection, search_text="Crystallisation")

        # then
        assert len(rows) == 1
        assert rows[0]["name"] == "Crystallisation"

    def test_filters_by_search_text_in_content_markdown(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(
            connection,
            name="General",
            content_markdown="# Extraction\nUse diethyl ether.",
        )
        create(connection, name="Other", content_markdown="# No match here")

        # when
        rows = get_all(connection, search_text="diethyl ether")

        # then
        assert len(rows) == 1
        assert rows[0]["name"] == "General"

    def test_search_text_is_case_insensitive(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, name="Reflux Setup", content_markdown="# Reflux")
        create(connection, name="Filtration", content_markdown="# Filtration")

        # when
        rows = get_all(connection, search_text="reflux")

        # then
        assert len(rows) == 1
        assert rows[0]["name"] == "Reflux Setup"

    def test_ignores_whitespace_only_search_text(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, name="All protocols visible", content_markdown="# Visible")

        # when
        rows = get_all(connection, search_text="   ")

        # then
        assert len(rows) == 1

    def test_returns_empty_list_when_no_content_matches(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(connection, name="Something", content_markdown="# Something")

        # when
        rows = get_all(connection, search_text="Nonexistent")

        # then
        assert len(rows) == 0


class TestUpdate:
    def test_updates_name(self, connection: sqlite3.Connection) -> None:
        # given
        protocol_id = create(connection, name="Old Name", content_markdown="# Old")

        # when
        row = update(connection, protocol_id, name="New Name")

        # then
        assert row is not None
        assert row["name"] == "New Name"

    def test_updates_content_markdown(self, connection: sqlite3.Connection) -> None:
        # given
        protocol_id = create(connection, name="Protocol", content_markdown="# Old")

        # when
        row = update(connection, protocol_id, content_markdown="# Updated content")

        # then
        assert row is not None
        assert row["content_markdown"] == "# Updated content"

    def test_updates_multiple_fields(self, connection: sqlite3.Connection) -> None:
        # given
        protocol_id = create(connection, name="Original", content_markdown="# Original")

        # when
        row = update(
            connection,
            protocol_id,
            name="Updated Name",
            content_markdown="# Updated",
        )

        # then
        assert row is not None
        assert row["name"] == "Updated Name"
        assert row["content_markdown"] == "# Updated"

    def test_ignores_unknown_fields(self, connection: sqlite3.Connection) -> None:
        # given
        protocol_id = create(connection, name="Stable", content_markdown="# Stable")

        # when
        row = update(connection, protocol_id, name="Still Stable", nonexistent="boom")

        # then
        assert row is not None
        assert row["name"] == "Still Stable"

    def test_keeps_other_fields_unchanged_when_updating_name(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        protocol_id = create(connection, name="Original", content_markdown="# Keep me")

        # when
        row = update(connection, protocol_id, name="Updated")

        # then
        assert row is not None
        assert row["name"] == "Updated"
        assert row["content_markdown"] == "# Keep me"

    def test_noop_when_no_valid_fields(self, connection: sqlite3.Connection) -> None:
        # given
        protocol_id = create(connection, name="No Change", content_markdown="# No")

        # when
        row = update(connection, protocol_id)

        # then
        assert row is not None
        assert row["name"] == "No Change"


class TestDelete:
    def test_deletes_protocol_without_experiments(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        protocol_id = create(
            connection, name="Disposable", content_markdown="# Discard"
        )

        # when
        delete(connection, protocol_id)

        # then
        assert get_by_id(connection, protocol_id) is None

    def test_rejects_deletion_when_experiments_reference_protocol(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        protocol_id = create(
            connection, name="Protected", content_markdown="# Protected"
        )
        project_id = connection.execute(
            "INSERT INTO projects (name) VALUES ('Project')"
        ).lastrowid
        connection.execute(
            "INSERT INTO experiments (project_id, protocol_id, title, state) "
            "VALUES (?, ?, 'Linked experiment', 'Running')",
            (project_id, protocol_id),
        )
        connection.commit()

        # when / then
        with pytest.raises(ProtocolHasExperimentsError):
            delete(connection, protocol_id)

    def test_does_not_delete_protocol_when_deletion_is_rejected(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        protocol_id = create(connection, name="Still Here", content_markdown="# Here")
        project_id = connection.execute(
            "INSERT INTO projects (name) VALUES ('Project')"
        ).lastrowid
        connection.execute(
            "INSERT INTO experiments (project_id, protocol_id, title, state) "
            "VALUES (?, ?, 'Linked experiment', 'Running')",
            (project_id, protocol_id),
        )
        connection.commit()

        # when / then
        with pytest.raises(ProtocolHasExperimentsError):
            delete(connection, protocol_id)

        assert get_by_id(connection, protocol_id) is not None
