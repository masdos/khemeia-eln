import sqlite3

import pytest

from app.database.connection import close_connection, get_connection
from app.repositories.experiment_repository import create as create_experiment
from app.repositories.report_repository import (
    create,
    get_by_experiment,
    get_by_id,
    get_by_project,
    link_to_experiments,
)


@pytest.fixture(name="connection")
def connection_fixture() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    yield conn
    close_connection(conn)


def _insert_project(connection: sqlite3.Connection, name: str) -> int:
    cursor = connection.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    connection.commit()
    return cursor.lastrowid


def _insert_protocol(connection: sqlite3.Connection, name: str) -> int:
    cursor = connection.execute(
        "INSERT INTO protocols (name, content_markdown) VALUES (?, '# Content')",
        (name,),
    )
    connection.commit()
    return cursor.lastrowid


def _insert_experiment(connection: sqlite3.Connection, title: str) -> int:
    project_id = _insert_project(connection, name=f"Project {title}")
    protocol_id = _insert_protocol(connection, name=f"Protocol {title}")
    return create_experiment(
        connection,
        project_id=project_id,
        protocol_id=protocol_id,
        title=title,
    )


def test_creates_report_with_project_title_and_content(
    connection: sqlite3.Connection,
) -> None:
    # given
    project_id = _insert_project(connection, "Lab Project")

    # when
    report_id = create(connection, project_id, "Monthly report", "# Content")

    # then
    report = get_by_id(connection, report_id)
    assert report is not None
    assert report["project_id"] == project_id
    assert report["title"] == "Monthly report"
    assert report["content_markdown"] == "# Content"
    assert report["created_at"] is not None
    assert report["modified_at"] is not None


def test_defaults_content_to_empty_string(connection: sqlite3.Connection) -> None:
    # given
    project_id = _insert_project(connection, "Lab Project")

    # when
    report_id = create(connection, project_id, "Monthly report")

    # then
    report = get_by_id(connection, report_id)
    assert report is not None
    assert report["content_markdown"] == ""


def test_links_report_to_multiple_experiments(connection: sqlite3.Connection) -> None:
    # given
    project_id = _insert_project(connection, "Lab Project")
    report_id = create(connection, project_id, "Monthly report")
    experiment_ids = [
        _insert_experiment(connection, "Experiment A"),
        _insert_experiment(connection, "Experiment B"),
    ]

    # when
    link_to_experiments(connection, report_id, experiment_ids)

    # then
    links = connection.execute(
        "SELECT experiment_id FROM experiment_reports WHERE report_id = ?",
        (report_id,),
    ).fetchall()
    assert {link["experiment_id"] for link in links} == set(experiment_ids)


def test_returns_only_reports_linked_to_experiment(
    connection: sqlite3.Connection,
) -> None:
    # given
    project_id = _insert_project(connection, "Lab Project")
    experiment_a = _insert_experiment(connection, "Experiment A")
    experiment_b = _insert_experiment(connection, "Experiment B")
    report_a = create(connection, project_id, "Report A")
    report_b = create(connection, project_id, "Report B")
    link_to_experiments(connection, report_a, [experiment_a])
    link_to_experiments(connection, report_b, [experiment_b])

    # when
    reports = get_by_experiment(connection, experiment_a)

    # then
    assert [report["id"] for report in reports] == [report_a]


def test_returns_reports_belonging_to_project(
    connection: sqlite3.Connection,
) -> None:
    # given
    project_a = _insert_project(connection, "Project A")
    project_b = _insert_project(connection, "Project B")
    report_a = create(connection, project_a, "Report A", "# A")
    create(connection, project_b, "Report B", "# B")

    # when
    reports = get_by_project(connection, project_a)

    # then
    assert [report["id"] for report in reports] == [report_a]
    assert reports[0]["content_markdown"] == "# A"


def test_returns_none_for_missing_report(connection: sqlite3.Connection) -> None:
    # given
    missing_report_id = 999

    # when
    report = get_by_id(connection, missing_report_id)

    # then
    assert report is None
