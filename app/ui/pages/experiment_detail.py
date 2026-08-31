from __future__ import annotations

from pathlib import Path

from nicegui import ui

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
from app.services.export_service import ExportService
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
    export_service = ExportService(
        base_dir=base_dir,
        experiment_repo=experiment_repo,
        reagent_repo=reagent_repo,
        equipment_repo=equipment_repo,
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

    with ui.column().classes("w-full max-w-5xl mx-auto mt-8 px-4"):
        title = "New Experiment" if is_new else f"Experiment: {experiment['title']}"
        ui.label(title).classes("text-2xl font-semibold")

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
        ui.label("Reaction Onset").classes("font-semibold mt-4")
        reaction_input = (
            ui.textarea(
                value=experiment.get("reaction_onset", "") if experiment else ""
            )
            .props("outlined")
            .classes("w-full")
        )

        ui.label("Workup").classes("font-semibold mt-2")
        workup_input = (
            ui.textarea(value=experiment.get("workup", "") if experiment else "")
            .props("outlined")
            .classes("w-full")
        )

        ui.label("Purification").classes("font-semibold mt-2")
        purification_input = (
            ui.textarea(value=experiment.get("purification", "") if experiment else "")
            .props("outlined")
            .classes("w-full")
        )

        ui.label("Notes").classes("font-semibold mt-2")
        notes_input = (
            ui.textarea(value=experiment.get("notes", "") if experiment else "")
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
                        reaction_onset=reaction_input.value,
                        workup=workup_input.value,
                        purification=purification_input.value,
                        notes=notes_input.value,
                    )
                    ui.notify("Experiment created", type="positive")
                    ui.navigate.to(f"/experiments/{result['id']}")
                else:
                    exp_svc.update_experiment(
                        experiment_id,
                        project_id=project_select.value,
                        protocol_id=protocol_select.value,
                        title=title_input.value,
                        state=state_select.value,
                        reaction_onset=reaction_input.value,
                        workup=workup_input.value,
                        purification=purification_input.value,
                        notes=notes_input.value,
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
            _build_attachments_section(experiment_id, file_svc, conn)

            # --- Export section ---
            _build_export_section(experiment_id, export_svc)


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
                if r.get("amount_used") is not None:
                    ui.label(f"({r['amount_used']} {r.get('unit', '')})").classes(
                        "text-sm text-slate-500"
                    )
                smiles = r.get("smiles", "")
                if smiles:
                    svg = chem_svc.smiles_to_svg(smiles)
                    if svg:
                        ui.html(svg).classes("h-8")
    else:
        ui.label("_No reagents linked._").classes("text-slate-500 text-sm")

    all_reagents = inv_svc.list_reagents()
    reagent_options = {r["id"]: r["name"] for r in all_reagents}
    if reagent_options:
        with ui.row().classes("w-full items-end gap-2 mt-2"):
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
                ui.navigate.reload()

            ui.button("Link", on_click=link_reagent).props(
                "color=primary dense"
            )
    else:
        with ui.row().classes("items-center gap-1 mt-1"):
            ui.label("_No reagents in inventory._").classes("text-slate-500 text-sm")
            ui.link("Create some", "/inventory").classes(
                "text-sm text-primary"
            )

    # --- Equipment ---
    ui.label("Equipment").classes("font-semibold mt-2")
    equip_rows = resources.get("equipment", [])
    if equip_rows:
        for e in equip_rows:
            ui.label(f"- {e['name']}").classes("text-sm")
    else:
        ui.label("_No equipment linked._").classes("text-slate-500 text-sm")

    all_equipment = inv_svc.list_equipment()
    equipment_options = {eq["id"]: eq["name"] for eq in all_equipment}
    if equipment_options:
        with ui.row().classes("w-full items-end gap-2 mt-2"):
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
                ui.navigate.reload()

            ui.button("Link", on_click=link_equipment).props(
                "color=primary dense"
            )
    else:
        with ui.row().classes("items-center gap-1 mt-1"):
            ui.label("_No equipment in inventory._").classes(
                "text-slate-500 text-sm"
            )
            ui.link("Create some", "/inventory").classes(
                "text-sm text-primary"
            )


def _build_attachments_section(
    experiment_id: int,
    file_svc: FileService,
    conn,
) -> None:
    ui.separator().classes("mt-6")
    ui.label("Attachments").classes("text-xl font-semibold mt-4")

    attachments = list(attachment_repository.get_by_experiment(conn, experiment_id))

    if attachments:
        for att in attachments:
            with ui.row().classes("items-center gap-2"):
                ui.label(att["file_name"]).classes("text-sm")

                def make_delete(att_id: int = att["id"]) -> None:
                    attachment_repository.delete(conn, att_id)
                    ui.notify("Attachment deleted", type="positive")
                    ui.navigate.reload()

                ui.button(
                    icon="delete",
                    on_click=make_delete,
                ).props("flat dense color=negative").classes("text-xs")
    else:
        ui.label("_No attachments._").classes("text-slate-500 text-sm")

    def upload(event) -> None:
        uploaded = event.args[0]
        stored = file_svc.save_attachment(experiment_id, uploaded)
        attachment_repository.create(
            conn,
            experiment_id,
            uploaded.name,
            stored,
            Path(uploaded.name).suffix,
        )
        ui.notify("File uploaded", type="positive")
        ui.navigate.reload()

    ui.upload(
        label="Upload file",
        on_upload=upload,
    ).classes("w-full mt-2")


def _build_export_section(
    experiment_id: int,
    export_svc: ExportService,
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
