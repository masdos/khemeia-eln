import sqlite3

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.attachment_repository import (
    create,
    delete,
    get_by_experiment,
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
    def test_creates_attachment_and_returns_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        attachment_id = create(
            connection,
            experiment_id=1,
            file_name="report.pdf",
            stored_name="550e8400-e29b-41d4-a716-446655440000.pdf",
        )

        # then
        row = connection.execute(
            "SELECT id, experiment_id, file_name, stored_name "
            "FROM attachments WHERE id = ?",
            (attachment_id,),
        ).fetchone()
        assert row["file_name"] == "report.pdf"
        assert row["stored_name"] == "550e8400-e29b-41d4-a716-446655440000.pdf"

    def test_creates_attachment_with_same_file_name_on_different_experiments(
        self, connection: sqlite3.Connection
    ) -> None:
        # given / when
        id1 = create(
            connection, experiment_id=1, file_name="data.csv", stored_name="uuid1.csv"
        )
        id2 = create(
            connection, experiment_id=2, file_name="data.csv", stored_name="uuid2.csv"
        )

        # then
        assert id1 != id2
        row1 = connection.execute(
            "SELECT * FROM attachments WHERE id = ?", (id1,)
        ).fetchone()
        row2 = connection.execute(
            "SELECT * FROM attachments WHERE id = ?", (id2,)
        ).fetchone()
        assert row1["stored_name"] == "uuid1.csv"
        assert row2["stored_name"] == "uuid2.csv"


class TestGetByExperiment:
    def test_returns_attachments_for_experiment(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(
            connection,
            experiment_id=1,
            file_name="chromatogram.png",
            stored_name="abc.png",
        )
        create(
            connection,
            experiment_id=1,
            file_name="notes.txt",
            stored_name="def.txt",
        )

        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 2
        file_names = [r["file_name"] for r in rows]
        assert "chromatogram.png" in file_names
        assert "notes.txt" in file_names

    def test_returns_empty_list_when_no_attachments(
        self, connection: sqlite3.Connection
    ) -> None:
        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 0

    def test_does_not_return_attachments_from_other_experiments(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(
            connection,
            experiment_id=2,
            file_name="exp_b_only.txt",
            stored_name="only.txt",
        )

        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 0

    def test_returns_only_id_experiment_id_file_name_and_stored_name(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        create(
            connection,
            experiment_id=1,
            file_name="test.txt",
            stored_name="stored.txt",
        )

        # when
        rows = get_by_experiment(connection, experiment_id=1)

        # then
        assert len(rows) == 1
        assert set(rows[0].keys()) == {
            "id",
            "experiment_id",
            "file_name",
            "stored_name",
        }


class TestDelete:
    def test_deletes_attachment_by_id(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        attachment_id = create(
            connection,
            experiment_id=1,
            file_name="temporary.txt",
            stored_name="temp.txt",
        )

        # when
        delete(connection, attachment_id)

        # then
        row = connection.execute(
            "SELECT * FROM attachments WHERE id = ?", (attachment_id,)
        ).fetchone()
        assert row is None

    def test_does_not_affect_other_attachments_when_deleting_one(
        self, connection: sqlite3.Connection
    ) -> None:
        # given
        id1 = create(
            connection,
            experiment_id=1,
            file_name="keep.txt",
            stored_name="keep.txt",
        )
        id2 = create(
            connection,
            experiment_id=1,
            file_name="remove.txt",
            stored_name="remove.txt",
        )

        # when
        delete(connection, id2)

        # then
        remaining = get_by_experiment(connection, experiment_id=1)
        assert len(remaining) == 1
        assert remaining[0]["id"] == id1

    def test_succeeds_when_attachment_does_not_exist(
        self, connection: sqlite3.Connection
    ) -> None:
        # when / then (no exception)
        delete(connection, 999)
