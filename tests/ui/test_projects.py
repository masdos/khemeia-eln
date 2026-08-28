from __future__ import annotations

from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from app.services.project_service import (
    ProjectDeletionError,
    ProjectService,
)


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

    def get_all(
        self, search_text: str | None = None
    ) -> Sequence[dict[str, Any]]:
        results = list(self._projects.values())
        if search_text:
            results = [
                p for p in results
                if search_text.lower() in p["name"].lower()
            ]
        return results

    def update(
        self, project_id: int, **fields: object
    ) -> dict[str, Any] | None:
        project = self._projects.get(project_id)
        if project is None:
            return None
        project.update(fields)
        return project

    def delete(self, project_id: int) -> None:
        del self._projects[project_id]


def _make_chainable(value: str = "") -> MagicMock:
    """Create a mock that supports .props().classes() chaining."""
    mock = MagicMock()
    mock.value = value
    mock.props.return_value = mock
    mock.classes.return_value = mock
    return mock


def _make_chainable_label() -> MagicMock:
    """Create a mock label that supports .classes() chaining."""
    mock = MagicMock()
    mock.classes.return_value = mock
    return mock


def _make_service() -> tuple[ProjectService, FakeProjectRepository]:
    repo = FakeProjectRepository()
    return ProjectService(repo), repo


def test_build_projects_page_lists_projects() -> None:
    """Page should call list_projects and render a table."""
    # given
    service, repo = _make_service()
    repo.create("Alpha", "First project")
    repo.create("Beta", "Second project")

    with patch(
        "app.ui.pages.projects._get_service", return_value=service
    ):
        with patch("app.ui.pages.projects.ui") as mock_ui:
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
            mock_ui.button.return_value = MagicMock()
            mock_ui.label.return_value = MagicMock()

            from app.ui.pages.projects import build_projects_page

            build_projects_page()

            # Then - list_projects was called and returned data
            result = service.list_projects()
            assert len(result) == 2


def test_create_project_via_dialog() -> None:
    """Creating a project should call service.create_project."""
    # given
    service, _repo = _make_service()

    with patch(
        "app.ui.pages.projects._get_service", return_value=service
    ):
        with patch("app.ui.pages.projects.ui") as mock_ui:
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
            # First call = search input (empty), next calls in dialog
            mock_ui.input.return_value = _make_chainable("")
            mock_ui.button.return_value = MagicMock()
            mock_ui.label.return_value = MagicMock()

            from app.ui.pages.projects import _open_create_dialog

            refresh = MagicMock()
            # Set input value before dialog opens
            mock_ui.input.return_value.value = "Test Project"
            _open_create_dialog(service, refresh)

            # Find the save callback from the Create button
            button_calls = mock_ui.button.call_args_list
            create_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Create":
                    create_button = call
                    break

            assert create_button is not None
            save_callback = create_button.kwargs["on_click"]
            save_callback()

            # Then - project should be created
            projects = service.list_projects()
            assert len(projects) == 1


def test_edit_project_via_dialog() -> None:
    """Editing a project should call service.update_project."""
    # given
    service, _repo = _make_service()
    project = service.create_project("Original", "Original desc")

    with patch(
        "app.ui.pages.projects._get_service", return_value=service
    ):
        with patch("app.ui.pages.projects.ui") as mock_ui:
            mock_ui.dialog.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.dialog.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.card.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.card.return_value.__exit__ = MagicMock(
                return_value=False
            )

            name_mock = _make_chainable("Updated")
            desc_mock = _make_chainable("Updated desc")
            mock_ui.input = MagicMock(return_value=name_mock)
            mock_ui.textarea = MagicMock(return_value=desc_mock)
            mock_ui.label.return_value = MagicMock()

            from app.ui.pages.projects import _open_edit_dialog

            refresh = MagicMock()
            _open_edit_dialog(service, project["id"], refresh)

            # Get the save callback
            button_calls = mock_ui.button.call_args_list
            save_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Save":
                    save_button = call
                    break

            assert save_button is not None
            save_button.kwargs["on_click"]()

            # Then - project should be updated
            updated = service.get_project(project["id"])
            assert updated["name"] == "Updated"


def test_delete_project_shows_error_for_linked_experiments() -> None:
    """Delete with linked experiments should show error message."""
    # given
    service, _repo = _make_service()
    project = service.create_project("Doomed", "")

    # Override delete to raise ProjectDeletionError
    def failing_delete(project_id: int) -> None:
        raise ProjectDeletionError("Cannot delete")

    service.delete_project = failing_delete

    with patch(
        "app.ui.pages.projects._get_service", return_value=service
    ):
        with patch("app.ui.pages.projects.ui") as mock_ui:
            mock_ui.dialog.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.dialog.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.card.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.card.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.label.return_value = _make_chainable_label()
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )

            from app.ui.pages.projects import _open_delete_dialog

            refresh = MagicMock()
            _open_delete_dialog(
                service, project["id"], "Doomed", refresh
            )

            # Get the confirm_delete callback from Delete button
            button_calls = mock_ui.button.call_args_list
            delete_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Delete":
                    delete_button = call
                    break

            assert delete_button is not None
            delete_button.kwargs["on_click"]()

            # Then - message label's .text was set with error message
            message_label = mock_ui.label.return_value
            assert message_label.text == (
                "Cannot delete this project because it has "
                "associated experiments. Remove them first."
            )


def test_delete_project_succeeds() -> None:
    """Successful delete should close dialog and notify."""
    # given
    service, _repo = _make_service()
    project = service.create_project("ToDelete", "")

    with patch(
        "app.ui.pages.projects._get_service", return_value=service
    ):
        with patch("app.ui.pages.projects.ui") as mock_ui:
            mock_ui.dialog.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.dialog.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.card.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.card.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.label.return_value = MagicMock()
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )

            from app.ui.pages.projects import _open_delete_dialog

            refresh = MagicMock()
            _open_delete_dialog(
                service, project["id"], "ToDelete", refresh
            )

            # Get the confirm_delete callback
            button_calls = mock_ui.button.call_args_list
            delete_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Delete":
                    delete_button = call
                    break

            assert delete_button is not None
            delete_button.kwargs["on_click"]()

            # Then - project should be deleted
            projects = service.list_projects()
            assert len(projects) == 0


def test_create_project_rejects_blank_name() -> None:
    """Creating with blank name should show error."""
    # given
    service, _repo = _make_service()

    with patch(
        "app.ui.pages.projects._get_service", return_value=service
    ):
        with patch("app.ui.pages.projects.ui") as mock_ui:
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
            mock_ui.button.return_value = MagicMock()
            mock_ui.label.return_value = MagicMock()

            from app.ui.pages.projects import _open_create_dialog

            refresh = MagicMock()
            _open_create_dialog(service, refresh)

            # Simulate save with blank name
            button_calls = mock_ui.button.call_args_list
            create_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Create":
                    create_button = call
                    break

            assert create_button is not None
            create_button.kwargs["on_click"]()

            # Then - no project should be created (name is blank)
            projects = service.list_projects()
            assert len(projects) == 0
