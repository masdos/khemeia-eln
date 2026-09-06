from __future__ import annotations

import base64
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
            created = experiment["created_at"][:10]
            modified = experiment["modified_at"][:10]
            ui.label(f"Created: {created}  ·  Modified: {modified}").classes(
                "text-sm text-slate-500"
            )

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

        ui.label("Experimental Procedure").classes("font-semibold mt-2")
        experimental_procedure_input = (
            ui.textarea(
                value=experiment.get("experimental_procedure_markdown", "")
                if experiment
                else ""
            )
            .props("outlined")
            .classes("w-full")
        )

        ui.label("Results").classes("font-semibold mt-2")
        result_input = (
            ui.textarea(
                value=experiment.get("result_markdown", "") if experiment else ""
            )
            .props("outlined")
            .classes("w-full")
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

        ui.button(
            "Save",
            on_click=save_experiment,
        ).classes("w-full mt-4")

        # --- Reagents & Equipment section ---
        if not is_new:
            _build_resources_section(experiment_id, inv_svc, conn, chem_svc)

            # --- Attachments section ---
            _build_attachments_section(experiment_id, file_svc, conn, base_dir)

            # --- Export section ---
            _build_export_section(experiment_id, export_svc, base_dir)

        ui.button(
            icon="arrow_back",
            on_click=lambda: router.navigate("dashboard"),
        ).props("flat round").classes("mt-4")


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
    reagent_rows = resources.get("reagents", [])
    if reagent_rows:
        for r in reagent_rows:
            with ui.row().classes("items-center gap-2"):
                ui.label(f"- {r['name']}").classes("text-sm")
                lot_number = r.get("lot_number", "")
                unit = r.get("unit", "")
                if r.get("amount_used") is not None:
                    label_text = f"({r['amount_used']} {unit}"
                    if lot_number:
                        label_text += f" - {lot_number}"
                    label_text += ")"
                    ui.label(label_text).classes("text-sm text-slate-500")
                elif lot_number:
                    ui.label(f" - {lot_number}").classes("text-sm text-slate-500")
                smiles = r.get("smiles", "")
                if smiles:
                    svg = chem_svc.smiles_to_svg(smiles)
                    if svg:
                        svg_clean = _strip_svg_rect(svg)
                        svg_b64 = base64.b64encode(svg.encode()).decode()
                        img_src = f"data:image/svg+xml;base64,{svg_b64}"
                        dialog = ui.dialog()
                        with dialog:
                            with ui.column().classes("bg-white p-4 gap-2"):
                                ui.image(img_src).style("width:500px; height:400px;")
                                ui.button(
                                    "Copy SVG",
                                    icon="content_copy",
                                    on_click=lambda s=svg_clean: ui.clipboard.write(s),
                                ).props("flat dense")
                        ui.button(
                            icon="image",
                            on_click=dialog.open,
                        ).props("flat dense color=primary").classes("text-sm")

                def _make_unlink(
                    _exp_id=experiment_id,
                    _reagent_id=r["id"],
                ) -> None:
                    inv_svc.unlink_reagent_from_experiment(_exp_id, _reagent_id)
                    ui.notify("Reagent unlinked", type="positive")
                    router.refresh()

                ui.button(
                    icon="delete",
                    on_click=_make_unlink,
                ).props("flat dense color=negative").classes("text-xs")
    else:
        ui.label("No reagents linked.").classes("text-slate-500 text-sm")

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
                    format="%.2f",
                )
                .props("outlined dense")
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

    # --- Equipment ---
    ui.label("Equipment").classes("font-semibold mt-2")
    equip_rows = resources.get("equipment", [])
    if equip_rows:
        for e in equip_rows:
            with ui.row().classes("items-center gap-2"):
                ui.label(f"- {e['name']}").classes("text-sm")

                def _make_unlink_equip(
                    _exp_id=experiment_id,
                    _equip_id=e["id"],
                ) -> None:
                    inv_svc.unlink_equipment_from_experiment(_exp_id, _equip_id)
                    ui.notify("Equipment unlinked", type="positive")
                    router.refresh()

                ui.button(
                    icon="delete",
                    on_click=_make_unlink_equip,
                ).props("flat dense color=negative").classes("text-xs")
    else:
        ui.label("No equipment linked.").classes("text-slate-500 text-sm")

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


def _build_attachments_section(
    experiment_id: int,
    file_svc: FileService,
    conn,
    base_dir: Path,
) -> None:
    ui.separator().classes("mt-6")
    ui.label("Attachments").classes("text-xl font-semibold mt-4")

    attachments = list(attachment_repository.get_by_experiment(conn, experiment_id))

    if attachments:
        for att in attachments:
            with ui.row().classes("items-center gap-2"):
                ui.label(f"- {att['file_name']}").classes("text-sm")

                def make_delete(
                    att_id: int = att["id"],
                    stored_name: str = att["stored_name"],
                    exp_id: int = experiment_id,
                ) -> None:
                    file_svc.delete_attachment(exp_id, stored_name)
                    attachment_repository.delete(conn, att_id)
                    ui.notify("Attachment deleted", type="positive")
                    router.refresh()

                ui.button(
                    icon="delete",
                    on_click=make_delete,
                ).props("flat dense color=negative").classes("text-xs")
    else:
        ui.label("No attachments.").classes("text-slate-500 text-sm")

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
        )
        ui.notify("File uploaded", type="positive")
        router.refresh()

    ui.upload(
        label="Upload file",
        on_upload=upload,
    ).classes("w-full mt-2")
    ui.label(
        f"Files are stored in ({base_dir / 'attachments' / str(experiment_id)})"
    ).classes("text-xs text-slate-400")


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

    def export_pdf() -> None:
        try:
            path = export_svc.export_experiment_pdf(experiment_id)
            ui.notify(f"Exported to {path.name}", type="positive")
        except Exception as e:
            ui.notify(str(e), type="negative")

    with ui.row().classes("gap-2"):
        ui.button("Export Markdown", on_click=export_md).props("outline")
        ui.button("Export PDF", on_click=export_pdf).props("outline")
    ui.label(f"Exports are stored in ({base_dir / 'exports'})").classes(
        "text-xs text-slate-400"
    )
