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


def _get_service() -> ProtocolService:
    repo = SqliteProtocolRepository(get_connection())
    return ProtocolService(repo)


def build_protocols_page() -> None:
    """Build the Protocols CRUD page."""
    service = _get_service()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("Protocols").classes("text-2xl font-semibold")

        with ui.row().classes("w-full items-center gap-4 mt-4"):
            search = (
                ui.input(placeholder="Search protocols...")
                .props("outlined dense")
                .classes("flex-1")
            )
            ui.button(
                "New protocol",
                on_click=lambda: _open_create_dialog(service, refresh),
            ).props("color=primary")

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


def _open_create_dialog(service: ProtocolService, refresh: callable) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[40rem] max-w-full"):
        ui.label("New Protocol").classes("text-xl font-semibold")
        name_input = ui.input("Name *").props("outlined").classes("w-full")

        state = {"textarea": None}

        def _insert(text):
            if state["textarea"]:
                t = state["textarea"]
                t.set_value(t.value + text)

        with ui.row().classes("w-full gap-1 mt-1"):
            ui.button(
                "H1", on_click=lambda: _insert("\n# Title\n")
            ).props("flat dense")
            ui.button(
                "H2", on_click=lambda: _insert("\n## Subtitle\n")
            ).props("flat dense")
            ui.button(
                "H3", on_click=lambda: _insert("\n### Subsubtitle\n")
            ).props("flat dense")
            ui.button(
                "Bold", on_click=lambda: _insert(" **text** ")
            ).props("flat dense")
            ui.button(
                "Italic", on_click=lambda: _insert(" _text_ ")
            ).props("flat dense")
            ui.button(
                "Table",
                on_click=lambda: _insert(
                    "\n| Column 1 | Column 2 |\n| --- | --- |\n| Data | Data |\n"
                ),
            ).props("flat dense")
            ui.button(
                "List", on_click=lambda: _insert("\n- Item 1\n- Item 2\n")
            ).props("flat dense")

        with ui.row().classes("w-full gap-4 items-start no-wrap"):
            content_input = (
                ui.textarea("Content (Markdown) *")
                .props("outlined")
                .style("width: 50%")
            )
            state["textarea"] = content_input

            preview = (
                ui.markdown("")
                .style("width: 50%")
                .classes("border rounded p-2 overflow-auto min-h-[8rem]")
            )

        def update_preview() -> None:
            content = content_input.value or ""
            preview.content = content

        content_input.on_value_change(update_preview)
        message = ui.label().classes("text-negative mt-2")

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

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close)
            ui.button("Create", on_click=save).props("color=primary")

    dialog.open()


def _open_edit_dialog(
    service: ProtocolService, protocol_id: int, refresh: callable
) -> None:
    try:
        protocol = service.get_protocol(protocol_id)
    except ProtocolNotFoundError:
        ui.notify("Protocol not found", type="negative")
        return

    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[40rem] max-w-full"):
        ui.label("Edit Protocol").classes("text-xl font-semibold")
        name_input = (
            ui.input("Name *", value=protocol["name"])
            .props("outlined")
            .classes("w-full")
        )

        state = {"textarea": None}

        def _insert(text):
            if state["textarea"]:
                t = state["textarea"]
                t.set_value(t.value + text)

        with ui.row().classes("w-full gap-1 mt-1"):
            ui.button(
                "H1", on_click=lambda: _insert("\n# Title\n")
            ).props("flat dense")
            ui.button(
                "H2", on_click=lambda: _insert("\n## Subtitle\n")
            ).props("flat dense")
            ui.button(
                "H3", on_click=lambda: _insert("\n### Subsubtitle\n")
            ).props("flat dense")
            ui.button(
                "Bold", on_click=lambda: _insert(" **text** ")
            ).props("flat dense")
            ui.button(
                "Italic", on_click=lambda: _insert(" _text_ ")
            ).props("flat dense")
            ui.button(
                "Table",
                on_click=lambda: _insert(
                    "\n| Column 1 | Column 2 |\n| --- | --- |\n| Data | Data |\n"
                ),
            ).props("flat dense")
            ui.button(
                "List", on_click=lambda: _insert("\n- Item 1\n- Item 2\n")
            ).props("flat dense")

        with ui.row().classes("w-full gap-4 items-start no-wrap"):
            content_input = (
                ui.textarea(
                    "Content (Markdown) *",
                    value=protocol.get("content_markdown", ""),
                )
                .props("outlined")
                .style("width: 50%")
            )
            state["textarea"] = content_input

            preview = (
                ui.markdown("")
                .style("width: 50%")
                .classes("border rounded p-2 overflow-auto min-h-[8rem]")
            )

        def update_preview() -> None:
            content = content_input.value or ""
            preview.content = content

        content_input.on_value_change(update_preview)
        update_preview()
        message = ui.label().classes("text-negative mt-2")

        def save() -> None:
            try:
                service.update_protocol(
                    protocol_id=protocol_id,
                    name=name_input.value,
                    content_markdown=content_input.value,
                )
                dialog.close()
                ui.notify("Protocol updated", type="positive")
                refresh()
            except (
                ProtocolValidationError,
                ProtocolNotFoundError,
            ) as error:
                message.text = str(error)

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close)
            ui.button("Save", on_click=save).props("color=primary")

    dialog.open()


def _open_delete_dialog(
    service: ProtocolService,
    protocol_id: int,
    protocol_name: str,
    refresh: callable,
) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[28rem] max-w-full"):
        ui.label("Delete Protocol").classes("text-xl font-semibold")
        ui.label(f'Are you sure you want to delete "{protocol_name}"?').classes(
            "text-slate-600 mt-2"
        )
        message = ui.label().classes("text-negative mt-2")

        def confirm_delete() -> None:
            try:
                service.delete_protocol(protocol_id)
                dialog.close()
                ui.notify("Protocol deleted", type="positive")
                refresh()
            except ProtocolDeletionError:
                message.text = (
                    "Cannot delete this protocol because it has "
                    "associated experiments. Remove them first."
                )
            except ProtocolNotFoundError:
                message.text = "Protocol not found."

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Delete", on_click=confirm_delete).props("color=negative")

    dialog.open()
