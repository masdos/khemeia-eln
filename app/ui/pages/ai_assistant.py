from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from nicegui import ui

from app.config import get_current_config
from app.database.connection import get_connection
from app.services.ai_service import AIService
from app.services.experiment_service import (
    ExperimentService,
    SqliteExperimentRepository,
)
from app.services.export_service import (
    ExportService,
    SqliteAttachmentRepository,
    SqliteReportRepository,
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
from app.services.ollama_client import OllamaClient
from app.services.project_service import SqliteProjectRepository
from app.services.protocol_service import SqliteProtocolRepository
from app.ui import router

logger = logging.getLogger(__name__)

NO_AI_WARNING = (
    "Ollama is not ready. Open AI Reports to install Ollama and download a local model."
)
SELECTION_REQUIRED = "Select at least one experiment."
DRAFT_REQUIRED = "Generate a draft before exporting."


def get_experiment_choices(experiment_service: ExperimentService) -> dict[int, str]:
    """Return experiment id to display label mapping for the selector."""
    choices: dict[int, str] = {}
    for experiment in experiment_service.list_experiments({}):
        experiment_id = experiment.get("id")
        title = experiment.get("title") or f"Experiment {experiment_id}"
        if experiment_id is not None:
            choices[experiment_id] = f"#{experiment_id} {title}"
    return choices


def collect_experiments_data(
    experiment_service: ExperimentService,
    experiment_ids: Sequence[int],
) -> list[dict[str, Any]]:
    """Return full experiment records for the selected ids, skipping missing."""
    collected: list[dict[str, Any]] = []
    for experiment_id in experiment_ids:
        experiment = experiment_service.get_experiment(experiment_id)
        if experiment is not None:
            collected.append(experiment)
    return collected


def generate_draft(
    ai_service: AIService,
    experiments_data: Sequence[Mapping[str, Any]],
) -> str | None:
    """Generate a report draft, returning None when AI is not ready."""
    draft = ai_service.generate_report(experiments_data)
    if draft is None:
        logger.warning("AI draft generation returned no content")
        return None
    logger.info("AI draft generated count=%s", len(experiments_data))
    return draft


def export_draft(
    export_service: ExportService,
    markdown_content: str,
    experiment_ids: Sequence[int],
    file_format: str,
) -> Path:
    """Export the edited draft as Markdown or PDF and return its path."""
    if file_format == "pdf":
        return export_service.export_ai_report_pdf(markdown_content, experiment_ids)
    return export_service.export_ai_report_markdown(markdown_content, experiment_ids)


def _get_services(base_dir: Path) -> dict[str, Any]:
    conn = get_connection()
    experiment_service = ExperimentService(
        experiment_repo=SqliteExperimentRepository(conn),
        project_repo=SqliteProjectRepository(conn),
        protocol_repo=SqliteProtocolRepository(conn),
    )
    config = get_current_config()
    export_service = ExportService(
        base_dir=base_dir,
        experiment_repo=ExportSqliteExperimentRepository(conn),
        reagent_repo=ExportSqliteReagentRepository(conn),
        equipment_repo=ExportSqliteEquipmentRepository(conn),
        project_repo=ExportSqliteProjectRepository(conn),
        protocol_repo=ExportSqliteProtocolRepository(conn),
        attachment_repo=SqliteAttachmentRepository(conn),
        user_name=config.user_name,
        user_email=config.user_email,
        report_repo=SqliteReportRepository(conn),
    )
    return {
        "experiment_service": experiment_service,
        "ai_service": AIService(OllamaClient()),
        "export_service": export_service,
    }


def build_ai_assistant_page(
    base_dir: Path | None = None,
    *,
    experiment_service: ExperimentService | None = None,
    ai_service: AIService | None = None,
    export_service: ExportService | None = None,
) -> None:
    """Build the AI Assistant page for drafting reports from experiments."""
    if experiment_service is None or ai_service is None or export_service is None:
        if base_dir is None:
            from app.bootstrap import run_bootstrap

            base_dir = run_bootstrap().base_dir
        services = _get_services(base_dir)
        experiment_service = experiment_service or services["experiment_service"]
        ai_service = ai_service or services["ai_service"]
        export_service = export_service or services["export_service"]

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("AI Assistant").classes("text-2xl font-semibold")
        ui.label(
            "Select experiments, generate a draft with Ollama, "
            "edit it and export to Markdown or PDF."
        ).classes("text-slate-600 mt-2")

        choices = get_experiment_choices(experiment_service)
        experiment_select = (
            ui.select(options=choices, multiple=True, label="Experiments")
            .props("outlined")
            .classes("w-full")
        )

        message = ui.label().classes("text-negative")

        warning_container = ui.column().classes("w-full mt-4")
        warning_container.visible = False
        with warning_container:
            ui.label(NO_AI_WARNING).classes("text-negative")
            ui.button(
                "Go to AI Reports",
                on_click=lambda: router.navigate("ai_reports"),
            ).props("outline")

        draft_area = ui.textarea("Draft").props("outlined").classes("w-full")

        def selected_ids() -> list[int]:
            return list(experiment_select.value or [])

        def on_generate() -> None:
            ids = selected_ids()
            if not ids:
                message.text = SELECTION_REQUIRED
                return
            experiments_data = collect_experiments_data(experiment_service, ids)
            if not experiments_data:
                message.text = SELECTION_REQUIRED
                return
            draft = generate_draft(ai_service, experiments_data)
            if draft is None:
                warning_container.visible = True
                ui.notify(NO_AI_WARNING, type="warning")
                return
            warning_container.visible = False
            message.text = ""
            draft_area.value = draft
            ui.notify("Draft generated", type="positive")

        def on_export(file_format: str) -> None:
            markdown = draft_area.value or ""
            if not markdown.strip():
                message.text = DRAFT_REQUIRED
                return
            ids = selected_ids()
            if not ids:
                message.text = SELECTION_REQUIRED
                return
            try:
                file_path = export_draft(export_service, markdown, ids, file_format)
            except (ValueError, RuntimeError) as error:
                message.text = str(error)
                return
            message.text = ""
            ui.notify(f"Report exported to {file_path.name}", type="positive")

        ui.button("Generate draft", on_click=on_generate).props("color=primary")

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Export Markdown", on_click=lambda: on_export("md")).props(
                "color=primary"
            )
            ui.button("Export PDF", on_click=lambda: on_export("pdf")).props(
                "color=primary"
            )
