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


def _get_service() -> ProjectService:
    repo = SqliteProjectRepository(get_connection())
    return ProjectService(repo)


def build_projects_page() -> None:
    """Build the Projects CRUD page."""
    service = _get_service()

    with ui.column().classes("w-full max-w-5xl mx-auto mt-8 px-4"):
        ui.label("Projects").classes("text-2xl font-semibold")

        # --- Toolbar: search + new ---
        with ui.row().classes("w-full items-center gap-4 mt-4"):
            search = (
                ui.input(placeholder="Search projects...")
                .props("outlined dense")
                .classes("flex-1")
            )
            ui.button(
                "New project",
                on_click=lambda: _open_create_dialog(service, refresh),
            ).props("color=primary")

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
        table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

        table.add_slot(
            "body-cell-actions",
            """
            <q-td :props="props">
                <q-btn flat dense icon="edit"
                       @click="() => $parent.$emit('edit', props.row)" />
                <q-btn flat dense icon="delete" color="negative"
                       @click="() => $parent.$emit('delete', props.row)" />
            </q-td>
            """,
        )

        def on_edit(e) -> None:
            _open_edit_dialog(service, e.args["id"], refresh)

        def on_delete(e) -> None:
            _open_delete_dialog(service, e.args["id"], e.args["name"], refresh)

        table.on("edit", on_edit)
        table.on("delete", on_delete)


def _open_create_dialog(service: ProjectService, refresh: callable) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[32rem] max-w-full"):
        ui.label("New Project").classes("text-xl font-semibold")
        name_input = ui.input("Name *").props("outlined").classes("w-full")
        desc_input = ui.textarea("Description").props("outlined").classes("w-full")
        message = ui.label().classes("text-negative mt-2")

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

        ui.button("Create", on_click=save).classes("w-full mt-2")

    dialog.open()


def _open_edit_dialog(
    service: ProjectService, project_id: int, refresh: callable
) -> None:
    try:
        project = service.get_project(project_id)
    except ProjectNotFoundError:
        ui.notify("Project not found", type="negative")
        return

    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[32rem] max-w-full"):
        ui.label("Edit Project").classes("text-xl font-semibold")
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

        def save() -> None:
            try:
                service.update_project(
                    project_id=project_id,
                    name=name_input.value,
                    description=desc_input.value,
                )
                dialog.close()
                ui.notify("Project updated", type="positive")
                refresh()
            except (ProjectNameError, ProjectNotFoundError) as error:
                message.text = str(error)

        ui.button("Save", on_click=save).classes("w-full mt-2")

    dialog.open()


def _open_delete_dialog(
    service: ProjectService,
    project_id: int,
    project_name: str,
    refresh: callable,
) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[28rem] max-w-full"):
        ui.label("Delete Project").classes("text-xl font-semibold")
        ui.label(f'Are you sure you want to delete "{project_name}"?').classes(
            "text-slate-600 mt-2"
        )
        message = ui.label().classes("text-negative mt-2")

        def confirm_delete() -> None:
            try:
                service.delete_project(project_id)
                dialog.close()
                ui.notify("Project deleted", type="positive")
                refresh()
            except ProjectDeletionError:
                message.text = (
                    "Cannot delete this project because it has "
                    "associated experiments. Remove them first."
                )
            except ProjectNotFoundError:
                message.text = "Project not found."

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Delete", on_click=confirm_delete).props("color=negative")

    dialog.open()
