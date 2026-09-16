from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from nicegui import run, ui

from app.config import ConfigValidationError, get_current_config, write_config
from app.database.connection import get_connection
from app.services.ai_service import AIService
from app.services.experiment_service import (
    ExperimentService,
    SqliteExperimentRepository,
)
from app.services.export_service import ExportService, SqliteReportRepository
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
from app.services.ollama_client import OllamaClient
from app.services.project_service import SqliteProjectRepository
from app.services.protocol_service import SqliteProtocolRepository
from app.ui import router
from app.ui.components.forms import back_button

logger = logging.getLogger(__name__)

NO_AI_WARNING = "Ollama is not ready. Check the requirements on the AI Assistant page."
SELECTION_REQUIRED = "Select at least one experiment."
MODEL_REQUIRED = "Select a model."
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
    model: str,
) -> str | None:
    """Generate a report draft with the chosen model, or None when not ready."""
    draft = ai_service.generate_report(experiments_data, model)
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
        attachment_repo=ExportSqliteAttachmentRepository(conn),
        user_name=config.user_name,
        user_email=config.user_email,
        report_repo=SqliteReportRepository(conn),
    )
    ollama_client = OllamaClient()
    return {
        "experiment_service": experiment_service,
        "ai_service": AIService(ollama_client),
        "export_service": export_service,
        "ollama_client": ollama_client,
    }


def _load_saved_model() -> str | None:
    """Return the remembered model, or None when there is no profile."""
    try:
        return get_current_config().last_used_model
    except ConfigValidationError:
        return None


def _persist_last_used_model(base_dir: Path | None, model: str) -> None:
    """Remember the used model in config.json for the next session."""
    if base_dir is None:
        return
    try:
        current = get_current_config()
    except ConfigValidationError as error:
        logger.warning("Last used model not saved error=%s", str(error))
        return
    write_config(
        {
            "user_name": current.user_name,
            "user_email": current.user_email,
            "last_used_model": model,
        },
        base_dir=base_dir,
    )
    logger.info("Last used model saved model=%s", model)


def build_ai_report_generator_page(
    base_dir: Path | None = None,
    *,
    experiment_service: ExperimentService | None = None,
    ai_service: AIService | None = None,
    export_service: ExportService | None = None,
    ollama_client: OllamaClient | None = None,
) -> None:
    """Build the report generator form reached from the AI Assistant hub."""
    if (
        experiment_service is None
        or ai_service is None
        or export_service is None
        or ollama_client is None
    ):
        if base_dir is None:
            from app.bootstrap import run_bootstrap

            base_dir = run_bootstrap().base_dir
        services = _get_services(base_dir)
        experiment_service = experiment_service or services["experiment_service"]
        ai_service = ai_service or services["ai_service"]
        export_service = export_service or services["export_service"]
        ollama_client = ollama_client or services["ollama_client"]

    saved_model = _load_saved_model()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("Report generator").classes("text-2xl font-semibold")
        ui.label(
            "Select experiments, choose a model, generate a draft with Ollama, "
            "edit it and export to Markdown or PDF."
        ).classes("text-slate-600 mt-2")

        choices = get_experiment_choices(experiment_service)
        experiment_select = (
            ui.select(options=choices, multiple=True, label="Experiments")
            .props("outlined")
            .classes("w-full")
        )

        model_select = (
            ui.select(options=[], value=None, label="Model")
            .props("outlined")
            .classes("w-full")
        )

        message = ui.label().classes("text-negative")

        warning_container = ui.column().classes("w-full mt-4")
        warning_container.visible = False
        with warning_container:
            ui.label(NO_AI_WARNING).classes("text-negative")
            ui.button(
                "Go to AI Assistant",
                on_click=lambda: router.navigate("ai_assistant"),
            ).props("outline")

        draft_area = ui.textarea("Draft").props("outlined").classes("w-full")

        def selected_ids() -> list[int]:
            return list(experiment_select.value or [])

        async def on_generate() -> None:
            ids = selected_ids()
            if not ids:
                message.text = SELECTION_REQUIRED
                return
            model = model_select.value
            if not model:
                message.text = MODEL_REQUIRED
                return
            experiments_data = collect_experiments_data(experiment_service, ids)
            if not experiments_data:
                message.text = SELECTION_REQUIRED
                return
            generate_button.disable()
            busy.visible = True
            ui.notify(
                "Generating draft, this can take several minutes on CPU-only machines.",
                type="info",
            )
            try:
                draft = await run.io_bound(
                    generate_draft, ai_service, experiments_data, model
                )
            finally:
                busy.visible = False
                refresh_generate_state()
            if draft is None:
                warning_container.visible = True
                ui.notify(NO_AI_WARNING, type="warning")
                return
            warning_container.visible = False
            message.text = ""
            draft_area.value = draft
            refresh_export_state()
            _persist_last_used_model(base_dir, model)
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

        with ui.row().classes("w-full items-center gap-2 mt-4"):
            generate_button = ui.button("Generate draft", on_click=on_generate).props(
                "color=primary"
            )
            busy = ui.spinner()
            busy.visible = False

        def refresh_generate_state() -> None:
            if model_select.value:
                generate_button.enable()
            else:
                generate_button.disable()

        model_select.on_value_change(lambda: refresh_generate_state())
        refresh_generate_state()

        async def load_models() -> None:
            """Fetch installed models off the event loop into the dropdown.

            The Ollama probe is a network call that takes seconds when the
            server is down, so the page renders first with an empty model
            list and the options arrive afterwards without blocking
            navigation.
            """
            try:
                installed_models = await run.io_bound(
                    lambda: list(ollama_client.get_installed_models())
                )
            except Exception as error:
                logger.warning("Installed models check failed error=%s", str(error))
                installed_models = []
            if model_select.is_deleted:
                logger.debug("Model list render skipped reason=%s", "page left")
                return
            initial_model = saved_model if saved_model in installed_models else None
            model_select.set_options(installed_models, value=initial_model)
            refresh_generate_state()
            logger.info("Installed models loaded count=%s", len(installed_models))

        ui.timer(0.5, load_models, once=True)

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            export_md_button = ui.button(
                "Export Markdown", on_click=lambda: on_export("md")
            ).props("color=primary")
            export_pdf_button = ui.button(
                "Export PDF", on_click=lambda: on_export("pdf")
            ).props("color=primary")
        export_md_button.disable()
        export_pdf_button.disable()

        def refresh_export_state() -> None:
            if (draft_area.value or "").strip():
                export_md_button.enable()
                export_pdf_button.enable()
            else:
                export_md_button.disable()
                export_pdf_button.disable()

        draft_area.on_value_change(lambda: refresh_export_state())

        back_button("ai_assistant")
