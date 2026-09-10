from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.protocol_service import (
    ProtocolNotFoundError,
    ProtocolService,
    ProtocolValidationError,
    SqliteProtocolRepository,
)
from app.ui import router


def _get_service() -> ProtocolService:
    repo = SqliteProtocolRepository(get_connection())
    return ProtocolService(repo)


def build_protocol_detail_page(protocol_id: int) -> None:
    """Build the protocol detail/edit page."""
    service = _get_service()

    try:
        protocol = service.get_protocol(protocol_id)
    except ProtocolNotFoundError:
        ui.notify("Protocol not found", type="negative")
        return

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        title_label = ui.label(protocol["name"]).classes("text-2xl font-semibold")

        created = (protocol.get("created_at") or "")[:10]
        modified = (protocol.get("modified_at") or "")[:10]
        meta = f"Created: {created}"
        if modified:
            meta += f"  ·  Modified: {modified}"
        ui.label(meta).classes("text-sm text-slate-500")

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
                ui.markdown(protocol.get("content_markdown", ""))
                .style("width: 50%")
                .classes("border rounded p-2 overflow-auto min-h-[8rem]")
            )

        def update_preview() -> None:
            preview.content = content_input.value or ""

        content_input.on_value_change(update_preview)

        message = ui.label().classes("text-negative mt-2")

        def save_protocol() -> None:
            try:
                service.update_protocol(
                    protocol_id=protocol_id,
                    name=name_input.value,
                    content_markdown=content_input.value,
                )
                title_label.text = name_input.value
                ui.notify("Protocol updated", type="positive")
            except (
                ProtocolValidationError,
                ProtocolNotFoundError,
            ) as error:
                message.text = str(error)

        with ui.row().classes("w-full justify-end mt-4"):
            ui.button("Save", on_click=save_protocol).props("color=primary")

        ui.button(
            icon="arrow_back",
            on_click=lambda: router.navigate("protocols"),
        ).props("flat round").classes("mt-4")
