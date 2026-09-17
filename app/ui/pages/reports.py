from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.experiment_service import (
    ExperimentService,
    SqliteExperimentRepository,
)
from app.services.project_service import SqliteProjectRepository
from app.services.protocol_service import SqliteProtocolRepository
from app.services.report_service import (
    ReportNotFoundError,
    ReportService,
    ReportTitleError,
    SqliteReportRepository,
)
from app.ui import router
from app.ui.components.dialogs import ConfirmBlocked, confirm_delete_dialog
from app.ui.components.forms import dialog_actions, form_message
from app.ui.components.lists import search_toolbar
from app.ui.components.tables import add_view_delete_actions, entity_table


def _get_service() -> ReportService:
    repo = SqliteReportRepository(get_connection())
    return ReportService(repo)


def _get_experiment_service() -> ExperimentService:
    conn = get_connection()
    return ExperimentService(
        experiment_repo=SqliteExperimentRepository(conn),
        project_repo=SqliteProjectRepository(conn),
        protocol_repo=SqliteProtocolRepository(conn),
    )


def _get_project_repo() -> SqliteProjectRepository:
    return SqliteProjectRepository(get_connection())


def build_reports_page() -> None:
    """Build the Reports list page."""
    service = _get_service()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("Reports").classes("text-2xl font-semibold")

        # --- Toolbar: search + new ---
        search = search_toolbar(
            placeholder="Search reports...",
            action_label="New report",
            on_action=lambda: _open_create_dialog(service, refresh),
        )

        # --- Table ---
        table_container = ui.column().classes("w-full")

        def refresh() -> None:
            table_container.clear()
            _render_table(service, search.value or "", table_container, refresh)

        search.on_value_change(lambda: refresh())
        refresh()


def _render_table(
    service: ReportService,
    search_text: str,
    container: ui.column,
    refresh: callable,
) -> None:
    reports = service.list_reports({"search_text": search_text or None})

    if not reports:
        with container:
            ui.label("No reports found.").classes("text-slate-500 mt-4")
        return

    columns = [
        {"name": "title", "label": "Title", "field": "title", "align": "left"},
        {
            "name": "project",
            "label": "Project",
            "field": "project",
            "align": "left",
        },
        {
            "name": "created_at",
            "label": "Created",
            "field": "created_at",
            "align": "left",
        },
        {
            "name": "actions",
            "label": "Actions",
            "field": "actions",
            "align": "center",
        },
    ]

    rows = [
        {
            "id": r["id"],
            "title": r["title"],
            "project": r.get("project_name") or "",
            "created_at": (r.get("created_at") or "")[:10],
        }
        for r in reports
    ]

    with container:
        table = entity_table(columns, rows)

        def on_view(e) -> None:
            router.navigate("report_detail", report_id=e.args["id"])

        def on_delete(e) -> None:
            _open_delete_dialog(service, e.args["id"], e.args["title"], refresh)

        add_view_delete_actions(table, on_view, on_delete)


def _open_create_dialog(service: ReportService, refresh: callable) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[32rem] max-w-full"):
        ui.label("New Report").classes("text-xl font-semibold")

        project_choices = {
            project["id"]: project["name"]
            for project in _get_project_repo().get_all()
            if project.get("id") is not None
        }
        project_select = (
            ui.select(options=project_choices, value=None, label="Project")
            .props("outlined")
            .classes("w-full")
        )
        experiment_select = (
            ui.select(options={}, multiple=True, label="Experiments")
            .props("outlined")
            .classes("w-full")
        )
        title_input = ui.input("Title *").props("outlined").classes("w-full")
        message = form_message()

        def refresh_experiments() -> None:
            project_id = project_select.value
            experiment_service = _get_experiment_service()
            choices = (
                {
                    experiment["id"]: f"#{experiment['id']} {experiment['title']}"
                    for experiment in experiment_service.list_experiments(
                        {"project_id": project_id}
                    )
                }
                if project_id is not None
                else {}
            )
            experiment_select.set_options(choices, value=[])

        project_select.on_value_change(lambda: refresh_experiments())

        def save() -> None:
            project_id = project_select.value
            if project_id is None:
                message.text = "Select a project."
                return
            experiment_ids = list(experiment_select.value or [])
            if not experiment_ids:
                message.text = "Select at least one experiment."
                return
            try:
                created = service.create_report(
                    project_id=project_id,
                    title=title_input.value or "",
                    experiment_ids=experiment_ids,
                )
                dialog.close()
                ui.notify("Report created", type="positive")
                router.navigate("report_detail", report_id=created["id"])
            except ReportTitleError as error:
                message.text = str(error)

        dialog_actions("Create", save, dialog.close)

    dialog.open()


def _open_delete_dialog(
    service: ReportService,
    report_id: int,
    report_title: str,
    refresh: callable,
) -> None:
    def do_delete() -> None:
        try:
            service.delete_report(report_id)
        except ReportNotFoundError:
            raise ConfirmBlocked("Report not found.") from None

    confirm_delete_dialog(
        title="Delete Report",
        question=f'Are you sure you want to delete "{report_title}"?',
        success_message="Report deleted",
        on_confirm=do_delete,
        on_success=refresh,
    )
