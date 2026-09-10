from __future__ import annotations

from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from app.services.experiment_service import ExperimentService
from app.services.project_service import ProjectService


class FakeProjectRepository:
    """In-memory fake for ProjectService tests."""

    def __init__(self) -> None:
        self._projects: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def create(self, name: str, description: str = "") -> int:
        project_id = self._next_id
        self._next_id += 1
        self._projects[project_id] = {
            "id": project_id,
            "name": name,
            "description": description,
            "created_at": "2026-01-01",
        }
        return project_id

    def get_by_id(self, project_id: int) -> dict[str, Any] | None:
        return self._projects.get(project_id)

    def update(self, project_id: int, **fields: object) -> dict[str, Any] | None:
        project = self._projects.get(project_id)
        if project is None:
            return None
        project.update(fields)
        return project


def _make_chainable(value: str = "") -> MagicMock:
    """Create a mock that supports .props().classes() chaining."""
    mock = MagicMock()
    mock.value = value
    mock.props.return_value = mock
    mock.classes.return_value = mock
    return mock


def _make_service() -> ProjectService:
    return ProjectService(FakeProjectRepository())


def _mock_page_chrome(mock_ui: MagicMock) -> None:
    mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
    mock_ui.row.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ui.row.return_value.__exit__ = MagicMock(return_value=False)
    mock_ui.label.return_value = MagicMock()
    mock_ui.button.return_value = MagicMock()


def test_detail_page_prefills_current_values() -> None:
    """Detail page must show current name and description in inputs."""
    # given
    service = _make_service()
    project = service.create_project("Alpha", "First project")

    with patch("app.ui.pages.project_detail._get_service", return_value=service):
        with patch(
            "app.ui.pages.project_detail._get_experiment_service",
            return_value=_mock_experiment_service(),
        ):
            with patch("app.ui.pages.project_detail.ui") as mock_ui:
                _mock_page_chrome(mock_ui)
                mock_ui.input = MagicMock(return_value=_make_chainable("Alpha"))
                mock_ui.textarea = MagicMock(
                    return_value=_make_chainable("First project")
                )

                from app.ui.pages.project_detail import build_project_detail_page

                # when
                build_project_detail_page(project["id"])

            # then
            assert mock_ui.input.call_args.kwargs["value"] == "Alpha"
            assert mock_ui.textarea.call_args.kwargs["value"] == "First project"


def test_saving_from_detail_updates_project() -> None:
    """Saving from the detail page must persist the new values."""
    # given
    service = _make_service()
    project = service.create_project("Alpha", "First project")

    with patch("app.ui.pages.project_detail._get_service", return_value=service):
        with patch(
            "app.ui.pages.project_detail._get_experiment_service",
            return_value=_mock_experiment_service(),
        ):
            with patch("app.ui.pages.project_detail.ui") as mock_ui:
                _mock_page_chrome(mock_ui)
                mock_ui.input = MagicMock(return_value=_make_chainable("Renamed"))
                mock_ui.textarea = MagicMock(
                    return_value=_make_chainable("Renamed desc")
                )

                from app.ui.pages.project_detail import build_project_detail_page

                build_project_detail_page(project["id"])

                # when - the Save button is clicked
                save_button = None
                for call in mock_ui.button.call_args_list:
                    if call.args and call.args[0] == "Save":
                        save_button = call
                        break

                assert save_button is not None
                save_button.kwargs["on_click"]()

                # then
                updated = service.get_project(project["id"])
                assert updated["name"] == "Renamed"
                mock_ui.notify.assert_called_once_with(
                    "Project updated", type="positive"
                )


def test_back_button_returns_to_projects_list() -> None:
    """Back button must navigate to the projects list."""
    # given
    service = _make_service()
    project = service.create_project("Alpha", "First project")

    with patch("app.ui.pages.project_detail._get_service", return_value=service):
        with patch(
            "app.ui.pages.project_detail._get_experiment_service",
            return_value=_mock_experiment_service(),
        ):
            with patch("app.ui.pages.project_detail.ui") as mock_ui:
                with patch("app.ui.pages.project_detail.router") as mock_router:
                    _mock_page_chrome(mock_ui)
                    mock_ui.input = MagicMock(return_value=_make_chainable("Alpha"))
                    mock_ui.textarea = MagicMock(
                        return_value=_make_chainable("First project")
                    )

                    from app.ui.pages.project_detail import build_project_detail_page

                    build_project_detail_page(project["id"])

                    # when - the back button is clicked
                    back_button = None
                    for call in mock_ui.button.call_args_list:
                        if call.kwargs.get("icon") == "arrow_back":
                            back_button = call
                            break

                    assert back_button is not None
                    back_button.kwargs["on_click"]()

                    # then
                    mock_router.navigate.assert_called_once_with("projects")


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
        }
        return exp_id

    def get_all(
        self,
        state: str | None = None,
        project_id: int | None = None,
        search_text: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        results = list(self._experiments.values())
        if project_id is not None:
            results = [e for e in results if e["project_id"] == project_id]
        return results


class FakeRefRepository:
    def __init__(self, items: dict[int, dict[str, Any]]) -> None:
        self._items = items

    def get_by_id(self, entity_id: int) -> dict[str, Any] | None:
        return self._items.get(entity_id)


def _make_experiment_service(
    exp_repo: FakeExperimentRepository,
) -> ExperimentService:
    return ExperimentService(
        exp_repo,
        FakeRefRepository({1: {"id": 1, "name": "P1"}}),
        FakeRefRepository({1: {"id": 1, "name": "Proto1"}}),
    )


def _mock_experiment_service() -> ExperimentService:
    return _make_experiment_service(FakeExperimentRepository())


def test_experiments_table_lists_project_experiments() -> None:
    """Experiments section must list only this project experiments."""
    # given
    service = _make_service()
    exp_repo = FakeExperimentRepository()
    exp_repo.create(1, 1, "Exp A", "Running")
    exp_repo.create(2, 1, "Other project exp", "Running")
    exp_service = _make_experiment_service(exp_repo)

    with patch(
        "app.ui.pages.project_detail._get_service", return_value=service
    ):
        with patch(
            "app.ui.pages.project_detail._get_experiment_service",
            return_value=exp_service,
        ):
            with patch("app.ui.pages.project_detail.ui") as mock_ui:
                _mock_page_chrome(mock_ui)
                mock_ui.input = MagicMock(return_value=_make_chainable("Alpha"))
                mock_ui.textarea = MagicMock(
                    return_value=_make_chainable("First project")
                )

                from app.ui.pages.project_detail import build_project_detail_page

                project = service.create_project("Alpha", "First project")

                # when
                build_project_detail_page(project["id"])

                # then
                rows = mock_ui.table.call_args.kwargs["rows"]
                assert [r["title"] for r in rows] == ["Exp A"]


def test_experiment_view_action_navigates_to_detail() -> None:
    """Experiment view action must navigate to the experiment detail."""
    # given
    service = _make_service()
    exp_repo = FakeExperimentRepository()
    exp_repo.create(1, 1, "Exp A", "Running")
    exp_service = _make_experiment_service(exp_repo)

    with patch(
        "app.ui.pages.project_detail._get_service", return_value=service
    ):
        with patch(
            "app.ui.pages.project_detail._get_experiment_service",
            return_value=exp_service,
        ):
            with patch("app.ui.pages.project_detail.ui") as mock_ui:
                with patch(
                    "app.ui.pages.project_detail.router"
                ) as mock_router:
                    _mock_page_chrome(mock_ui)
                    mock_ui.input = MagicMock(
                        return_value=_make_chainable("Alpha")
                    )
                    mock_ui.textarea = MagicMock(
                        return_value=_make_chainable("First project")
                    )

                    from app.ui.pages.project_detail import (
                        build_project_detail_page,
                    )

                    project = service.create_project("Alpha", "First project")
                    build_project_detail_page(project["id"])

                    # when - the view action of the experiment row is triggered
                    table = mock_ui.table.return_value.classes.return_value
                    view_handler = None
                    for call in table.on.call_args_list:
                        if call.args and call.args[0] == "view":
                            view_handler = call.args[1]
                            break

                    assert view_handler is not None
                    event = MagicMock()
                    event.args = {"id": 1}
                    view_handler(event)

                    # then
                    mock_router.navigate.assert_called_with(
                        "experiment_detail", experiment_id=1
                    )


def test_detail_notifies_when_project_missing() -> None:
    """Detail page must notify when the project does not exist."""
    # given
    service = _make_service()

    with patch("app.ui.pages.project_detail._get_service", return_value=service):
        with patch("app.ui.pages.project_detail.ui") as mock_ui:
            from app.ui.pages.project_detail import build_project_detail_page

            # when
            build_project_detail_page(999)

            # then
            mock_ui.notify.assert_called_once_with(
                "Project not found", type="negative"
            )
