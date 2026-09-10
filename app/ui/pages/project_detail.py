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
from app.ui.components.forms import (
    back_button,
    detail_save_row,
    form_message,
)
from app.ui.components.meta import entity_meta
from app.ui.components.tables import add_view_actions, entity_table


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

        entity_meta(project.get("created_at"), project.get("modified_at"))

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

        message = form_message()

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

        detail_save_row(save_project)

        _build_experiments_section(project_id)

        back_button("projects")


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
    table = entity_table(columns, rows)

    def on_view(e) -> None:
        router.navigate("experiment_detail", experiment_id=e.args["id"])

    add_view_actions(table, on_view)
