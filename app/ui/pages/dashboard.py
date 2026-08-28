from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.experiment_service import (
    ExperimentService,
    SqliteExperimentRepository,
)
from app.services.project_service import (
    SqliteProjectRepository,
)
from app.services.protocol_service import (
    SqliteProtocolRepository,
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

    with ui.column().classes("w-full max-w-5xl mx-auto mt-8 px-4"):
        ui.label("Experiments").classes("text-2xl font-semibold")

        with ui.row().classes("w-full items-center gap-4 mt-4"):
            search = ui.input(placeholder="Search experiments...").props(
                "outlined dense"
            ).classes("flex-1")
            state_filter = ui.select(
                options=["All", "Running", "Success", "Fail"],
                value="All",
                label="State",
            ).props("outlined dense").classes("w-40")

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
            )

        search.on_value_change(lambda: refresh())
        state_filter.on_value_change(lambda: refresh())
        refresh()


def _render_table(
    service: ExperimentService,
    search_text: str,
    state: str | None,
    container: ui.column,
) -> None:
    experiments = service.list_experiments(
        {"search_text": search_text or None, "state": state}
    )

    if not experiments:
        with container:
            ui.label("No experiments found.").classes(
                "text-slate-500 mt-4"
            )
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
        table = ui.table(
            columns=columns, rows=rows, row_key="id"
        ).classes("w-full cursor-pointer")

        table.add_slot(
            "body-cell-state",
            """
            <q-td :props="props">
                <q-badge :color="props.row.state === 'Running' ? 'blue' :
                                  props.row.state === 'Success' ? 'green' : 'red'"
                         :label="props.row.state" />
            </q-td>
            """,
        )

        def on_row_click(row: dict) -> None:
            ui.navigate.to(f"/experiments/{row['id']}")

        table.on("rowClick", on_row_click)


def build_experiment_detail_page(experiment_id: int) -> None:
    """Placeholder for experiment detail page (feature #22)."""
    with ui.column().classes("w-full max-w-5xl mx-auto mt-8 px-4"):
        ui.label(f"Experiment #{experiment_id}").classes(
            "text-2xl font-semibold"
        )
        ui.label("Detail page coming soon.").classes("text-slate-500 mt-4")
