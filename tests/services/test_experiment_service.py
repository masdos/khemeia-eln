from collections.abc import Sequence
from typing import Any

import pytest

from app.services.experiment_service import (
    ExperimentNotFoundError,
    ExperimentReferenceError,
    ExperimentService,
    ExperimentStateError,
)


class InMemoryExperimentRepository:
    """Test double implementing ExperimentRepository without SQLite."""

    def __init__(self) -> None:
        self._experiments: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def create(
        self,
        project_id: int,
        protocol_id: int,
        title: str,
        state: str = "Running",
        question: str | None = None,
        experimental_procedure_markdown: str | None = None,
        result_markdown: str | None = None,
        conclusions: str | None = None,
    ) -> int:
        experiment_id = self._next_id
        self._next_id += 1
        self._experiments[experiment_id] = {
            "id": experiment_id,
            "project_id": project_id,
            "protocol_id": protocol_id,
            "title": title,
            "state": state,
            "question": question,
            "experimental_procedure_markdown": experimental_procedure_markdown,
            "result_markdown": result_markdown,
            "conclusions": conclusions,
            "created_at": "2026-01-01 00:00:00",
            "modified_at": "2026-01-01 00:00:00",
        }
        return experiment_id

    def get_by_id(self, experiment_id: int) -> dict[str, Any] | None:
        return self._experiments.get(experiment_id)

    def get_all(
        self,
        state: str | None = None,
        project_id: int | None = None,
        search_text: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        experiments = list(self._experiments.values())
        if state is not None:
            experiments = [e for e in experiments if e["state"] == state]
        if project_id is not None:
            experiments = [e for e in experiments if e["project_id"] == project_id]
        if search_text is not None and search_text.strip():
            term = search_text.strip().lower()
            experiments = [
                e
                for e in experiments
                if term in (e["title"] or "").lower()
                or term in (e["conclusions"] or "").lower()
            ]
        return sorted(experiments, key=lambda e: e["id"], reverse=True)

    def update(self, experiment_id: int, **fields: object) -> dict[str, Any] | None:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return None

        allowed = {
            "title",
            "state",
            "question",
            "experimental_procedure_markdown",
            "result_markdown",
            "conclusions",
        }
        for key, value in fields.items():
            if key in allowed:
                experiment[key] = value
        return experiment


class InMemoryLookupRepository:
    """Test double implementing ReferenceLookup for projects and protocols."""

    def __init__(self, ids: set[int] | None = None) -> None:
        self._ids = ids or set()

    def get_by_id(self, entity_id: int) -> dict[str, Any] | None:
        if entity_id in self._ids:
            return {"id": entity_id}

        return None


@pytest.fixture(name="experiment_repository")
def experiment_repository_fixture() -> InMemoryExperimentRepository:
    return InMemoryExperimentRepository()


@pytest.fixture(name="project_repository")
def project_repository_fixture() -> InMemoryLookupRepository:
    return InMemoryLookupRepository(ids={1, 2})


@pytest.fixture(name="protocol_repository")
def protocol_repository_fixture() -> InMemoryLookupRepository:
    return InMemoryLookupRepository(ids={1})


@pytest.fixture(name="service")
def service_fixture(
    experiment_repository: InMemoryExperimentRepository,
    project_repository: InMemoryLookupRepository,
    protocol_repository: InMemoryLookupRepository,
) -> ExperimentService:
    return ExperimentService(
        experiment_repository,
        project_repository,
        protocol_repository,
    )


class TestCreateExperiment:
    def test_creates_experiment_and_returns_its_data(
        self, service: ExperimentService
    ) -> None:
        # when
        experiment = service.create_experiment(
            project_id=1, protocol_id=1, title="Synthesis of Aspirin"
        )

        # then
        assert experiment["title"] == "Synthesis of Aspirin"
        assert experiment["project_id"] == 1
        assert experiment["protocol_id"] == 1
        assert experiment["state"] == "Running"

    def test_creates_experiment_with_full_notes(
        self, service: ExperimentService
    ) -> None:
        # when
        experiment = service.create_experiment(
            project_id=1,
            protocol_id=1,
            title="Crystal Growth",
            state="Running",
            question="Exothermic",
            conclusions="Yield 85%",
        )

        # then
        assert experiment["question"] == "Exothermic"
        assert experiment["conclusions"] == "Yield 85%"

    def test_rejects_creation_when_project_does_not_exist(
        self, service: ExperimentService
    ) -> None:
        # when / then
        with pytest.raises(ExperimentReferenceError, match="Project with id 999"):
            service.create_experiment(project_id=999, protocol_id=1, title="No project")

    def test_rejects_creation_when_protocol_does_not_exist(
        self, service: ExperimentService
    ) -> None:
        # when / then
        with pytest.raises(ExperimentReferenceError, match="Protocol with id 999"):
            service.create_experiment(
                project_id=1, protocol_id=999, title="No protocol"
            )

    def test_rejects_unsupported_state(self, service: ExperimentService) -> None:
        # when / then
        with pytest.raises(ExperimentStateError, match="must be one of"):
            service.create_experiment(
                project_id=1, protocol_id=1, title="Bad state", state="Paused"
            )


class TestGetExperiment:
    def test_returns_experiment_for_existing_id(
        self, service: ExperimentService
    ) -> None:
        # given
        experiment_id = service.create_experiment(
            project_id=1, protocol_id=1, title="Find me"
        )["id"]

        # when
        experiment = service.get_experiment(experiment_id)

        # then
        assert experiment["title"] == "Find me"

    def test_raises_not_found_for_missing_id(self, service: ExperimentService) -> None:
        # when / then
        with pytest.raises(ExperimentNotFoundError, match="does not exist"):
            service.get_experiment(999)


class TestUpdateExperiment:
    def test_updates_title_and_notes(self, service: ExperimentService) -> None:
        # given
        experiment_id = service.create_experiment(
            project_id=1, protocol_id=1, title="Original", conclusions="Old notes"
        )["id"]

        # when
        experiment = service.update_experiment(
            experiment_id, title="Updated", conclusions="New notes"
        )

        # then
        assert experiment["title"] == "Updated"
        assert experiment["conclusions"] == "New notes"

    def test_raises_not_found_for_missing_id(self, service: ExperimentService) -> None:
        # when / then
        with pytest.raises(ExperimentNotFoundError, match="does not exist"):
            service.update_experiment(999, title="Anything")


class TestChangeState:
    def test_changes_state_to_success(self, service: ExperimentService) -> None:
        # given
        experiment_id = service.create_experiment(
            project_id=1, protocol_id=1, title="Reaction"
        )["id"]

        # when
        experiment = service.change_state(experiment_id, "Success")

        # then
        assert experiment["state"] == "Success"

    def test_rejects_unsupported_state(self, service: ExperimentService) -> None:
        # given
        experiment_id = service.create_experiment(
            project_id=1, protocol_id=1, title="Reaction"
        )["id"]

        # when / then
        with pytest.raises(ExperimentStateError, match="must be one of"):
            service.change_state(experiment_id, "Paused")

    def test_raises_not_found_for_missing_id(self, service: ExperimentService) -> None:
        # when / then
        with pytest.raises(ExperimentNotFoundError, match="does not exist"):
            service.change_state(999, "Success")


class TestListExperiments:
    def test_returns_all_experiments(self, service: ExperimentService) -> None:
        # given
        service.create_experiment(project_id=1, protocol_id=1, title="Alpha")
        service.create_experiment(project_id=1, protocol_id=1, title="Beta")

        # when
        experiments = service.list_experiments()

        # then
        assert len(experiments) == 2

    def test_returns_empty_list_when_no_experiments(
        self, service: ExperimentService
    ) -> None:
        # when
        experiments = service.list_experiments()

        # then
        assert experiments == []

    def test_filters_by_state(self, service: ExperimentService) -> None:
        # given
        service.create_experiment(project_id=1, protocol_id=1, title="Running one")
        success_id = service.create_experiment(
            project_id=1, protocol_id=1, title="Success one", state="Success"
        )["id"]

        # when
        experiments = service.list_experiments({"state": "Success"})

        # then
        assert len(experiments) == 1
        assert experiments[0]["id"] == success_id

    def test_filters_by_project(self, service: ExperimentService) -> None:
        # given
        service.create_experiment(project_id=1, protocol_id=1, title="Project one")
        service.create_experiment(project_id=2, protocol_id=1, title="Other project")

        # when
        experiments = service.list_experiments({"project_id": 2})

        # then
        assert len(experiments) == 1
        assert experiments[0]["title"] == "Other project"

    def test_filters_by_search_text_in_title(self, service: ExperimentService) -> None:
        # given
        service.create_experiment(project_id=1, protocol_id=1, title="Polymer Study")
        service.create_experiment(project_id=1, protocol_id=1, title="Water Test")

        # when
        experiments = service.list_experiments({"search_text": "polymer"})

        # then
        assert len(experiments) == 1
        assert experiments[0]["title"] == "Polymer Study"

    def test_returns_no_experiments_when_no_title_matches(
        self, service: ExperimentService
    ) -> None:
        # given
        service.create_experiment(project_id=1, protocol_id=1, title="Something")

        # when
        experiments = service.list_experiments({"search_text": "Nonexistent"})

        # then
        assert experiments == []
