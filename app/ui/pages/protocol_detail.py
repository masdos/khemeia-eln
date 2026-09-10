from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.protocol_service import (
    ProtocolNotFoundError,
    ProtocolService,
    ProtocolValidationError,
    SqliteProtocolRepository,
)
from app.ui.components.forms import (
    back_button,
    detail_save_row,
    form_message,
)
from app.ui.components.markdown_editor import markdown_editor
from app.ui.components.meta import entity_meta


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

        entity_meta(protocol.get("created_at"), protocol.get("modified_at"))

        name_input = (
            ui.input("Name *", value=protocol["name"])
            .props("outlined")
            .classes("w-full")
        )

        content_input = markdown_editor(
            "Content (Markdown) *", protocol.get("content_markdown", "")
        )

        message = form_message()

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

        detail_save_row(save_protocol)

        back_button("protocols")
