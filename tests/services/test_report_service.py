from typing import Any, Sequence

import pytest

from app.services.report_service import (
    ReportNotFoundError,
    ReportService,
    ReportTitleError,
)


class FakeReportRepository:
    """Test double for report persistence without SQLite."""

    def __init__(self) -> None:
        self._reports: dict[int, dict[str, Any]] = {}
        self._links: dict[int, list[int]] = {}
        self._next_id = 1

    def create(
        self,
        project_id: int,
        title: str,
        content_markdown: str = "",
    ) -> int:
        report_id = self._next_id
        self._next_id += 1
        self._reports[report_id] = {
            "id": report_id,
            "project_id": project_id,
            "title": title,
            "content_markdown": content_markdown,
            "project_name": f"Project {project_id}",
        }
        return report_id

    def link_to_experiments(
        self, report_id: int, experiment_ids: Sequence[int]
    ) -> None:
        self._links[report_id] = list(experiment_ids)

    def seed(self, project_id: int, title: str, content_markdown: str = "") -> int:
        report_id = self._next_id
        self._next_id += 1
        self._reports[report_id] = {
            "id": report_id,
            "project_id": project_id,
            "title": title,
            "content_markdown": content_markdown,
            "project_name": f"Project {project_id}",
        }
        return report_id

    def get_all(
        self,
        project_id: int | None = None,
        search_text: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        results = list(self._reports.values())
        if project_id is not None:
            results = [r for r in results if r["project_id"] == project_id]
        if search_text:
            results = [r for r in results if search_text.lower() in r["title"].lower()]
        return results

    def get_by_id(self, report_id: int) -> dict[str, Any] | None:
        return self._reports.get(report_id)

    def update(self, report_id: int, **fields: object) -> dict[str, Any] | None:
        report = self._reports.get(report_id)
        if report is None:
            return None
        report.update(fields)
        return report

    def delete(self, report_id: int) -> None:
        del self._reports[report_id]


def test_lists_reports_of_selected_project() -> None:
    # given
    repository = FakeReportRepository()
    service = ReportService(repository)
    repository.seed(1, "Report A")
    repository.seed(2, "Other project report")

    # when
    reports = service.list_reports({"project_id": 1})

    # then
    assert [report["title"] for report in reports] == ["Report A"]


def test_searches_reports_by_title_text() -> None:
    # given
    repository = FakeReportRepository()
    service = ReportService(repository)
    repository.seed(1, "Monthly synthesis")
    repository.seed(1, "Weekly cleanup")

    # when
    reports = service.list_reports({"search_text": "synthesis"})

    # then
    assert [report["title"] for report in reports] == ["Monthly synthesis"]


def test_returns_report_by_identifier() -> None:
    # given
    repository = FakeReportRepository()
    service = ReportService(repository)
    report_id = repository.seed(1, "Report A", "# Content")

    # when
    report = service.get_report(report_id)

    # then
    assert report["title"] == "Report A"
    assert report["content_markdown"] == "# Content"


def test_raises_when_report_does_not_exist() -> None:
    # given
    service = ReportService(FakeReportRepository())

    # when / then
    with pytest.raises(ReportNotFoundError, match="does not exist"):
        service.get_report(999)


def test_updates_title_and_content() -> None:
    # given
    repository = FakeReportRepository()
    service = ReportService(repository)
    report_id = repository.seed(1, "Old title", "# Old")

    # when
    updated = service.update_report(report_id, "New title", "# New")

    # then
    assert updated["title"] == "New title"
    assert updated["content_markdown"] == "# New"


def test_rejects_blank_title_when_updating() -> None:
    # given
    repository = FakeReportRepository()
    service = ReportService(repository)
    report_id = repository.seed(1, "Old title")

    # when / then
    with pytest.raises(ReportTitleError, match="must not be empty"):
        service.update_report(report_id, "   ")


def test_raises_when_updating_missing_report() -> None:
    # given
    service = ReportService(FakeReportRepository())

    # when / then
    with pytest.raises(ReportNotFoundError, match="does not exist"):
        service.update_report(999, "Ghost")


def test_deletes_existing_report() -> None:
    # given
    repository = FakeReportRepository()
    service = ReportService(repository)
    report_id = repository.seed(1, "Report A")

    # when
    service.delete_report(report_id)

    # then
    assert repository.get_by_id(report_id) is None


def test_raises_when_deleting_missing_report() -> None:
    # given
    service = ReportService(FakeReportRepository())

    # when / then
    with pytest.raises(ReportNotFoundError, match="does not exist"):
        service.delete_report(999)


def test_creates_report_linked_to_experiments() -> None:
    # given
    repository = FakeReportRepository()
    service = ReportService(repository)

    # when
    created = service.create_report(1, "Monthly report", "# Draft", [1, 2])

    # then
    assert created["project_id"] == 1
    assert created["title"] == "Monthly report"
    assert created["content_markdown"] == "# Draft"
    assert repository._links[created["id"]] == [1, 2]


def test_rejects_blank_title_when_creating() -> None:
    # given
    service = ReportService(FakeReportRepository())

    # when / then
    with pytest.raises(ReportTitleError, match="must not be empty"):
        service.create_report(1, "   ", "", [1])


def test_rejects_creation_without_experiments() -> None:
    # given
    service = ReportService(FakeReportRepository())

    # when / then
    with pytest.raises(ValueError, match="experiment_ids"):
        service.create_report(1, "Monthly report")
