from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.experiment_service import (
    ExperimentNotFoundError,
    ExperimentReferenceError,
    ExperimentService,
    ExperimentStateError,
    SqliteExperimentRepository,
)
from app.services.project_service import (
    SqliteProjectRepository,
)
from app.services.protocol_service import (
    SqliteProtocolRepository,
)
from app.ui import router
from app.ui.components.dialogs import ConfirmBlocked, confirm_delete_dialog
from app.ui.components.forms import dialog_actions, form_message
from app.ui.components.tables import (
    add_experiment_actions,
    add_state_badge,
    entity_table,
)


def _get_experiment_service() -> ExperimentService:
    conn = get_connection()
    return ExperimentService(
        experiment_repo=SqliteExperimentRepository(conn),
        project_repo=SqliteProjectRepository(conn),
        protocol_repo=SqliteProtocolRepository(conn),
    )


STATE_COLORS = {
    "Running": "blue",
    "Success": "green",
    "Fail": "red",
}


def build_dashboard_page() -> None:
    """Build the Dashboard page listing experiments."""
    service = _get_experiment_service()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("Experiments").classes("text-2xl font-semibold")

        with ui.row().classes("w-full items-center gap-4 mt-4"):
            search = (
                ui.input(placeholder="Search experiments...")
                .props("outlined dense")
                .classes("flex-1")
            )
            state_filter = (
                ui.select(
                    options=["All", "Running", "Success", "Fail"],
                    value="All",
                    label="State",
                )
                .props("outlined dense")
                .classes("w-40")
            )
            ui.button(
                "New experiment",
                on_click=lambda: _open_create_dialog(service, refresh),
            ).props("color=primary")

        table_container = ui.column().classes("w-full")

        def refresh() -> None:
            state_val = state_filter.value
            state = None if state_val == "All" else state_val
            table_container.clear()
            _render_table(
                service,
                search.value or "",
                state,
                table_container,
                refresh,
            )

        search.on_value_change(lambda: refresh())
        state_filter.on_value_change(lambda: refresh())
        refresh()


def _render_table(
    service: ExperimentService,
    search_text: str,
    state: str | None,
    container: ui.column,
    refresh,
) -> None:
    experiments = service.list_experiments(
        {"search_text": search_text or None, "state": state}
    )

    if not experiments:
        with container:
            ui.label("No experiments found.").classes("text-slate-500 mt-4")
        return

    columns = [
        {
            "name": "title",
            "label": "Title",
            "field": "title",
            "align": "left",
        },
        {
            "name": "state",
            "label": "State",
            "field": "state",
            "align": "center",
        },
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
            "id": e["id"],
            "title": e["title"],
            "state": e["state"],
            "project": e.get("project_name", ""),
            "created_at": e.get("created_at", ""),
        }
        for e in experiments
    ]

    with container:
        table = entity_table(columns, rows)
        add_state_badge(table)

        def on_view(e) -> None:
            router.navigate("experiment_detail", experiment_id=e.args["id"])

        def on_request_delete(e) -> None:
            _confirm_delete(service, e.args["id"], refresh)

        add_experiment_actions(table, on_view, on_request_delete)


def _confirm_delete(service: ExperimentService, experiment_id: int, refresh) -> None:
    def do_delete() -> None:
        try:
            service.delete_experiment(experiment_id)
        except ExperimentNotFoundError:
            raise ConfirmBlocked("Experiment not found.") from None

    confirm_delete_dialog(
        title="Delete this experiment?",
        question="This action cannot be undone.",
        success_message="Experiment deleted",
        on_confirm=do_delete,
        on_success=refresh,
    )


def _open_create_dialog(service: ExperimentService, refresh) -> None:
    conn = get_connection()
    projects = list(SqliteProjectRepository(conn).get_all())
    protocols = list(SqliteProtocolRepository(conn).get_all())

    project_options = {p["id"]: p["name"] for p in projects}
    protocol_options = {p["id"]: p["name"] for p in protocols}

    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[40rem] max-w-full"):
        ui.label("New Experiment").classes("text-xl font-semibold")

        project_select = (
            ui.select(
                options=project_options,
                label="Project *",
            )
            .props("outlined")
            .classes("w-full")
        )

        protocol_select = (
            ui.select(
                options=protocol_options,
                label="Protocol *",
            )
            .props("outlined")
            .classes("w-full")
        )

        title_input = ui.input("Title *").props("outlined").classes("w-full")

        state_select = (
            ui.select(
                options=["Running", "Success", "Fail"],
                value="Running",
                label="State *",
            )
            .props("outlined")
            .classes("w-full")
        )

        ui.label("Question").classes("font-semibold mt-4")
        question_input = ui.textarea().props("outlined").classes("w-full")

        message = form_message()

        def save() -> None:
            try:
                service.create_experiment(
                    project_id=project_select.value,
                    protocol_id=protocol_select.value,
                    title=title_input.value,
                    state=state_select.value,
                    question=question_input.value,
                )
                dialog.close()
                ui.notify("Experiment created", type="positive")
                refresh()
            except (
                ExperimentReferenceError,
                ExperimentStateError,
            ) as error:
                message.text = str(error)

        dialog_actions("Create", save, dialog.close)

    dialog.open()


def build_experiment_detail_page(experiment_id: int) -> None:
    """Placeholder for experiment detail page (feature #22)."""
    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label(f"Experiment #{experiment_id}").classes("text-2xl font-semibold")
        ui.label("Detail page coming soon.").classes("text-slate-500 mt-4")
