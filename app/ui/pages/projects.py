from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.project_service import (
    ProjectDeletionError,
    ProjectNameError,
    ProjectNotFoundError,
    ProjectService,
    SqliteProjectRepository,
)
from app.ui import router
from app.ui.components.dialogs import ConfirmBlocked, confirm_delete_dialog
from app.ui.components.forms import dialog_actions, form_message
from app.ui.components.lists import search_toolbar
from app.ui.components.tables import add_view_delete_actions, entity_table


def _get_service() -> ProjectService:
    repo = SqliteProjectRepository(get_connection())
    return ProjectService(repo)


def build_projects_page() -> None:
    """Build the Projects CRUD page."""
    service = _get_service()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("Projects").classes("text-2xl font-semibold")

        # --- Toolbar: search + new ---
        search = search_toolbar(
            placeholder="Search projects...",
            action_label="New project",
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
    service: ProjectService,
    search_text: str,
    container: ui.column,
    refresh: callable,
) -> None:
    projects = service.list_projects({"search_text": search_text or None})

    if not projects:
        with container:
            ui.label("No projects found.").classes("text-slate-500 mt-4")
        return

    columns = [
        {"name": "name", "label": "Name", "field": "name", "align": "left"},
        {
            "name": "description",
            "label": "Description",
            "field": "description",
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
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "created_at": p.get("created_at", ""),
        }
        for p in projects
    ]

    with container:
        table = entity_table(columns, rows)

        def on_view(e) -> None:
            router.navigate("project_detail", project_id=e.args["id"])

        def on_delete(e) -> None:
            _open_delete_dialog(service, e.args["id"], e.args["name"], refresh)

        add_view_delete_actions(table, on_view, on_delete)


def _open_create_dialog(service: ProjectService, refresh: callable) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[32rem] max-w-full"):
        ui.label("New Project").classes("text-xl font-semibold")
        name_input = ui.input("Name *").props("outlined").classes("w-full")
        desc_input = ui.textarea("Description").props("outlined").classes("w-full")
        message = form_message()

        def save() -> None:
            try:
                service.create_project(
                    name=name_input.value,
                    description=desc_input.value,
                )
                dialog.close()
                ui.notify("Project created", type="positive")
                refresh()
            except ProjectNameError as error:
                message.text = str(error)

        dialog_actions("Create", save, dialog.close)

    dialog.open()


def _open_delete_dialog(
    service: ProjectService,
    project_id: int,
    project_name: str,
    refresh: callable,
) -> None:
    def do_delete() -> None:
        try:
            service.delete_project(project_id)
        except ProjectDeletionError:
            raise ConfirmBlocked(
                "Cannot delete this project because it has "
                "associated experiments. Remove them first."
            ) from None
        except ProjectNotFoundError:
            raise ConfirmBlocked("Project not found.") from None

    confirm_delete_dialog(
        title="Delete Project",
        question=f'Are you sure you want to delete "{project_name}"?',
        success_message="Project deleted",
        on_confirm=do_delete,
        on_success=refresh,
    )
