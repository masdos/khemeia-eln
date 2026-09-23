from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable, Mapping, Sequence
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
from app.ui.components.markdown_editor import markdown_editor

logger = logging.getLogger(__name__)

NO_AI_WARNING = "Ollama is not ready. Check the requirements on the AI Assistant page."
SELECTION_REQUIRED = "Select at least one experiment."
MODEL_REQUIRED = "Select a model."
LANGUAGE_REQUIRED = "Select a language."
PROJECT_REQUIRED = "Select a project."
TITLE_REQUIRED = "Enter a report title."
SAVE_REQUIRED = "Generate a draft before saving."
LANGUAGE_OPTIONS = ["Spanish", "English"]

PROGRESS_POLL_SECONDS = 0.2


def get_project_choices(project_repo: Any) -> dict[int, str]:
    """Return project id to name mapping for the selector."""
    choices: dict[int, str] = {}
    for project in project_repo.get_all():
        project_id = project.get("id")
        name = project.get("name") or f"Project {project_id}"
        if project_id is not None:
            choices[project_id] = str(name)
    return choices


def get_experiment_choices(
    experiment_service: ExperimentService, project_id: int | None = None
) -> dict[int, str]:
    """Return experiment id to label mapping, filtered by project when given."""
    filters = {"project_id": project_id} if project_id is not None else {}
    choices: dict[int, str] = {}
    for experiment in experiment_service.list_experiments(filters):
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
    language: str,
    on_progress: Callable[[str], None] | None = None,
) -> str | None:
    """Generate a report draft with the chosen model, or None when not ready."""
    draft = ai_service.generate_report(
        experiments_data, model, language, on_progress=on_progress
    )
    if draft is None:
        logger.warning("AI draft generation returned no content")
        return None
    logger.info(
        "AI draft generated count=%s language=%s", len(experiments_data), language
    )
    return draft


def save_draft(
    export_service: ExportService,
    markdown_content: str,
    experiment_ids: Sequence[int],
    project_id: int,
    title: str,
) -> int:
    """Store the edited draft in the database and return its report identifier."""
    return export_service.save_report(
        markdown_content, experiment_ids, project_id, title
    )


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
        user_institution=config.institution or "",
        report_repo=SqliteReportRepository(conn),
    )
    ollama_client = OllamaClient()
    return {
        "experiment_service": experiment_service,
        "ai_service": AIService(ollama_client),
        "export_service": export_service,
        "ollama_client": ollama_client,
        "project_repo": SqliteProjectRepository(conn),
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
            "institution": current.institution or "",
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
    project_repo: Any | None = None,
) -> None:
    """Build the report generator form reached from the AI Assistant hub."""
    if base_dir is None:
        from app.bootstrap import run_bootstrap

        base_dir = run_bootstrap().base_dir
    if (
        experiment_service is None
        or ai_service is None
        or export_service is None
        or ollama_client is None
        or project_repo is None
    ):
        services = _get_services(base_dir)
        experiment_service = experiment_service or services["experiment_service"]
        ai_service = ai_service or services["ai_service"]
        export_service = export_service or services["export_service"]
        ollama_client = ollama_client or services["ollama_client"]
        project_repo = project_repo or services["project_repo"]

    saved_model = _load_saved_model()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("Report generator").classes("text-2xl font-semibold")
        ui.label(
            "Select experiments, choose a model, generate a draft with Ollama, "
            "edit it and save it as a report."
        ).classes("text-slate-600 mt-2")

        project_choices = get_project_choices(project_repo)
        project_select = (
            ui.select(options=project_choices, value=None, label="Project")
            .props("outlined")
            .classes("w-full")
        )
        experiment_select = (
            ui.select(options={}, multiple=True, label="Experiments")
            .props("outlined")
            .classes("w-full")
        )

        model_select = (
            ui.select(options=[], value=None, label="Model")
            .props("outlined")
            .classes("w-full")
        )

        language_select = (
            ui.select(options=LANGUAGE_OPTIONS, value=None, label="Language")
            .props("outlined")
            .classes("w-full")
        )

        title_input = ui.input("Title *").props("outlined").classes("w-full")

        message = ui.label().classes("text-negative")

        warning_container = ui.column().classes("w-full mt-4")
        warning_container.visible = False
        with warning_container:
            ui.label(NO_AI_WARNING).classes("text-negative")
            ui.button(
                "Go to AI Assistant",
                on_click=lambda: router.navigate("ai_assistant"),
            ).props("outline")

        draft_area = markdown_editor("Draft")

        def selected_ids() -> list[int]:
            return list(experiment_select.value or [])

        def on_generate() -> None:
            ids = selected_ids()
            if not ids:
                message.text = SELECTION_REQUIRED
                return
            model = model_select.value
            if not model:
                message.text = MODEL_REQUIRED
                return
            language = language_select.value
            if not language:
                message.text = LANGUAGE_REQUIRED
                return
            experiments_data = collect_experiments_data(experiment_service, ids)
            if not experiments_data:
                message.text = SELECTION_REQUIRED
                return
            generate_button.disable()
            progress_container.visible = True
            ui.notify(
                "Generating draft, this can take several minutes on CPU-only machines.",
                type="info",
            )
            updates: queue.Queue[tuple[str, str | None]] = queue.Queue()

            def worker() -> None:
                try:
                    draft = generate_draft(
                        ai_service,
                        experiments_data,
                        model,
                        language,
                        on_progress=lambda text: updates.put(("chunk", text)),
                    )
                except Exception as error:
                    logger.warning("Report generation failed error=%s", str(error))
                    updates.put(("error", None))
                    return
                updates.put(("done", draft))

            def finish_generation(draft: str | None) -> None:
                progress_container.visible = False
                refresh_generate_state()
                if draft is None:
                    warning_container.visible = True
                    ui.notify(NO_AI_WARNING, type="warning")
                    return
                warning_container.visible = False
                message.text = ""
                draft_area.value = draft
                refresh_save_state()
                _persist_last_used_model(base_dir, model)
                ui.notify("Draft generated", type="positive")

            def poll_updates() -> None:
                if progress_container.is_deleted:
                    poll_timer.cancel()
                    return
                while True:
                    try:
                        kind, text = updates.get_nowait()
                    except queue.Empty:
                        return
                    if kind == "chunk":
                        draft_area.value = text or ""
                    else:
                        poll_timer.cancel()
                        finish_generation(text if kind == "done" else None)

            threading.Thread(target=worker, daemon=True).start()
            poll_timer = ui.timer(PROGRESS_POLL_SECONDS, poll_updates)

        def on_save() -> None:
            def reject(reason: str) -> None:
                message.text = reason
                ui.notify(reason, type="warning")

            project_id = project_select.value
            if project_id is None:
                reject(PROJECT_REQUIRED)
                return
            title = (title_input.value or "").strip()
            if not title:
                reject(TITLE_REQUIRED)
                return
            markdown = draft_area.value or ""
            if not markdown.strip():
                reject(SAVE_REQUIRED)
                return
            ids = selected_ids()
            if not ids:
                reject(SELECTION_REQUIRED)
                return
            try:
                report_id = save_draft(export_service, markdown, ids, project_id, title)
            except (ValueError, RuntimeError) as error:
                reject(str(error))
                return
            message.text = ""
            logger.info("AI draft saved report_id=%s", report_id)
            ui.notify("Report saved", type="positive")

        with ui.row().classes("w-full items-center gap-2 mt-4"):
            generate_button = ui.button("Generate draft", on_click=on_generate).props(
                "color=primary"
            )
            save_button = ui.button("Save report", on_click=on_save).props(
                "color=primary"
            )

        progress_container = ui.column().classes("w-full mt-4")
        progress_container.visible = False
        with progress_container:
            with ui.row().classes("items-center gap-2"):
                ui.spinner().props("color=primary")
                ui.label("Generating draft…").classes("text-slate-600")

        def refresh_generate_state() -> None:
            if model_select.value:
                generate_button.enable()
            else:
                generate_button.disable()

        model_select.on_value_change(lambda: refresh_generate_state())
        refresh_generate_state()

        def refresh_experiments_for_project() -> None:
            """Populate experiments with those of the selected project."""
            project_id = project_select.value
            try:
                project_choices = get_experiment_choices(experiment_service, project_id)
            except Exception as error:
                logger.warning("Experiment choices failed error=%s", str(error))
                return
            experiment_select.set_options(project_choices, value=[])
            logger.debug("Experiment choices refreshed project_id=%s", project_id)

        project_select.on_value_change(lambda: refresh_experiments_for_project())

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

        save_button.disable()

        def refresh_save_state() -> None:
            if (draft_area.value or "").strip():
                save_button.enable()
            else:
                save_button.disable()

        draft_area.on_value_change(lambda: refresh_save_state())

        back_button("ai_assistant")
