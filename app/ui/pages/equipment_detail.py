from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.inventory_service import (
    EquipmentNotFoundError,
    InventoryNameError,
    InventoryService,
    SqliteEquipmentRepository,
    SqliteReagentRepository,
)
from app.ui import router


def _get_service() -> InventoryService:
    conn = get_connection()
    return InventoryService(
        reagent_repo=SqliteReagentRepository(conn),
        equipment_repo=SqliteEquipmentRepository(conn),
    )


def build_equipment_detail_page(equipment_id: int) -> None:
    """Build the equipment detail/edit page."""
    service = _get_service()

    try:
        equipment = service.get_equipment(equipment_id)
    except EquipmentNotFoundError:
        ui.notify("Equipment not found", type="negative")
        return

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        title_label = ui.label(equipment["name"]).classes("text-2xl font-semibold")

        created = (equipment.get("created_at") or "")[:10]
        modified = (equipment.get("modified_at") or "")[:10]
        meta = f"Created: {created}"
        if modified:
            meta += f"  ·  Modified: {modified}"
        ui.label(meta).classes("text-sm text-slate-500")

        name_input = (
            ui.input("Name *", value=equipment["name"])
            .props("outlined")
            .classes("w-full")
        )
        desc_input = (
            ui.textarea("Description", value=equipment.get("description", ""))
            .props("outlined")
            .classes("w-full")
        )

        message = ui.label().classes("text-negative mt-2")

        def save_equipment() -> None:
            try:
                service.update_equipment(
                    equipment_id=equipment_id,
                    name=name_input.value,
                    description=desc_input.value,
                )
                title_label.text = name_input.value
                ui.notify("Equipment updated", type="positive")
            except (InventoryNameError, EquipmentNotFoundError) as error:
                message.text = str(error)

        with ui.row().classes("w-full justify-end mt-4"):
            ui.button("Save", on_click=save_equipment).props("color=primary")

        ui.button(
            icon="arrow_back",
            on_click=lambda: router.navigate("inventory"),
        ).props("flat round").classes("mt-4")
