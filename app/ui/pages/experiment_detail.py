from __future__ import annotations

import base64
import logging
import re
from pathlib import Path

from nicegui import ui

from app.config import get_current_config
from app.database.connection import get_connection
from app.repositories import attachment_repository
from app.services.chemistry_service import ChemistryService
from app.services.experiment_service import (
    ExperimentNotFoundError,
    ExperimentReferenceError,
    ExperimentService,
    ExperimentStateError,
    SqliteExperimentRepository,
)
from app.services.export_service import (
    ExportService,
)
from app.services.export_service import (
    SqliteAttachmentRepository as ExportSqliteAttachmentRepository,
)
from app.services.export_service import (
    SqliteEquipmentRepository as ExportSqliteEquipmentRepository,
)
from app.services.export_service import (
    SqliteExperimentRepository as ExportSqliteExperimentRepository,
)
from app.services.export_service import (
    SqliteProjectRepository as ExportSqliteProjectRepository,
)
from app.services.export_service import (
    SqliteProtocolRepository as ExportSqliteProtocolRepository,
)
from app.services.export_service import (
    SqliteReagentRepository as ExportSqliteReagentRepository,
)
from app.services.file_service import FileService
from app.services.inventory_service import (
    InventoryService,
    SqliteEquipmentRepository,
    SqliteReagentRepository,
)
from app.services.project_service import (
    SqliteProjectRepository,
)
from app.services.protocol_service import (
    SqliteProtocolRepository,
)
from app.ui import router
from app.ui.components.export_location import (
    attachment_location_label,
    export_location_label,
)
from app.ui.components.forms import back_button, detail_save_row
from app.ui.components.markdown_editor import markdown_editor
from app.ui.components.meta import entity_meta
from app.ui.components.tables import entity_table

logger = logging.getLogger(__name__)

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

REAGENT_ACTIONS_SLOT = """
<q-td :props="props">
    <q-btn flat dense icon="image" color="primary"
            :disable="!props.row.has_structure"
            @click="() => $parent.$emit('structure', props.row)">
        <q-tooltip>View structure</q-tooltip>
    </q-btn>
    <q-btn flat dense icon="edit" color="primary"
            @click="() => $parent.$emit('edit', props.row)">
        <q-tooltip>Edit amount</q-tooltip>
    </q-btn>
    <q-btn flat dense icon="delete" color="negative"
            @click="() => $parent.$emit('unlink', props.row)">
        <q-tooltip>Unlink reagent</q-tooltip>
    </q-btn>
</q-td>
"""

EQUIPMENT_ACTIONS_SLOT = """
<q-td :props="props">
    <q-btn flat dense icon="delete" color="negative"
            @click="() => $parent.$emit('unlink', props.row)">
        <q-tooltip>Unlink equipment</q-tooltip>
    </q-btn>
</q-td>
"""

ATTACHMENT_ACTIONS_SLOT = """
<q-td :props="props">
    <q-btn flat dense icon="edit" color="primary"
            @click="() => $parent.$emit('edit', props.row)">
        <q-tooltip>Edit description</q-tooltip>
    </q-btn>
    <q-btn flat dense icon="delete" color="negative"
            @click="() => $parent.$emit('delete', props.row)">
        <q-tooltip>Delete attachment</q-tooltip>
    </q-btn>
</q-td>
"""


def _strip_svg_rect(svg: str) -> str:
    """Remove background <rect> elements from an RDKit-generated SVG."""
    return re.sub(r"<rect[^>]*>.*?</rect>\s*", "", svg, flags=re.DOTALL)


def _get_services(base_dir: Path) -> dict:
    conn = get_connection()
    experiment_repo = SqliteExperimentRepository(conn)
    project_repo = SqliteProjectRepository(conn)
    protocol_repo = SqliteProtocolRepository(conn)
    reagent_repo = SqliteReagentRepository(conn)
    equipment_repo = SqliteEquipmentRepository(conn)
    inventory_service = InventoryService(
        reagent_repo=reagent_repo,
        equipment_repo=equipment_repo,
    )
    file_service = FileService(base_dir)
    config = get_current_config()
    export_service = ExportService(
        base_dir=base_dir,
        experiment_repo=ExportSqliteExperimentRepository(conn),
        reagent_repo=ExportSqliteReagentRepository(conn),
        equipment_repo=ExportSqliteEquipmentRepository(conn),
        project_repo=ExportSqliteProjectRepository(conn),
        protocol_repo=ExportSqliteProtocolRepository(conn),
        attachment_repo=ExportSqliteAttachmentRepository(conn),
        user_name=config.user_name,
        user_email=config.user_email,
        user_institution=config.institution or "",
    )
    chemistry_service = ChemistryService()
    return {
        "experiment_service": ExperimentService(
            experiment_repo=experiment_repo,
            project_repo=project_repo,
            protocol_repo=protocol_repo,
        ),
        "inventory_service": inventory_service,
        "file_service": file_service,
        "export_service": export_service,
        "chemistry_service": chemistry_service,
        "connection": conn,
    }


def build_experiment_detail_page(
    experiment_id: int | None = None,
    base_dir: Path | None = None,
) -> None:
    """Build the experiment detail/edit page."""
    if base_dir is None:
        from app.bootstrap import run_bootstrap

        base_dir = run_bootstrap().base_dir

    services = _get_services(base_dir)
    exp_svc = services["experiment_service"]
    inv_svc = services["inventory_service"]
    file_svc = services["file_service"]
    export_svc = services["export_service"]
    chem_svc = services["chemistry_service"]
    conn = services["connection"]

    is_new = experiment_id is None
    experiment = None
    if not is_new:
        try:
            experiment = exp_svc.get_experiment(experiment_id)
        except ExperimentNotFoundError:
            ui.notify("Experiment not found", type="negative")
            return

    projects = list(SqliteProjectRepository(conn).get_all())
    protocols = list(SqliteProtocolRepository(conn).get_all())

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        title = "New Experiment" if is_new else f"{experiment['title']}"
        ui.label(title).classes("text-2xl font-semibold")

        if not is_new and experiment:
            entity_meta(experiment["created_at"], experiment["modified_at"])

        # --- Basic fields ---
        project_options = {p["id"]: p["name"] for p in projects}
        protocol_options = {p["id"]: p["name"] for p in protocols}

        project_select = (
            ui.select(
                options=project_options,
                value=experiment["project_id"] if experiment else None,
                label="Project *",
            )
            .props("outlined")
            .classes("w-full")
        )

        protocol_select = (
            ui.select(
                options=protocol_options,
                value=experiment["protocol_id"] if experiment else None,
                label="Protocol *",
            )
            .props("outlined")
            .classes("w-full")
        )

        title_input = (
            ui.input(
                "Title *",
                value=experiment["title"] if experiment else "",
            )
            .props("outlined")
            .classes("w-full")
        )

        state_select = (
            ui.select(
                options=["Running", "Success", "Fail"],
                value=experiment["state"] if experiment else "Running",
                label="State *",
            )
            .props("outlined")
            .classes("w-full")
        )

        # --- Notes fields ---
        ui.label("Question").classes("font-semibold mt-4")
        question_input = (
            ui.textarea(value=experiment.get("question", "") if experiment else "")
            .props("outlined")
            .classes("w-full")
        )

        experimental_procedure_input = markdown_editor(
            "Experimental Procedure",
            experiment.get("experimental_procedure_markdown", "") if experiment else "",
        )

        result_input = markdown_editor(
            "Result",
            experiment.get("result_markdown", "") if experiment else "",
        )

        ui.label("Conclusions").classes("font-semibold mt-2")
        conclusions_input = (
            ui.textarea(value=experiment.get("conclusions", "") if experiment else "")
            .props("outlined")
            .classes("w-full")
        )

        message = ui.label().classes("text-negative mt-2")

        # --- Save ---
        def save_experiment() -> None:
            try:
                if is_new:
                    result = exp_svc.create_experiment(
                        project_id=project_select.value,
                        protocol_id=protocol_select.value,
                        title=title_input.value,
                        state=state_select.value,
                        question=question_input.value,
                        experimental_procedure_markdown=experimental_procedure_input.value,
                        result_markdown=result_input.value,
                        conclusions=conclusions_input.value,
                    )
                    ui.notify("Experiment created", type="positive")
                    router.navigate("experiment_detail", experiment_id=result["id"])
                else:
                    exp_svc.update_experiment(
                        experiment_id,
                        project_id=project_select.value,
                        protocol_id=protocol_select.value,
                        title=title_input.value,
                        state=state_select.value,
                        question=question_input.value,
                        experimental_procedure_markdown=experimental_procedure_input.value,
                        result_markdown=result_input.value,
                        conclusions=conclusions_input.value,
                    )
                    ui.notify("Experiment updated", type="positive")
            except (
                ExperimentReferenceError,
                ExperimentStateError,
            ) as error:
                message.text = str(error)

        detail_save_row(save_experiment)

        # --- Reagents & Equipment section ---
        if not is_new:
            _build_resources_section(experiment_id, inv_svc, conn, chem_svc)

            # --- Attachments section ---
            _build_attachments_section(experiment_id, file_svc, conn, base_dir)

            # --- Export section ---
            _build_export_section(experiment_id, export_svc, base_dir)

        back_button("dashboard")


def _build_resources_section(
    experiment_id: int,
    inv_svc: InventoryService,
    conn,
    chem_svc: ChemistryService,
) -> None:
    ui.separator().classes("mt-6")
    ui.label("Resources").classes("text-xl font-semibold mt-4")

    resources = inv_svc.get_experiment_resources(experiment_id)

    # --- Reagents ---
    ui.label("Reagents").classes("font-semibold mt-2")
    all_reagents = inv_svc.list_reagents()
    reagent_options = {r["id"]: r["name"] for r in all_reagents}
    if reagent_options:
        with ui.row().classes("w-full items-center gap-2 mt-2"):
            reagent_select = (
                ui.select(
                    options=reagent_options,
                    label="Select reagent",
                )
                .props("outlined dense")
                .classes("flex-1")
            )
            reagent_amount = (
                ui.number(
                    label="Amount",
                    value=0,
                    min=0,
                )
                .props("outlined dense step=any")
                .classes("w-24")
            )
            reagent_unit = (
                ui.input(
                    label="Unit",
                    placeholder="g",
                )
                .props("outlined dense")
                .classes("w-20")
            )

            def link_reagent(
                _reagent_id=reagent_select,
                _amount=reagent_amount,
                _unit=reagent_unit,
            ) -> None:
                if _reagent_id.value is None:
                    ui.notify("Select a reagent", type="warning")
                    return
                inv_svc.link_reagent_to_experiment(
                    experiment_id,
                    _reagent_id.value,
                    _amount.value or 0,
                    _unit.value or "",
                )
                ui.notify("Reagent linked", type="positive")
                router.refresh()

            ui.button("Link", on_click=link_reagent).props("color=primary dense")
    else:
        with ui.row().classes("items-center gap-1 mt-1"):
            ui.label("No reagents in inventory.").classes("text-slate-500 text-sm")
            ui.button(
                "Create some",
                on_click=lambda: router.navigate("inventory"),
            ).props("flat dense").classes("text-sm text-primary p-0")

    reagent_rows = resources.get("reagents", [])
    if reagent_rows:
        reagent_by_id = {r["id"]: r for r in reagent_rows}
        columns = [
            {"name": "name", "label": "Name", "field": "name", "align": "left"},
            {
                "name": "amount",
                "label": "Amount Used",
                "field": "amount",
                "align": "left",
            },
            {"name": "lot", "label": "Lot", "field": "lot", "align": "left"},
            {"name": "ghs", "label": "GHS", "field": "ghs", "align": "left"},
            {
                "name": "actions",
                "label": "Actions",
                "field": "actions",
                "align": "center",
            },
        ]
        rows = []
        for r in reagent_rows:
            amount_used = r.get("amount_used")
            unit = r.get("unit", "") or ""
            if amount_used is not None:
                amount_text = f"{amount_used} {unit}".strip()
            else:
                amount_text = "-"
            ghs_labels = [label for field, _code, label in GHS_FIELDS if r.get(field)]
            rows.append(
                {
                    "id": r["id"],
                    "name": r.get("name", ""),
                    "amount": amount_text,
                    "lot": r.get("lot_number", "") or "-",
                    "ghs": ", ".join(ghs_labels) if ghs_labels else "-",
                    "has_structure": bool(r.get("smiles", "")),
                }
            )
        reagent_table = entity_table(columns, rows)
        reagent_table.add_slot("body-cell-actions", REAGENT_ACTIONS_SLOT)
        reagent_table.on(
            "structure",
            lambda e, _by_id=reagent_by_id: _open_structure_dialog(
                chem_svc, _by_id.get(e.args["id"], {}).get("smiles", "")
            ),
        )

        def _edit_reagent_amount(e) -> None:
            reagent = reagent_by_id.get(e.args["id"])
            if reagent is None:
                return
            dialog = ui.dialog()
            with dialog:
                with ui.card().classes("w-96"):
                    ui.label(f"Edit amount - {reagent.get('name', '')}").classes(
                        "font-semibold"
                    )
                    amount_input = (
                        ui.number(
                            label="Amount",
                            value=reagent.get("amount_used"),
                            min=0,
                        )
                        .props("outlined dense step=any")
                        .classes("w-full")
                    )
                    unit_input = (
                        ui.input(
                            label="Unit",
                            value=reagent.get("unit", "") or "",
                            placeholder="g",
                        )
                        .props("outlined dense")
                        .classes("w-full")
                    )
                    with ui.row().classes("w-full justify-end gap-2 mt-2"):

                        def save(
                            _reagent_id: int = reagent["id"],
                            _amount=amount_input,
                            _unit=unit_input,
                        ) -> None:
                            if _amount.value is None:
                                ui.notify("Enter an amount", type="warning")
                                return
                            inv_svc.link_reagent_to_experiment(
                                experiment_id,
                                _reagent_id,
                                _amount.value,
                                (_unit.value or "").strip(),
                            )
                            ui.notify("Amount updated", type="positive")
                            dialog.close()
                            router.refresh()

                        ui.button("Cancel", on_click=dialog.close).props("flat dense")
                        ui.button("Save", on_click=save).props("color=primary dense")
            dialog.open()

        def _unlink_reagent(e) -> None:
            inv_svc.unlink_reagent_from_experiment(experiment_id, e.args["id"])
            ui.notify("Reagent unlinked", type="positive")
            router.refresh()

        reagent_table.on("edit", _edit_reagent_amount)
        reagent_table.on("unlink", _unlink_reagent)
    else:
        ui.label("No reagents linked.").classes("text-slate-500 text-sm")

    # --- Equipment ---
    ui.label("Equipment").classes("font-semibold mt-2")
    all_equipment = inv_svc.list_equipment()
    equipment_options = {eq["id"]: eq["name"] for eq in all_equipment}
    if equipment_options:
        with ui.row().classes("w-full items-center gap-2 mt-2"):
            equipment_select = (
                ui.select(
                    options=equipment_options,
                    label="Select equipment",
                )
                .props("outlined dense")
                .classes("flex-1")
            )

            def link_equipment(_equip_id=equipment_select) -> None:
                if _equip_id.value is None:
                    ui.notify("Select equipment", type="warning")
                    return
                inv_svc.link_equipment_to_experiment(
                    experiment_id,
                    _equip_id.value,
                )
                ui.notify("Equipment linked", type="positive")
                router.refresh()

            ui.button("Link", on_click=link_equipment).props("color=primary dense")
    else:
        with ui.row().classes("items-center gap-1 mt-1"):
            ui.label("No equipment in inventory.").classes("text-slate-500 text-sm")
            ui.button(
                "Create some",
                on_click=lambda: router.navigate("inventory"),
            ).props("flat dense").classes("text-sm text-primary p-0")

    equip_rows = resources.get("equipment", [])
    if equip_rows:
        columns = [
            {"name": "name", "label": "Name", "field": "name", "align": "left"},
            {
                "name": "description",
                "label": "Description",
                "field": "description",
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
                "name": e.get("name", ""),
                "description": e.get("description", "") or "-",
            }
            for e in equip_rows
        ]
        equipment_table = entity_table(columns, rows)
        equipment_table.add_slot("body-cell-actions", EQUIPMENT_ACTIONS_SLOT)

        def _unlink_equipment(e) -> None:
            inv_svc.unlink_equipment_from_experiment(experiment_id, e.args["id"])
            ui.notify("Equipment unlinked", type="positive")
            router.refresh()

        equipment_table.on("unlink", _unlink_equipment)
    else:
        ui.label("No equipment linked.").classes("text-slate-500 text-sm")


def _open_structure_dialog(chem_svc: ChemistryService, smiles: str) -> None:
    if not smiles:
        ui.notify("No structure available", type="warning")
        return
    svg = chem_svc.smiles_to_svg(smiles)
    if not svg:
        ui.notify("Could not render structure", type="negative")
        return
    svg_clean = _strip_svg_rect(svg)
    svg_b64 = base64.b64encode(svg.encode()).decode()
    img_src = f"data:image/svg+xml;base64,{svg_b64}"
    dialog = ui.dialog()
    with dialog:
        with ui.column().classes("bg-white p-4 gap-2"):
            ui.image(img_src).style("width:500px; height:400px;")
            with ui.row().classes("w-full items-center gap-2"):
                ui.button(
                    "Copy SVG",
                    icon="content_copy",
                    on_click=lambda: ui.clipboard.write(svg_clean),
                ).props("flat dense")
                ui.button(
                    "Close",
                    icon="close",
                    on_click=dialog.close,
                ).props("flat dense")
    dialog.open()


def _build_attachments_section(
    experiment_id: int,
    file_svc: FileService,
    conn,
    base_dir: Path,
) -> None:
    ui.separator().classes("mt-6")
    ui.label("Attachments").classes("text-xl font-semibold mt-4")

    attachments = list(attachment_repository.get_by_experiment(conn, experiment_id))
    attachments_by_id = {att["id"]: att for att in attachments}

    description_input = (
        ui.input(
            label="Description",
            placeholder="Optional description",
        )
        .props("outlined dense")
        .classes("w-full mt-2")
    )

    async def upload(event) -> None:
        uploaded = event.file
        content = await uploaded.read()
        stored = file_svc.save_attachment_bytes(experiment_id, uploaded.name, content)
        attachment_repository.create(
            conn,
            experiment_id,
            uploaded.name,
            stored,
            Path(uploaded.name).suffix,
            (description_input.value or "").strip() or None,
        )
        description_input.value = ""
        ui.notify("File uploaded", type="positive")
        router.refresh()

    ui.upload(
        label="Upload file",
        on_upload=upload,
    ).classes("w-full mt-2")

    if attachments:
        columns = [
            {
                "name": "file_name",
                "label": "File Name",
                "field": "file_name",
                "align": "left",
            },
            {
                "name": "description",
                "label": "Description",
                "field": "description",
                "align": "left",
            },
            {
                "name": "extension",
                "label": "Extension",
                "field": "extension",
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
                "id": att["id"],
                "file_name": att["file_name"],
                "description": att["description"] or "No description",
                "extension": att["extension"],
            }
            for att in attachments
        ]
        attachment_table = entity_table(columns, rows)
        attachment_table.add_slot("body-cell-actions", ATTACHMENT_ACTIONS_SLOT)

        def _open_description_dialog(e) -> None:
            att = attachments_by_id.get(e.args["id"])
            if att is None:
                return
            dialog = ui.dialog()
            with dialog:
                with ui.card().classes("w-96"):
                    ui.label(f"Edit description - {att['file_name']}").classes(
                        "font-semibold"
                    )
                    desc_input = (
                        ui.textarea(value=att["description"] or "")
                        .props("outlined")
                        .classes("w-full")
                    )
                    with ui.row().classes("w-full justify-end gap-2 mt-2"):

                        def save(
                            _att_id: int = att["id"],
                            _input=desc_input,
                        ) -> None:
                            attachment_repository.update_description(
                                conn,
                                _att_id,
                                experiment_id,
                                (_input.value or "").strip() or None,
                            )
                            ui.notify("Description updated", type="positive")
                            dialog.close()
                            router.refresh()

                        ui.button("Cancel", on_click=dialog.close).props("flat dense")
                        ui.button("Save", on_click=save).props("color=primary dense")
            dialog.open()

        def _delete_attachment(e) -> None:
            att = attachments_by_id.get(e.args["id"])
            if att is None:
                return
            try:
                file_svc.delete_attachment(experiment_id, att["stored_name"])
            except OSError as error:
                logger.error(
                    "Attachment file deletion failed experiment_id=%s stored_name=%s "
                    "error=%s",
                    experiment_id,
                    att["stored_name"],
                    str(error),
                )
                ui.notify(f"Could not delete file: {error}", type="negative")
                return
            attachment_repository.delete(conn, att["id"], experiment_id)
            ui.notify("Attachment deleted", type="positive")
            router.refresh()

        attachment_table.on("edit", _open_description_dialog)
        attachment_table.on("delete", _delete_attachment)
    else:
        ui.label("No attachments.").classes("text-slate-500 text-sm")

    attachment_location_label(base_dir / "attachments" / str(experiment_id))


def _build_export_section(
    experiment_id: int,
    export_svc: ExportService,
    base_dir: Path,
) -> None:
    ui.separator().classes("mt-6")
    ui.label("Export").classes("text-xl font-semibold mt-4")

    def export_md() -> None:
        try:
            path = export_svc.export_experiment_markdown(experiment_id)
            ui.notify(f"Exported to {path.name}", type="positive")
        except Exception as e:
            ui.notify(str(e), type="negative")

    def export_docx() -> None:
        try:
            path = export_svc.export_experiment_docx(experiment_id)
            ui.notify(f"Exported to {path.name}", type="positive")
        except Exception as e:
            ui.notify(str(e), type="negative")

    def export_pdf() -> None:
        try:
            path = export_svc.export_experiment_pdf(experiment_id)
            ui.notify(f"Exported to {path.name}", type="positive")
        except Exception as e:
            ui.notify(str(e), type="negative")

    with ui.row().classes("gap-2"):
        ui.button("Markdown", on_click=export_md).props("color=primary")
        ui.button("DOCX", on_click=export_docx).props("color=primary")
        ui.button("PDF", on_click=export_pdf).props("color=primary")

    export_location_label(base_dir / "exports")
