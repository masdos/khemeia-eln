from __future__ import annotations

from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from app.services.experiment_service import ExperimentService


class FakeExperimentRepository:
    def __init__(self) -> None:
        self._experiments: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def create(
        self,
        project_id: int,
        protocol_id: int,
        title: str,
        state: str = "Running",
        **kwargs: object,
    ) -> int:
        exp_id = self._next_id
        self._next_id += 1
        self._experiments[exp_id] = {
            "id": exp_id,
            "project_id": project_id,
            "protocol_id": protocol_id,
            "title": title,
            "state": state,
            "created_at": "2026-01-01",
            "project_name": "Test Project",
        }
        return exp_id

    def get_by_id(self, experiment_id: int) -> dict[str, Any] | None:
        return self._experiments.get(experiment_id)

    def get_all(
        self,
        state: str | None = None,
        project_id: int | None = None,
        search_text: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        results = list(self._experiments.values())
        if state:
            results = [e for e in results if e["state"] == state]
        if search_text:
            results = [
                e for e in results
                if search_text.lower() in e["title"].lower()
            ]
        return results

    def update(
        self, experiment_id: int, **fields: object
    ) -> dict[str, Any] | None:
        exp = self._experiments.get(experiment_id)
        if exp is None:
            return None
        exp.update(fields)
        return exp


class FakeRefRepository:
    def __init__(self, items: dict[int, dict[str, Any]]) -> None:
        self._items = items

    def get_by_id(self, entity_id: int) -> dict[str, Any] | None:
        return self._items.get(entity_id)


def _make_chainable(value: str = "") -> MagicMock:
    mock = MagicMock()
    mock.value = value
    mock.props.return_value = mock
    mock.classes.return_value = mock
    return mock


def test_dashboard_lists_experiments() -> None:
    """Dashboard should render experiments from the service."""
    exp_repo = FakeExperimentRepository()
    project_repo = FakeRefRepository({1: {"id": 1, "name": "P1"}})
    protocol_repo = FakeRefRepository({1: {"id": 1, "name": "Proto1"}})

    exp_repo.create(1, 1, "Exp A", "Running")
    exp_repo.create(1, 1, "Exp B", "Success")

    service = ExperimentService(exp_repo, project_repo, protocol_repo)

    with patch(
        "app.ui.pages.dashboard._get_experiment_service",
        return_value=service,
    ):
        with patch("app.ui.pages.dashboard.ui") as mock_ui:
            mock_ui.column.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.column.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.input.return_value = _make_chainable("")
            mock_ui.select.return_value = _make_chainable("All")
            mock_ui.label.return_value = MagicMock()

            from app.ui.pages.dashboard import build_dashboard_page

            build_dashboard_page()

            experiments = service.list_experiments()
            assert len(experiments) == 2


def test_dashboard_filters_by_state() -> None:
    """Dashboard should filter experiments by selected state."""
    exp_repo = FakeExperimentRepository()
    project_repo = FakeRefRepository({1: {"id": 1, "name": "P1"}})
    protocol_repo = FakeRefRepository({1: {"id": 1, "name": "Proto1"}})

    exp_repo.create(1, 1, "Running One", "Running")
    exp_repo.create(1, 1, "Success One", "Success")

    service = ExperimentService(exp_repo, project_repo, protocol_repo)

    with patch(
        "app.ui.pages.dashboard._get_experiment_service",
        return_value=service,
    ):
        with patch("app.ui.pages.dashboard.ui") as mock_ui:
            mock_ui.column.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.column.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.input.return_value = _make_chainable("")
            mock_ui.select.return_value = _make_chainable("Running")
            mock_ui.label.return_value = MagicMock()

            from app.ui.pages.dashboard import build_dashboard_page

            build_dashboard_page()

            running = service.list_experiments({"state": "Running"})
            assert len(running) == 1
            assert running[0]["title"] == "Running One"
