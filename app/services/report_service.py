from __future__ import annotations

import logging
import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from app.repositories import report_repository

logger = logging.getLogger(__name__)


class ReportNotFoundError(ValueError):
    """Raised when operating on a report that does not exist."""


class ReportTitleError(ValueError):
    """Raised when a report is saved with a blank title."""


class ReportRepository(Protocol):
    """Data access contract required by ReportService."""

    def create(
        self,
        project_id: int,
        title: str,
        content_markdown: str = "",
    ) -> int: ...

    def link_to_experiments(
        self, report_id: int, experiment_ids: Sequence[int]
    ) -> None: ...

    def get_all(
        self,
        project_id: int | None = None,
        search_text: str | None = None,
    ) -> Sequence[dict[str, Any]]: ...

    def get_by_id(self, report_id: int) -> dict[str, Any] | None: ...

    def update(self, report_id: int, **fields: object) -> dict[str, Any] | None: ...

    def delete(self, report_id: int) -> None: ...


class SqliteReportRepository:
    """Adapter that backs the report contract with SQLite functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(
        self,
        project_id: int,
        title: str,
        content_markdown: str = "",
    ) -> int:
        return report_repository.create(
            self._connection, project_id, title, content_markdown
        )

    def link_to_experiments(
        self, report_id: int, experiment_ids: Sequence[int]
    ) -> None:
        report_repository.link_to_experiments(
            self._connection, report_id, experiment_ids
        )

    def get_all(
        self,
        project_id: int | None = None,
        search_text: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        rows = report_repository.get_all(
            self._connection, project_id=project_id, search_text=search_text
        )
        return [_row_to_dict(row) for row in rows]

    def get_by_id(self, report_id: int) -> dict[str, Any] | None:
        return _row_to_dict(report_repository.get_by_id(self._connection, report_id))

    def update(self, report_id: int, **fields: object) -> dict[str, Any] | None:
        return _row_to_dict(
            report_repository.update(self._connection, report_id, **fields)
        )

    def delete(self, report_id: int) -> None:
        report_repository.delete(self._connection, report_id)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return dict(row)


class ReportService:
    """Business logic for listing, editing and deleting reports."""

    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def list_reports(
        self, filters: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Return reports, optionally filtered by project or title text."""
        filters = filters or {}
        project_id = filters.get("project_id")
        search_text = filters.get("search_text")
        if search_text is not None and not str(search_text).strip():
            search_text = None
        return list(
            self._repository.get_all(project_id=project_id, search_text=search_text)
        )

    def get_report(self, report_id: int) -> dict[str, Any]:
        """Return a report by identifier, or raise when it does not exist."""
        report = self._repository.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError(f"Report with id {report_id} does not exist")
        return report

    def create_report(
        self,
        project_id: int,
        title: str,
        content_markdown: str = "",
        experiment_ids: Sequence[int] | None = None,
    ) -> dict[str, Any]:
        """Create a report linked to experiments and return it."""
        if not title or not title.strip():
            raise ReportTitleError("Report title must not be empty")
        experiment_ids = list(experiment_ids or [])
        if not experiment_ids:
            raise ValueError("experiment_ids must contain at least one id")
        report_id = self._repository.create(project_id, title.strip(), content_markdown)
        self._repository.link_to_experiments(report_id, experiment_ids)
        logger.info("Report created report_id=%s project_id=%s", report_id, project_id)
        created = self._repository.get_by_id(report_id)
        if created is None:
            raise ReportNotFoundError(f"Report with id {report_id} was not created")
        return created

    def update_report(
        self,
        report_id: int,
        title: str | None = None,
        content_markdown: str | None = None,
    ) -> dict[str, Any]:
        """Update report fields and return the updated report."""
        if title is not None and not title.strip():
            raise ReportTitleError("Report title must not be empty")
        fields: dict[str, object] = {}
        if title is not None:
            fields["title"] = title.strip()
        if content_markdown is not None:
            fields["content_markdown"] = content_markdown
        updated = self._repository.update(report_id, **fields)
        if updated is None:
            raise ReportNotFoundError(f"Report with id {report_id} does not exist")
        logger.info("Report updated report_id=%s", report_id)
        return updated

    def delete_report(self, report_id: int) -> None:
        """Delete a report and its experiment links."""
        if self._repository.get_by_id(report_id) is None:
            raise ReportNotFoundError(f"Report with id {report_id} does not exist")
        self._repository.delete(report_id)
        logger.info("Report deleted report_id=%s", report_id)
