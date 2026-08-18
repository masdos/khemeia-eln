import sqlite3

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.attachment_repository import create, delete, get_by_experiment
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
    def test_creates_attachment_and_returns_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Synthesis")

        # when
        attachment_id = create(
            connection,
            experiment_id=experiment_id,
            file_name="spectrum.png",
            stored_name="a1b2c3d4.png",
            extension="png",
        )

        # then
        row = connection.execute(
            "SELECT id, experiment_id, file_name, stored_name, extension "
            "FROM attachments WHERE id = ?",
            (attachment_id,),
        ).fetchone()
        assert row is not None
        assert row["experiment_id"] == experiment_id
        assert row["file_name"] == "spectrum.png"
        assert row["stored_name"] == "a1b2c3d4.png"
        assert row["extension"] == "png"

    def test_stores_only_relative_names_not_absolute_paths(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Synthesis")

        # when
        attachment_id = create(
            connection,
            experiment_id=experiment_id,
            file_name="report.pdf",
            stored_name="e5f6g7h8.pdf",
            extension="pdf",
        )

        # then
        row = connection.execute(
            "SELECT file_name, stored_name FROM attachments WHERE id = ?",
            (attachment_id,),
        ).fetchone()
        assert row is not None
        assert "/" not in row["file_name"]
        assert "\\" not in row["file_name"]
        assert ":" not in row["file_name"]
        assert "/" not in row["stored_name"]
        assert "\\" not in row["stored_name"]
        assert ":" not in row["stored_name"]


class TestGetByExperiment:
    def test_returns_attachments_for_experiment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_a = _insert_experiment(connection, title="Exp A")
        experiment_b = _insert_experiment(connection, title="Exp B")
        create(
            connection,
            experiment_id=experiment_a,
            file_name="a.png",
            stored_name="a1.png",
            extension="png",
        )
        create(
            connection,
            experiment_id=experiment_a,
            file_name="b.pdf",
            stored_name="b2.pdf",
            extension="pdf",
        )
        create(
            connection,
            experiment_id=experiment_b,
            file_name="c.txt",
            stored_name="c3.txt",
            extension="txt",
        )

        # when
        rows = get_by_experiment(connection, experiment_a)

        # then
        assert len(rows) == 2
        assert {row["file_name"] for row in rows} == {"a.png", "b.pdf"}

    def test_returns_empty_list_when_no_attachments(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="No Files")

        # when
        rows = get_by_experiment(connection, experiment_id)

        # then
        assert len(rows) == 0


class TestDelete:
    def test_deletes_attachment(self, connection: sqlite3.Connection) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Synthesis")
        attachment_id = create(
            connection,
            experiment_id=experiment_id,
            file_name="spectrum.png",
            stored_name="a1b2c3d4.png",
            extension="png",
        )

        # when
        delete(connection, attachment_id)

        # then
        row = connection.execute(
            "SELECT * FROM attachments WHERE id = ?", (attachment_id,)
        ).fetchone()
        assert row is None

    def test_deletes_only_the_targeted_attachment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        experiment_id = _insert_experiment(connection, title="Synthesis")
        id_a = create(
            connection,
            experiment_id=experiment_id,
            file_name="a.png",
            stored_name="a1.png",
            extension="png",
        )
        id_b = create(
            connection,
            experiment_id=experiment_id,
            file_name="b.pdf",
            stored_name="b2.pdf",
            extension="pdf",
        )

        # when
        delete(connection, id_a)

        # then
        remaining = get_by_experiment(connection, experiment_id)
        assert len(remaining) == 1
        assert remaining[0]["id"] == id_b