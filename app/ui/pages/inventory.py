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

GHS_FIELDS = [
    ("is_explosive", "GHS01", "Explosive"),
    ("is_flammable", "GHS02", "Flammable"),
    ("is_oxidizer", "GHS03", "Oxidizer"),
    ("is_gas_under_pressure", "GHS04", "Gas under pressure"),
    ("is_corrosive", "GHS05", "Corrosive"),
    ("is_acute_toxic", "GHS06", "Acute toxicity"),
    ("is_harmful_irritant", "GHS07", "Harmful/Irritant"),
    ("is_health_hazard", "GHS08", "Health hazard"),
    ("is_environmental_hazard", "GHS09", "Environmental hazard"),
]


def _get_service() -> InventoryService:
    conn = get_connection()
    return InventoryService(
        reagent_repo=SqliteReagentRepository(conn),
        equipment_repo=SqliteEquipmentRepository(conn),
    )


def build_inventory_page() -> None:
    """Build the Inventory page with Reagents and Equipment sections."""
    service = _get_service()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("Inventory").classes("text-2xl font-semibold")

        tabs = ui.tabs().classes("mt-4")

        with tabs:
            reagents_tab = ui.tab("Reagents")
            equipment_tab = ui.tab("Equipment")

        with ui.tab_panels(tabs, value=reagents_tab).classes("w-full"):
            with ui.tab_panel(reagents_tab):
                _build_reagents_section(service)

            with ui.tab_panel(equipment_tab):
                _build_equipment_section(service)


def _build_reagents_section(service: InventoryService) -> None:
    reagent_container = ui.column().classes("w-full")

    def refresh_reagents() -> None:
        reagent_container.clear()
        with reagent_container:
            ui.button(
                "Add Reagent",
                on_click=lambda: _open_reagent_dialog(service, refresh_reagents),
            ).props("color=primary").classes("mb-4")

            _render_reagent_list(service, refresh_reagents)

    refresh_reagents()


def _render_reagent_list(service: InventoryService, refresh: callable) -> None:
    reagents = service._reagent_repo.get_all()

    if not reagents:
        ui.label("No reagents in inventory.").classes("text-slate-500")
        return

    columns = [
        {"name": "name", "label": "Name", "field": "name", "align": "left"},
        {
            "name": "cas",
            "label": "CAS",
            "field": "cas_number",
            "align": "left",
        },
        {
            "name": "stock",
            "label": "In Stock",
            "field": "in_stock",
            "align": "center",
        },
        {
            "name": "ghs",
            "label": "GHS",
            "field": "ghs",
            "align": "left",
        },
        {
            "name": "actions",
            "label": "Actions",
            "field": "actions",
            "align": "center",
        },
    ]

    rows = []
    for r in reagents:
        ghs_flags = [label for field, code, label in GHS_FIELDS if r.get(field)]
        rows.append(
            {
                "id": r["id"],
                "name": r["name"],
                "cas_number": r.get("cas_number", ""),
                "in_stock": "Yes" if r.get("in_stock") else "No",
                "ghs": ", ".join(ghs_flags) if ghs_flags else "-",
            }
        )

    table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

    table.add_slot(
        "body-cell-actions",
        """
        <q-td :props="props">
            <q-btn flat dense icon="history"
                   @click="() => $parent.$emit('history', props.row)" />
        </q-td>
        """,
    )

    def on_history(e) -> None:
        _open_history_dialog(service, e.args["id"], e.args["name"])

    table.on("history", on_history)


def _open_reagent_dialog(service: InventoryService, refresh: callable) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[40rem] max-w-full max-h-[80vh] overflow-y-auto"):
        ui.label("Add Reagent").classes("text-xl font-semibold")

        name = ui.input("Name *").props("outlined").classes("w-full")
        cas = ui.input("CAS Number").props("outlined").classes("w-full")
        smiles = ui.input("SMILES").props("outlined").classes("w-full")
        lot = ui.input("Lot Number").props("outlined").classes("w-full")
        supplier = ui.input("Supplier").props("outlined").classes("w-full")
        expiry = ui.input("Expiry Date").props("outlined").classes("w-full")
        state = (
            ui.select(
                options=["solid", "liquid", "gas"],
                label="Physical State",
            )
            .props("outlined")
            .classes("w-full")
        )
        purity = ui.input("Purity (%)").props("outlined").classes("w-full")
        in_stock = ui.checkbox("In Stock", value=True)

        ui.label("GHS Hazards").classes("font-semibold mt-4")
        ghs_checkboxes = {}
        with ui.row().classes("flex-wrap gap-4"):
            for field, code, label in GHS_FIELDS:
                ghs_checkboxes[field] = ui.checkbox(f"{code} - {label}", value=False)

        message = ui.label().classes("text-negative mt-2")

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
                service.add_reagent(
                    name=name.value,
                    cas_number=cas.value,
                    smiles=smiles.value,
                    in_stock=in_stock.value,
                    lot_number=lot.value,
                    supplier=supplier.value,
                    expiry_date=expiry_val,
                    state=state.value,
                    purity=purity_val,
                    **{field: cb.value for field, cb in ghs_checkboxes.items()},
                )
                dialog.close()
                ui.notify("Reagent added", type="positive")
                refresh()
            except InventoryNameError as error:
                message.text = str(error)

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close)
            ui.button("Save", on_click=save).props("color=primary")

    dialog.open()


def _open_history_dialog(
    service: InventoryService, reagent_id: int, reagent_name: str
) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[36rem] max-w-full"):
        ui.label(f"History: {reagent_name}").classes("text-xl font-semibold")

        try:
            history = service.get_reagent_history(reagent_id)
        except ReagentNotFoundError:
            ui.label("Reagent not found.").classes("text-negative")
            return

        if not history:
            ui.label("No experiments use this reagent.").classes("text-slate-500 mt-2")
        else:
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
            ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

        ui.button("Close", on_click=dialog.close).classes("mt-4")

    dialog.open()


def _build_equipment_section(service: InventoryService) -> None:
    equip_container = ui.column().classes("w-full")

    def refresh_equipment() -> None:
        equip_container.clear()
        with equip_container:
            ui.button(
                "Add Equipment",
                on_click=lambda: _open_equipment_dialog(service, refresh_equipment),
            ).props("color=primary").classes("mb-4")

            _render_equipment_list(service)

    refresh_equipment()


def _render_equipment_list(service: InventoryService) -> None:
    equipment = service._equipment_repo.get_all()

    if not equipment:
        ui.label("No equipment in inventory.").classes("text-slate-500")
        return

    columns = [
        {"name": "name", "label": "Name", "field": "name", "align": "left"},
        {
            "name": "description",
            "label": "Description",
            "field": "description",
            "align": "left",
        },
    ]

    rows = [
        {
            "id": e["id"],
            "name": e["name"],
            "description": e.get("description", ""),
        }
        for e in equipment
    ]

    ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")


def _open_equipment_dialog(service: InventoryService, refresh: callable) -> None:
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[32rem] max-w-full"):
        ui.label("Add Equipment").classes("text-xl font-semibold")

        name = ui.input("Name *").props("outlined").classes("w-full")
        desc = ui.textarea("Description").props("outlined").classes("w-full")
        message = ui.label().classes("text-negative mt-2")

        def save() -> None:
            try:
                service.add_equipment(
                    name=name.value,
                    description=desc.value,
                )
                dialog.close()
                ui.notify("Equipment added", type="positive")
                refresh()
            except InventoryNameError as error:
                message.text = str(error)

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close)
            ui.button("Save", on_click=save).props("color=primary")

    dialog.open()
