from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.protocol_service import (
    ProtocolDeletionError,
    ProtocolNotFoundError,
    ProtocolService,
    ProtocolValidationError,
    SqliteProtocolRepository,
)
from app.ui import router
from app.ui.components.dialogs import ConfirmBlocked, confirm_delete_dialog
from app.ui.components.forms import dialog_actions, form_message
from app.ui.components.lists import search_toolbar
from app.ui.components.markdown_editor import markdown_editor
from app.ui.components.tables import add_view_delete_actions, entity_table


def _get_service() -> ProtocolService:
    repo = SqliteProtocolRepository(get_connection())
    return ProtocolService(repo)


def build_protocols_page() -> None:
    """Build the Protocols CRUD page."""
    service = _get_service()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("Protocols").classes("text-2xl font-semibold")

        search = search_toolbar(
            placeholder="Search protocols...",
            action_label="New protocol",
            on_action=lambda: _open_create_dialog(service, refresh),
        )

        table_container = ui.column().classes("w-full")

        def refresh() -> None:
            table_container.clear()
            _render_table(service, search.value or "", table_container, refresh)

        search.on_value_change(lambda: refresh())
        refresh()


def _render_table(
    service: ProtocolService,
    search_text: str,
    container: ui.column,
    refresh: callable,
) -> None:
    protocols = service.list_protocols({"search_text": search_text or None})

    if not protocols:
        with container:
            ui.label("No protocols found.").classes("text-slate-500 mt-4")
        return

    columns = [
        {"name": "name", "label": "Name", "field": "name", "align": "left"},
        {
            "name": "preview",
            "label": "Content",
            "field": "preview",
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
            "preview": (p.get("content_markdown") or "")[:80],
            "created_at": p.get("created_at", ""),
        }
        for p in protocols
    ]

    with container:
        table = entity_table(columns, rows)

        def on_view(e) -> None:
            router.navigate("protocol_detail", protocol_id=e.args["id"])

        def on_delete(e) -> None:
            _open_delete_dialog(service, e.args["id"], e.args["name"], refresh)

        add_view_delete_actions(table, on_view, on_delete)


def _open_create_dialog(service: ProtocolService, refresh: callable) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[40rem] max-w-full"):
        ui.label("New Protocol").classes("text-xl font-semibold")
        name_input = ui.input("Name *").props("outlined").classes("w-full")

        content_input = markdown_editor("Content (Markdown) *")

        message = form_message()

        def save() -> None:
            try:
                service.create_protocol(
                    name=name_input.value,
                    content_markdown=content_input.value,
                )
                dialog.close()
                ui.notify("Protocol created", type="positive")
                refresh()
            except ProtocolValidationError as error:
                message.text = str(error)

        dialog_actions("Create", save, dialog.close)

    dialog.open()


def _open_delete_dialog(
    service: ProtocolService,
    protocol_id: int,
    protocol_name: str,
    refresh: callable,
) -> None:
    def do_delete() -> None:
        try:
            service.delete_protocol(protocol_id)
        except ProtocolDeletionError:
            raise ConfirmBlocked(
                "Cannot delete this protocol because it has "
                "associated experiments. Remove them first."
            ) from None
        except ProtocolNotFoundError:
            raise ConfirmBlocked("Protocol not found.") from None

    confirm_delete_dialog(
        title="Delete Protocol",
        question=f'Are you sure you want to delete "{protocol_name}"?',
        success_message="Protocol deleted",
        on_confirm=do_delete,
        on_success=refresh,
    )
