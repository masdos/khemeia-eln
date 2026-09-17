from __future__ import annotations

from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from app.services.report_service import ReportService


class FakeReportRepository:
    """In-memory fake for ReportService tests."""

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
            "created_at": "2026-01-01",
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
            "created_at": "2026-01-01",
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


def _make_chainable(value: str = "") -> MagicMock:
    """Create a mock that supports .props().classes() chaining."""
    mock = MagicMock()
    mock.value = value
    mock.props.return_value = mock
    mock.classes.return_value = mock
    return mock


def _make_container() -> MagicMock:
    mock = _make_chainable()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class FakeExperimentService:
    """Test double listing experiments without SQLite."""

    def __init__(self, experiments: list[dict[str, Any]]) -> None:
        self._experiments = experiments

    def list_experiments(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        project_id = filters.get("project_id")
        if project_id is None:
            return []
        return [e for e in self._experiments if e.get("project_id") == project_id]


class FakeProjectRepo:
    """Test double listing projects without SQLite."""

    def __init__(self, projects: list[dict[str, Any]]) -> None:
        self._projects = projects

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._projects)


def _make_service() -> tuple[ReportService, FakeReportRepository]:
    repo = FakeReportRepository()
    return ReportService(repo), repo


def _mock_list_chrome(mock_ui: MagicMock, mock_lists_ui: MagicMock) -> None:
    mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
    mock_lists_ui.row.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_lists_ui.row.return_value.__exit__ = MagicMock(return_value=False)
    mock_lists_ui.input.return_value = _make_chainable("")
    mock_lists_ui.button.return_value = MagicMock()
    mock_ui.label.return_value = MagicMock()


def test_build_reports_page_lists_reports() -> None:
    """Page should list reports with their project names."""
    # given
    service, repo = _make_service()
    repo.seed(1, "Report A")
    repo.seed(2, "Report B")

    with patch("app.ui.pages.reports._get_service", return_value=service):
        with patch("app.ui.pages.reports.ui") as mock_ui:
            with patch("app.ui.components.lists.ui") as mock_lists_ui:
                with patch("app.ui.components.tables.ui") as mock_tables_ui:
                    _mock_list_chrome(mock_ui, mock_lists_ui)

                    from app.ui.pages.reports import build_reports_page

                    # when
                    build_reports_page()

                    # then
                    rows = mock_tables_ui.table.call_args.kwargs["rows"]
                    assert [r["title"] for r in rows] == ["Report A", "Report B"]
                    assert rows[0]["project"] == "Project 1"


def test_search_filters_reports_by_title() -> None:
    """Typing in search should refresh the table with matching reports."""
    # given
    service, repo = _make_service()
    repo.seed(1, "Monthly synthesis")
    repo.seed(1, "Weekly cleanup")

    with patch("app.ui.pages.reports._get_service", return_value=service):
        with patch("app.ui.pages.reports.ui") as mock_ui:
            with patch("app.ui.components.lists.ui") as mock_lists_ui:
                with patch("app.ui.components.tables.ui") as mock_tables_ui:
                    _mock_list_chrome(mock_ui, mock_lists_ui)
                    mock_lists_ui.input.return_value = _make_chainable("synthesis")

                    from app.ui.pages.reports import build_reports_page

                    # when
                    build_reports_page()
                    value_change = (
                        mock_lists_ui.input.return_value.on_value_change.call_args
                    )
                    search_handler = value_change.args[0]
                    search_handler()

                    # then — last render shows only the match
                    rows = mock_tables_ui.table.call_args.kwargs["rows"]
                    assert [r["title"] for r in rows] == ["Monthly synthesis"]


def test_view_action_navigates_to_report_detail() -> None:
    """View action should navigate to the report detail page."""
    # given
    service, repo = _make_service()
    report_id = repo.seed(1, "Report A")

    with patch("app.ui.pages.reports._get_service", return_value=service):
        with patch("app.ui.pages.reports.ui") as mock_ui:
            with patch("app.ui.pages.reports.router") as mock_router:
                with patch("app.ui.components.lists.ui") as mock_lists_ui:
                    with patch("app.ui.components.tables.ui") as mock_tables_ui:
                        _mock_list_chrome(mock_ui, mock_lists_ui)

                        from app.ui.pages.reports import build_reports_page

                        build_reports_page()

                        # when - the view action of the table row is triggered
                        table = mock_tables_ui.table.return_value.classes.return_value
                        view_handler = None
                        for call in table.on.call_args_list:
                            if call.args and call.args[0] == "view":
                                view_handler = call.args[1]
                                break

                        assert view_handler is not None
                        event = MagicMock()
                        event.args = {"id": report_id}
                        view_handler(event)

                        # then - navigates to the report detail page
                        mock_router.navigate.assert_called_once_with(
                            "report_detail", report_id=report_id
                        )


def test_delete_report_removes_it_from_service() -> None:
    """Confirming delete should remove the report and refresh."""
    # given
    service, repo = _make_service()
    report_id = repo.seed(1, "ToDelete")

    with patch("app.ui.pages.reports._get_service", return_value=service):
        with patch("app.ui.components.dialogs.ui") as mock_dialogs_ui:
            with patch("app.ui.components.forms.ui") as mock_forms_ui:
                mock_dialogs_ui.dialog.return_value.__enter__ = MagicMock(
                    return_value=MagicMock()
                )
                mock_dialogs_ui.dialog.return_value.__exit__ = MagicMock(
                    return_value=False
                )
                mock_dialogs_ui.card.return_value.__enter__ = MagicMock(
                    return_value=MagicMock()
                )
                mock_dialogs_ui.card.return_value.__exit__ = MagicMock(
                    return_value=False
                )
                mock_dialogs_ui.label.return_value = MagicMock()
                mock_forms_ui.label.return_value = MagicMock()
                mock_forms_ui.row.return_value.__enter__ = MagicMock(
                    return_value=MagicMock()
                )
                mock_forms_ui.row.return_value.__exit__ = MagicMock(return_value=False)
                mock_forms_ui.button.return_value = MagicMock()

                from app.ui.pages.reports import _open_delete_dialog

                refresh = MagicMock()
                _open_delete_dialog(service, report_id, "ToDelete", refresh)

                # when - the Delete button is pressed
                button_calls = mock_forms_ui.button.call_args_list
                delete_button = None
                for call in button_calls:
                    if call.args and call.args[0] == "Delete":
                        delete_button = call
                        break

                assert delete_button is not None
                delete_button.kwargs["on_click"]()

                # then - report is gone and the table refreshes
                assert service.list_reports() == []
                refresh.assert_called_once()


class _DialogContext:
    def __init__(self) -> None:
        self.project_select = _make_chainable(None)
        self.project_handler: Any = None
        self.experiment_select = _make_chainable([])
        self.title_input = _make_chainable("")
        self.message = _make_chainable("")
        self.create_handler: Any = None


def _run_dialog(
    service: ReportService,
    context: _DialogContext,
    action: Any,
    experiments: list[dict[str, Any]] | None = None,
    projects: list[dict[str, Any]] | None = None,
) -> None:
    """Open the create dialog and run the action with all patches active."""
    experiments = (
        experiments
        if experiments is not None
        else [
            {"id": 1, "title": "Exp A", "project_id": 10},
            {"id": 2, "title": "Exp B", "project_id": 20},
        ]
    )
    projects = (
        projects
        if projects is not None
        else [{"id": 10, "name": "Project X"}, {"id": 20, "name": "Project Y"}]
    )
    experiment_service = FakeExperimentService(experiments)
    project_repo = FakeProjectRepo(projects)

    with patch(
        "app.ui.pages.reports._get_experiment_service",
        return_value=experiment_service,
    ):
        with patch("app.ui.pages.reports._get_project_repo", return_value=project_repo):
            with patch("app.ui.pages.reports.ui") as mock_ui:
                with patch("app.ui.components.forms.ui") as mock_forms_ui:
                    mock_ui.dialog.return_value = _make_container()
                    mock_ui.card.return_value = _make_container()
                    mock_ui.label.return_value = MagicMock()
                    mock_ui.select.side_effect = [
                        context.project_select,
                        context.experiment_select,
                    ]
                    mock_ui.input.return_value = context.title_input

                    def capture_project_handler(handler: Any) -> MagicMock:
                        context.project_handler = handler
                        return MagicMock()

                    context.project_select.on_value_change.side_effect = (
                        capture_project_handler
                    )
                    mock_forms_ui.label.return_value = context.message
                    mock_forms_ui.row.return_value = _make_container()

                    def capture_button(*args: Any, **kwargs: Any) -> MagicMock:
                        if args and args[0] == "Create":
                            context.create_handler = kwargs.get("on_click")
                        return MagicMock()

                    mock_forms_ui.button.side_effect = capture_button

                    from app.ui.pages.reports import _open_create_dialog

                    _open_create_dialog(service, MagicMock())
                    action()


def test_dialog_populates_experiments_of_chosen_project() -> None:
    """Choosing a project should load only its experiments."""
    # given
    service, _repo = _make_service()
    context = _DialogContext()

    def choose_project() -> None:
        context.project_select.value = 20
        context.project_handler()

    # when
    _run_dialog(service, context, choose_project)

    # then
    set_call = context.experiment_select.set_options.call_args
    assert set(set_call.args[0]) == {2}
    assert set_call.kwargs.get("value") == []


def test_dialog_creates_report_and_opens_detail() -> None:
    """Creating should persist the report and navigate to its detail."""
    # given
    service, repo = _make_service()
    context = _DialogContext()

    def fill_and_create() -> None:
        context.project_select.value = 10
        context.project_handler()
        context.experiment_select.value = [1]
        context.title_input.value = "Monthly report"
        context.create_handler()

    # when
    with patch("app.ui.pages.reports.router") as mock_router:
        _run_dialog(service, context, fill_and_create)

        # then
        reports = service.list_reports()
        assert [r["title"] for r in reports] == ["Monthly report"]
        assert repo._links == {reports[0]["id"]: [1]}
        mock_router.navigate.assert_called_once_with(
            "report_detail", report_id=reports[0]["id"]
        )


def test_dialog_requires_project_before_creating() -> None:
    """Creating without a project should show a message."""
    # given
    service, _repo = _make_service()
    context = _DialogContext()

    # when
    _run_dialog(service, context, lambda: context.create_handler())

    # then
    assert context.message.text == "Select a project."
    assert service.list_reports() == []


def test_dialog_requires_experiments_before_creating() -> None:
    """Creating without experiments should show a message."""
    # given
    service, _repo = _make_service()
    context = _DialogContext()

    def skip_experiments() -> None:
        context.project_select.value = 10
        context.create_handler()

    # when
    _run_dialog(service, context, skip_experiments)

    # then
    assert context.message.text == "Select at least one experiment."
    assert service.list_reports() == []


def test_dialog_rejects_blank_title() -> None:
    """Creating with a blank title should show a message."""
    # given
    service, _repo = _make_service()
    context = _DialogContext()

    def blank_title() -> None:
        context.project_select.value = 10
        context.experiment_select.value = [1]
        context.title_input.value = "   "
        context.create_handler()

    # when
    _run_dialog(service, context, blank_title)

    # then
    assert context.message.text == "Report title must not be empty"
    assert service.list_reports() == []
