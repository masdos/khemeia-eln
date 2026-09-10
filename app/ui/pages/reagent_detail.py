from __future__ import annotations

from nicegui import ui

from app.database.connection import get_connection
from app.services.inventory_service import (
    InventoryNameError,
    InventoryService,
    ReagentNotFoundError,
    SqliteEquipmentRepository,
    SqliteReagentRepository,
)
from app.ui.components.forms import back_button, detail_save_row, form_message
from app.ui.components.ghs import ghs_checkboxes as ghs_checkbox_group
from app.ui.components.meta import entity_meta
from app.ui.components.tables import entity_table
from app.ui.pages.inventory import GHS_FIELDS


def _get_service() -> InventoryService:
    conn = get_connection()
    return InventoryService(
        reagent_repo=SqliteReagentRepository(conn),
        equipment_repo=SqliteEquipmentRepository(conn),
    )


def build_reagent_detail_page(reagent_id: int) -> None:
    """Build the reagent detail/edit page."""
    service = _get_service()

    try:
        reagent = service.get_reagent(reagent_id)
    except ReagentNotFoundError:
        ui.notify("Reagent not found", type="negative")
        return

    has_history = bool(service.get_reagent_history(reagent_id))

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        title_label = ui.label(reagent["name"]).classes("text-2xl font-semibold")

        entity_meta(reagent.get("created_at"), reagent.get("modified_at"))

        name = (
            ui.input("Name *", value=reagent["name"])
            .props("outlined")
            .classes("w-full")
        )
        cas = (
            ui.input("CAS Number", value=reagent.get("cas_number", "") or "")
            .props("outlined")
            .classes("w-full")
        )
        smiles = (
            ui.input("SMILES", value=reagent.get("smiles", "") or "")
            .props("outlined")
            .classes("w-full")
        )
        if has_history:
            cas.props("disable")
            smiles.props("disable")
            ui.label(
                "CAS and SMILES are locked because this reagent "
                "has been used in experiments."
            ).classes("text-sm text-slate-500")

        lot = (
            ui.input("Lot Number", value=reagent.get("lot_number", "") or "")
            .props("outlined")
            .classes("w-full")
        )
        supplier = (
            ui.input("Supplier", value=reagent.get("supplier", "") or "")
            .props("outlined")
            .classes("w-full")
        )
        expiry = (
            ui.input("Expiry Date", value=str(reagent.get("expiry_date") or ""))
            .props("outlined")
            .classes("w-full")
        )
        state = (
            ui.select(
                options=["solid", "liquid", "gas"],
                value=reagent.get("state"),
                label="Physical State",
            )
            .props("outlined")
            .classes("w-full")
        )
        purity_value = reagent.get("purity")
        purity = (
            ui.input(
                "Purity (%)",
                value="" if purity_value is None else str(purity_value),
            )
            .props("outlined")
            .classes("w-full")
        )
        in_stock = ui.checkbox("In Stock", value=bool(reagent.get("in_stock", True)))

        ghs_state = ghs_checkbox_group(GHS_FIELDS, reagent)

        message = form_message()

        def save() -> None:
            from datetime import date as date_type

            expiry_val = None
            if expiry.value:
                try:
                    expiry_val = date_type.fromisoformat(expiry.value)
                except ValueError:
                    message.text = "Invalid expiry date format"
                    return

            purity_val = None
            if purity.value:
                try:
                    purity_val = float(purity.value)
                except ValueError:
                    message.text = "Invalid purity value"
                    return

            try:
                service.update_reagent(
                    reagent_id,
                    name=name.value,
                    cas_number=cas.value,
                    smiles=smiles.value,
                    in_stock=in_stock.value,
                    lot_number=lot.value,
                    supplier=supplier.value,
                    expiry_date=expiry_val,
                    state=state.value,
                    purity=purity_val,
                    **{field: cb.value for field, cb in ghs_state.items()},
                )
                title_label.text = name.value
                ui.notify("Reagent updated", type="positive")
            except InventoryNameError as error:
                message.text = str(error)

        detail_save_row(save)

        _build_history_section(service, reagent_id, reagent["name"])

        back_button("inventory")


def _build_history_section(
    service: InventoryService, reagent_id: int, reagent_name: str
) -> None:
    ui.separator().classes("mt-6")
    ui.label(f"Usage history: {reagent_name}").classes("text-xl font-semibold mt-4")

    history = service.get_reagent_history(reagent_id)

    if not history:
        ui.label("No experiments use this reagent.").classes("text-slate-500 mt-2")
        return

    columns = [
        {
            "name": "title",
            "label": "Experiment",
            "field": "title",
            "align": "left",
        },
        {
            "name": "amount",
            "label": "Amount",
            "field": "amount",
            "align": "left",
        },
        {
            "name": "date",
            "label": "Date",
            "field": "date",
            "align": "left",
        },
    ]
    rows = [
        {
            "id": h["id"],
            "title": h.get("title", ""),
            "amount": (
                f"{h.get('amount_used', '')} {h.get('unit', '')}"
                if h.get("amount_used") is not None
                else "-"
            ),
            "date": h.get("created_at", ""),
        }
        for h in history
    ]
    entity_table(columns, rows)
