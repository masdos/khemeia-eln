from __future__ import annotations

import logging
import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from app.repositories import project_repository
from app.repositories.project_repository import ProjectHasExperimentsError

logger = logging.getLogger(__name__)


class ProjectNotFoundError(ValueError):
    """Raised when operating on a project that does not exist."""


class ProjectDeletionError(ValueError):
    """Raised when a project with associated experiments cannot be deleted."""


class ProjectNameError(ValueError):
    """Raised when a project is created or updated with a blank name."""


@runtime_checkable
class ProjectRepository(Protocol):
    """Data access contract required by ProjectService."""

    def create(self, name: str, description: str = "") -> int: ...

    def get_by_id(self, project_id: int) -> dict[str, Any] | None: ...

    def get_all(self, search_text: str | None = None) -> Sequence[dict[str, Any]]: ...

    def update(self, project_id: int, **fields: object) -> dict[str, Any] | None: ...

    def delete(self, project_id: int) -> None: ...


class SqliteProjectRepository:
    """Adapter that backs ProjectRepository with the SQLite project functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, name: str, description: str = "") -> int:
        return project_repository.create(self._connection, name, description)

    def get_by_id(self, project_id: int) -> dict[str, Any] | None:
        return _row_to_dict(project_repository.get_by_id(self._connection, project_id))

    def get_all(self, search_text: str | None = None) -> Sequence[dict[str, Any]]:
        rows = project_repository.get_all(self._connection, search_text=search_text)
        return [_row_to_dict(row) for row in rows]

    def update(self, project_id: int, **fields: object) -> dict[str, Any] | None:
        row = project_repository.update(self._connection, project_id, **fields)
        return _row_to_dict(row)

    def delete(self, project_id: int) -> None:
        project_repository.delete(self._connection, project_id)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return dict(row)


class ProjectService:
    """Business logic for managing projects. Never executes SQL directly."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def create_project(self, name: str, description: str = "") -> dict[str, Any]:
        _require_valid_name(name)
        project_id = self._repository.create(name, description)
        project = self._repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project with id {project_id} was not created")

        logger.info("Project created project_id=%s", project_id)
        return project

    def update_project(
        self,
        project_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        if self._repository.get_by_id(project_id) is None:
            raise ProjectNotFoundError(f"Project with id {project_id} does not exist")

        fields: dict[str, object] = {}
        if name is not None:
            _require_valid_name(name)
            fields["name"] = name
        if description is not None:
            fields["description"] = description

        updated = self._repository.update(project_id, **fields)
        if updated is None:
            raise ProjectNotFoundError(f"Project with id {project_id} does not exist")

        logger.info("Project updated project_id=%s", project_id)
        return updated

    def delete_project(self, project_id: int) -> None:
        if self._repository.get_by_id(project_id) is None:
            raise ProjectNotFoundError(f"Project with id {project_id} does not exist")

        try:
            self._repository.delete(project_id)
        except ProjectHasExperimentsError as error:
            raise ProjectDeletionError(
                f"Project with id {project_id} cannot be deleted because "
                "it has associated experiments"
            ) from error

        logger.info("Project deleted project_id=%s", project_id)

    def get_project(self, project_id: int) -> dict[str, Any]:
        project = self._repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project with id {project_id} does not exist")

        return project

    def list_projects(
        self,
        filters: Mapping[str, Any] | None = None,
    ) -> Sequence[dict[str, Any]]:
        search_text = None
        if filters:
            search_text = filters.get("search_text")

        projects = self._repository.get_all(search_text=search_text)
        logger.debug("Projects listed count=%s", len(projects))
        return projects


def _require_valid_name(name: str) -> None:
    if not name or not name.strip():
        raise ProjectNameError("Project name cannot be blank")
