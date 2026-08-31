from __future__ import annotations

import logging
import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from app.repositories import experiment_repository
from app.repositories.experiment_repository import VALID_STATES

logger = logging.getLogger(__name__)


class ExperimentNotFoundError(ValueError):
    """Raised when operating on an experiment that does not exist."""


class ExperimentReferenceError(ValueError):
    """Raised when creating an experiment referencing a missing project or protocol."""


class ExperimentStateError(ValueError):
    """Raised when changing an experiment to an unsupported state."""


class ExperimentRepository(Protocol):
    """Data access contract required by ExperimentService."""

    def create(
        self,
        project_id: int,
        protocol_id: int,
        title: str,
        state: str = "Running",
        reaction_onset: str | None = None,
        workup: str | None = None,
        purification: str | None = None,
        notes: str | None = None,
    ) -> int: ...

    def get_by_id(self, experiment_id: int) -> dict[str, Any] | None: ...

    def get_all(
        self,
        state: str | None = None,
        project_id: int | None = None,
        search_text: str | None = None,
    ) -> Sequence[dict[str, Any]]: ...

    def update(self, experiment_id: int, **fields: object) -> dict[str, Any] | None: ...

    def delete(self, experiment_id: int) -> bool: ...


class ReferenceLookup(Protocol):
    """Minimal lookup contract for validating project and protocol existence."""

    def get_by_id(self, entity_id: int) -> dict[str, Any] | None: ...


class SqliteExperimentRepository:
    """Adapter that backs ExperimentRepository with the SQLite experiment functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(
        self,
        project_id: int,
        protocol_id: int,
        title: str,
        state: str = "Running",
        reaction_onset: str | None = None,
        workup: str | None = None,
        purification: str | None = None,
        notes: str | None = None,
    ) -> int:
        return experiment_repository.create(
            self._connection,
            project_id,
            protocol_id,
            title,
            state,
            reaction_onset,
            workup,
            purification,
            notes,
        )

    def get_by_id(self, experiment_id: int) -> dict[str, Any] | None:
        return _row_to_dict(
            experiment_repository.get_by_id(self._connection, experiment_id)
        )

    def get_all(
        self,
        state: str | None = None,
        project_id: int | None = None,
        search_text: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        rows = experiment_repository.get_all(
            self._connection,
            state=state,
            project_id=project_id,
            search_text=search_text,
        )
        return [_row_to_dict(row) for row in rows]

    def update(self, experiment_id: int, **fields: object) -> dict[str, Any] | None:
        row = experiment_repository.update(self._connection, experiment_id, **fields)
        return _row_to_dict(row)

    def delete(self, experiment_id: int) -> bool:
        return experiment_repository.delete(self._connection, experiment_id)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return dict(row)


class ExperimentService:
    """Business logic for managing experiments. Never executes SQL directly."""

    def __init__(
        self,
        experiment_repo: ExperimentRepository,
        project_repo: ReferenceLookup,
        protocol_repo: ReferenceLookup,
    ) -> None:
        self._experiment_repo = experiment_repo
        self._project_repo = project_repo
        self._protocol_repo = protocol_repo

    def create_experiment(
        self,
        project_id: int,
        protocol_id: int,
        title: str,
        state: str = "Running",
        reaction_onset: str | None = None,
        workup: str | None = None,
        purification: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        _require_valid_state(state)
        _require_existing_reference(self._project_repo, project_id, "Project")
        _require_existing_reference(self._protocol_repo, protocol_id, "Protocol")

        experiment_id = self._experiment_repo.create(
            project_id,
            protocol_id,
            title,
            state,
            reaction_onset,
            workup,
            purification,
            notes,
        )
        experiment = self._experiment_repo.get_by_id(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(
                f"Experiment with id {experiment_id} was not created"
            )

        logger.info("Experiment created experiment_id=%s", experiment_id)
        return experiment

    def update_experiment(
        self,
        experiment_id: int,
        **fields: object,
    ) -> dict[str, Any]:
        if "state" in fields:
            _require_valid_state(fields["state"])

        if self._experiment_repo.get_by_id(experiment_id) is None:
            raise ExperimentNotFoundError(
                f"Experiment with id {experiment_id} does not exist"
            )

        updated = self._experiment_repo.update(experiment_id, **fields)
        if updated is None:
            raise ExperimentNotFoundError(
                f"Experiment with id {experiment_id} does not exist"
            )

        logger.info("Experiment updated experiment_id=%s", experiment_id)
        return updated

    def change_state(self, experiment_id: int, new_state: str) -> dict[str, Any]:
        _require_valid_state(new_state)
        return self.update_experiment(experiment_id, state=new_state)

    def get_experiment(self, experiment_id: int) -> dict[str, Any]:
        experiment = self._experiment_repo.get_by_id(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(
                f"Experiment with id {experiment_id} does not exist"
            )

        return experiment

    def list_experiments(
        self,
        filters: Mapping[str, Any] | None = None,
    ) -> Sequence[dict[str, Any]]:
        filters = filters or {}
        experiments = self._experiment_repo.get_all(
            state=filters.get("state"),
            project_id=filters.get("project_id"),
            search_text=filters.get("search_text"),
        )
        logger.debug("Experiments listed count=%s", len(experiments))
        return experiments

    def delete_experiment(self, experiment_id: int) -> None:
        if self._experiment_repo.get_by_id(experiment_id) is None:
            raise ExperimentNotFoundError(
                f"Experiment with id {experiment_id} does not exist"
            )
        self._experiment_repo.delete(experiment_id)
        logger.info("Experiment deleted experiment_id=%s", experiment_id)


def _require_valid_state(state: object) -> None:
    if state not in VALID_STATES:
        raise ExperimentStateError(
            f"Experiment state must be one of {sorted(VALID_STATES)}"
        )


def _require_existing_reference(
    repository: ReferenceLookup,
    entity_id: int,
    entity_name: str,
) -> None:
    if repository.get_by_id(entity_id) is None:
        raise ExperimentReferenceError(
            f"{entity_name} with id {entity_id} does not exist"
        )
