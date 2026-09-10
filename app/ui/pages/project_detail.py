from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.experiment_service import (
    ExperimentService,
    SqliteExperimentRepository,
)
from app.services.project_service import (
    ProjectNameError,
    ProjectNotFoundError,
    ProjectService,
    SqliteProjectRepository,
)
from app.services.protocol_service import (
    SqliteProtocolRepository,
)
from app.ui import router


def _get_service() -> ProjectService:
    repo = SqliteProjectRepository(get_connection())
    return ProjectService(repo)


def _get_experiment_service() -> ExperimentService:
    conn = get_connection()
    return ExperimentService(
        experiment_repo=SqliteExperimentRepository(conn),
        project_repo=SqliteProjectRepository(conn),
        protocol_repo=SqliteProtocolRepository(conn),
    )


def build_project_detail_page(project_id: int) -> None:
    """Build the project detail/edit page."""
    service = _get_service()

    try:
        project = service.get_project(project_id)
    except ProjectNotFoundError:
        ui.notify("Project not found", type="negative")
        return

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        title_label = ui.label(project["name"]).classes("text-2xl font-semibold")

        created = (project.get("created_at") or "")[:10]
        modified = (project.get("modified_at") or "")[:10]
        meta = f"Created: {created}"
        if modified:
            meta += f"  ·  Modified: {modified}"
        ui.label(meta).classes("text-sm text-slate-500")

        name_input = (
            ui.input("Name *", value=project["name"])
            .props("outlined")
            .classes("w-full")
        )
        desc_input = (
            ui.textarea("Description", value=project.get("description", ""))
            .props("outlined")
            .classes("w-full")
        )

        message = ui.label().classes("text-negative mt-2")

        def save_project() -> None:
            try:
                service.update_project(
                    project_id=project_id,
                    name=name_input.value,
                    description=desc_input.value,
                )
                title_label.text = name_input.value
                ui.notify("Project updated", type="positive")
            except (ProjectNameError, ProjectNotFoundError) as error:
                message.text = str(error)

        with ui.row().classes("w-full justify-end mt-4"):
            ui.button("Save", on_click=save_project).props("color=primary")

        _build_experiments_section(project_id)

        ui.button(
            icon="arrow_back",
            on_click=lambda: router.navigate("projects"),
        ).props("flat round").classes("mt-4")


def _build_experiments_section(project_id: int) -> None:
    ui.separator().classes("mt-6")
    ui.label("Experiments").classes("text-xl font-semibold mt-4")

    service = _get_experiment_service()
    experiments = service.list_experiments({"project_id": project_id})

    if not experiments:
        ui.label("No experiments in this project.").classes("text-slate-500 mt-2")
        return

    columns = [
        {"name": "title", "label": "Title", "field": "title", "align": "left"},
        {"name": "state", "label": "State", "field": "state", "align": "center"},
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
            "created_at": (e.get("created_at") or "")[:10],
        }
        for e in experiments
    ]
    table = ui.table(
        columns=columns, rows=rows, row_key="id", pagination=10
    ).classes("w-full")

    table.add_slot(
        "body-cell-actions",
        """
        <q-td :props="props">
            <q-btn flat dense icon="visibility"
                    @click="() => $parent.$emit('view', props.row)" />
        </q-td>
        """,
    )

    def on_view(e) -> None:
        router.navigate("experiment_detail", experiment_id=e.args["id"])

    table.on("view", on_view)
