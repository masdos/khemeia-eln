from collections.abc import Sequence
from typing import Any

import pytest

from app.repositories.project_repository import ProjectHasExperimentsError
from app.services.project_service import (
    ProjectDeletionError,
    ProjectNameError,
    ProjectNotFoundError,
    ProjectService,
)


class InMemoryProjectRepository:
    """Test double implementing ProjectRepository without SQLite."""

    def __init__(self) -> None:
        self._projects: dict[int, dict[str, Any]] = {}
        self._experiment_count_by_project: dict[int, int] = {}
        self._next_id = 1

    def create(self, name: str, description: str = "") -> int:
        project_id = self._next_id
        self._next_id += 1
        self._projects[project_id] = {
            "id": project_id,
            "name": name,
            "description": description,
            "created_at": "2026-01-01 00:00:00",
            "modified_at": "2026-01-01 00:00:00",
        }
        return project_id

    def get_by_id(self, project_id: int) -> dict[str, Any] | None:
        return self._projects.get(project_id)

    def get_all(self, search_text: str | None = None) -> Sequence[dict[str, Any]]:
        projects = list(self._projects.values())
        if search_text is not None and search_text.strip():
            term = search_text.strip().lower()
            projects = [p for p in projects if term in p["name"].lower()]
        return sorted(projects, key=lambda p: p["id"], reverse=True)

    def update(self, project_id: int, **fields: object) -> dict[str, Any] | None:
        project = self._projects.get(project_id)
        if project is None:
            return None

        for key in ("name", "description"):
            if key in fields:
                project[key] = fields[key]
        return project

    def delete(self, project_id: int) -> None:
        if self._experiment_count_by_project.get(project_id, 0) > 0:
            raise ProjectHasExperimentsError(
                "Project cannot be deleted while experiments reference it"
            )

        del self._projects[project_id]

    def add_experiment(self, project_id: int) -> None:
        self._experiment_count_by_project[project_id] = (
            self._experiment_count_by_project.get(project_id, 0) + 1
        )


@pytest.fixture(name="repository")
def repository_fixture() -> InMemoryProjectRepository:
    return InMemoryProjectRepository()


@pytest.fixture(name="service")
def service_fixture(repository: InMemoryProjectRepository) -> ProjectService:
    return ProjectService(repository)


class TestCreateProject:
    def test_creates_project_and_returns_its_data(
        self, service: ProjectService
    ) -> None:
        # when
        project = service.create_project(name="Synthesis of Aspirin")

        # then
        assert project["name"] == "Synthesis of Aspirin"
        assert project["description"] == ""
        assert project["id"] > 0

    def test_creates_project_with_description(self, service: ProjectService) -> None:
        # when
        project = service.create_project(
            name="Crystal Growth",
            description="Series of crystallisation experiments",
        )

        # then
        assert project["name"] == "Crystal Growth"
        assert project["description"] == "Series of crystallisation experiments"

    def test_rejects_blank_name(self, service: ProjectService) -> None:
        # when / then
        with pytest.raises(ProjectNameError, match="cannot be blank"):
            service.create_project(name="   ")

    def test_rejects_blank_name_when_no_projects_are_created(
        self, service: ProjectService, repository: InMemoryProjectRepository
    ) -> None:
        # given
        initial_count = len(repository.get_all())

        # when / then
        with pytest.raises(ProjectNameError):
            service.create_project(name="")

        assert len(repository.get_all()) == initial_count


class TestGetProject:
    def test_returns_project_for_existing_id(
        self, service: ProjectService, repository: InMemoryProjectRepository
    ) -> None:
        # given
        project_id = repository.create(name="Find me")

        # when
        project = service.get_project(project_id)

        # then
        assert project["name"] == "Find me"

    def test_raises_not_found_for_missing_id(self, service: ProjectService) -> None:
        # when / then
        with pytest.raises(ProjectNotFoundError, match="does not exist"):
            service.get_project(999)


class TestUpdateProject:
    def test_updates_name_and_description(
        self, service: ProjectService, repository: InMemoryProjectRepository
    ) -> None:
        # given
        project_id = repository.create(name="Original", description="Old desc")

        # when
        project = service.update_project(
            project_id, name="Updated", description="New desc"
        )

        # then
        assert project["name"] == "Updated"
        assert project["description"] == "New desc"

    def test_rejects_blank_name(
        self, service: ProjectService, repository: InMemoryProjectRepository
    ) -> None:
        # given
        project_id = repository.create(name="Stable")

        # when / then
        with pytest.raises(ProjectNameError, match="cannot be blank"):
            service.update_project(project_id, name="")

    def test_raises_not_found_for_missing_id(self, service: ProjectService) -> None:
        # when / then
        with pytest.raises(ProjectNotFoundError, match="does not exist"):
            service.update_project(999, name="Anything")


class TestDeleteProject:
    def test_deletes_project_without_experiments(
        self, service: ProjectService, repository: InMemoryProjectRepository
    ) -> None:
        # given
        project_id = repository.create(name="Disposable")

        # when
        service.delete_project(project_id)

        # then
        assert repository.get_by_id(project_id) is None

    def test_rejects_deletion_when_experiments_reference_project(
        self, service: ProjectService, repository: InMemoryProjectRepository
    ) -> None:
        # given
        project_id = repository.create(name="Protected")
        repository.add_experiment(project_id)

        # when / then
        with pytest.raises(ProjectDeletionError, match="associated experiments"):
            service.delete_project(project_id)

    def test_does_not_delete_project_when_deletion_is_rejected(
        self, service: ProjectService, repository: InMemoryProjectRepository
    ) -> None:
        # given
        project_id = repository.create(name="Still Here")
        repository.add_experiment(project_id)

        # when / then
        with pytest.raises(ProjectDeletionError):
            service.delete_project(project_id)

        assert repository.get_by_id(project_id) is not None

    def test_raises_not_found_for_missing_id(self, service: ProjectService) -> None:
        # when / then
        with pytest.raises(ProjectNotFoundError, match="does not exist"):
            service.delete_project(999)


class TestListProjects:
    def test_returns_all_projects(self, service: ProjectService) -> None:
        # given
        service.create_project(name="Alpha")
        service.create_project(name="Beta")

        # when
        projects = service.list_projects()

        # then
        assert len(projects) == 2

    def test_returns_empty_list_when_no_projects(self, service: ProjectService) -> None:
        # when
        projects = service.list_projects()

        # then
        assert projects == []

    def test_filters_by_search_text(self, service: ProjectService) -> None:
        # given
        service.create_project(name="Polymer Synthesis")
        service.create_project(name="Water Analysis")

        # when
        projects = service.list_projects({"search_text": "polymer"})

        # then
        assert len(projects) == 1
        assert projects[0]["name"] == "Polymer Synthesis"

    def test_returns_all_projects_when_filters_are_empty(
        self, service: ProjectService
    ) -> None:
        # given
        service.create_project(name="Only Project")

        # when
        projects = service.list_projects({})

        # then
        assert len(projects) == 1

    def test_returns_no_projects_when_no_name_matches(
        self, service: ProjectService
    ) -> None:
        # given
        service.create_project(name="Something")

        # when
        projects = service.list_projects({"search_text": "Nonexistent"})

        # then
        assert projects == []
