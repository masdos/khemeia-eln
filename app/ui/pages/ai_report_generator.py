from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from nicegui import run, ui
from nicegui.events import GenericEventArguments

from app.config import ConfigValidationError, get_current_config, write_config
from app.database.connection import get_connection
from app.repositories import attachment_repository
from app.services.ai_service import AIService
from app.services.experiment_service import (
    ExperimentNotFoundError,
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
from app.services.inventory_service import (
    InventoryService,
    SqliteEquipmentRepository,
    SqliteReagentRepository,
)
from app.services.ollama_client import RECOMMENDED_MODEL, OllamaClient
from app.services.project_service import SqliteProjectRepository
from app.services.protocol_service import SqliteProtocolRepository
from app.ui import router
from app.ui.components.forms import back_button
from app.ui.components.markdown_editor import markdown_editor

logger = logging.getLogger(__name__)

NO_AI_WARNING = "Ollama is not ready. Check the requirements on the AI Assistant page."
SELECTION_REQUIRED = "Select at least one experiment."
MODEL_REQUIRED = "Select a model."
LANGUAGE_REQUIRED = "Select or type a language."
PROJECT_REQUIRED = "Select a project."
TITLE_REQUIRED = "Enter a report title."
SAVE_REQUIRED = "Generate a draft before saving."
LANGUAGE_OPTIONS = ["Spanish", "English"]

PROGRESS_POLL_SECONDS = 0.2

_generation_active = False
_cancel_requested = False


class _GenerationCancelled(Exception):
    """Raised inside the worker when leaving the page discards the draft."""


def is_generation_in_progress() -> bool:
    """Return whether an AI draft is currently streaming."""
    return _generation_active


def request_cancel_generation() -> None:
    """Ask a running generation to stop at the next streamed chunk."""
    global _cancel_requested
    _cancel_requested = True
    logger.info("Generation cancel requested")


def _set_generation_active(active: bool) -> None:
    """Track streaming state and keep the router leave guard in sync."""
    global _generation_active, _cancel_requested
    _generation_active = active
    if active:
        _cancel_requested = False
        router.set_navigation_guard(is_generation_in_progress, _leave_and_cancel)
    else:
        router.clear_navigation_guard()


def _leave_and_cancel() -> None:
    """Cancel a running generation when the user confirms leaving."""
    request_cancel_generation()
    _set_generation_active(False)


GHS_HAZARDS = (
    ("is_explosive", "Explosive"),
    ("is_flammable", "Flammable"),
    ("is_oxidizer", "Oxidizer"),
    ("is_gas_under_pressure", "Gas under pressure"),
    ("is_corrosive", "Corrosive"),
    ("is_acute_toxic", "Acute toxicity"),
    ("is_harmful_irritant", "Harmful/Irritant"),
    ("is_health_hazard", "Health hazard"),
    ("is_environmental_hazard", "Environmental hazard"),
)


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
    *,
    protocol_repo: Any | None = None,
    inventory_service: InventoryService | None = None,
    connection: Any | None = None,
) -> list[dict[str, Any]]:
    """Return full experiment records for the selected ids, skipping missing.

    Each record is enriched with the protocol name, the linked reagents
    (with amount, lot and hazards), the linked equipment and the attachments
    (with file name, extension and description), so the AI draft is built
    from the same data shown on the experiment detail page. Sources left
    as None are skipped.
    """
    collected: list[dict[str, Any]] = []
    for experiment_id in experiment_ids:
        try:
            experiment = experiment_service.get_experiment(experiment_id)
        except ExperimentNotFoundError:
            continue
        if experiment is None:
            continue
        record = dict(experiment)
        if protocol_repo is not None:
            protocol = protocol_repo.get_by_id(record.get("protocol_id"))
            if protocol is not None:
                record["protocol_name"] = protocol.get("name")
        if inventory_service is not None:
            resources = inventory_service.get_experiment_resources(experiment_id)
            record["reagents"] = [
                {
                    "name": reagent.get("name", ""),
                    "amount_used": reagent.get("amount_used"),
                    "unit": reagent.get("unit", "") or "",
                    "lot_number": reagent.get("lot_number", "") or "",
                    "hazards": [
                        label for field, label in GHS_HAZARDS if reagent.get(field)
                    ],
                }
                for reagent in resources.get("reagents", [])
            ]
            record["equipment"] = [
                {
                    "name": item.get("name", ""),
                    "description": item.get("description", "") or "",
                }
                for item in resources.get("equipment", [])
            ]
        if connection is not None:
            record["attachments"] = [
                {
                    "file_name": attachment["file_name"],
                    "extension": attachment["extension"],
                    "description": attachment["description"] or "",
                }
                for attachment in attachment_repository.get_by_experiment(
                    connection, experiment_id
                )
            ]
        collected.append(record)
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
    protocol_repo = SqliteProtocolRepository(conn)
    inventory_service = InventoryService(
        reagent_repo=SqliteReagentRepository(conn),
        equipment_repo=SqliteEquipmentRepository(conn),
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
        "protocol_repo": protocol_repo,
        "inventory_service": inventory_service,
        "connection": conn,
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
    protocol_repo: Any | None = None,
    inventory_service: InventoryService | None = None,
    connection: Any | None = None,
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
        protocol_repo = protocol_repo or services["protocol_repo"]
        inventory_service = inventory_service or services["inventory_service"]
        connection = connection or services["connection"]
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
            ui.select(
                options=list(LANGUAGE_OPTIONS),
                value=None,
                label="Language",
                new_value_mode="add-unique",
            )
            .props('outlined placeholder="Select or type a language"')
            .classes("w-full")
        )

        typed_language = ""

        def _remember_typed_language(event: GenericEventArguments) -> None:
            nonlocal typed_language
            if isinstance(event.args, str):
                typed_language = event.args

        def _commit_typed_language(_event: GenericEventArguments) -> None:
            text = typed_language.strip()
            if language_select.value or not text:
                return
            if text not in language_select.options:
                language_select.options.append(text)
                language_select.update()
            language_select.set_value(text)
            logger.info("Custom language committed language=%s", text)

        language_select.on("input-value", _remember_typed_language)
        language_select.on("blur", _commit_typed_language)

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
            language = language_select.value or typed_language.strip() or None
            if not language or not str(language).strip():
                message.text = LANGUAGE_REQUIRED
                return
            experiments_data = collect_experiments_data(
                experiment_service,
                ids,
                protocol_repo=protocol_repo,
                inventory_service=inventory_service,
                connection=connection,
            )
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

            def report_progress(text: str) -> None:
                if _cancel_requested:
                    raise _GenerationCancelled()
                updates.put(("chunk", text))

            def worker() -> None:
                try:
                    draft = generate_draft(
                        ai_service,
                        experiments_data,
                        model,
                        language,
                        on_progress=report_progress,
                    )
                except _GenerationCancelled:
                    logger.info("Generation discarded after leaving page")
                    updates.put(("cancelled", None))
                    return
                except Exception as error:
                    logger.warning("Report generation failed error=%s", str(error))
                    updates.put(("error", None))
                    return
                updates.put(("done", draft))

            def finish_generation(draft: str | None) -> None:
                _set_generation_active(False)
                progress_container.visible = False
                refresh_generate_state()
                if draft is None:
                    if progress_container.is_deleted:
                        return
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

            _set_generation_active(True)
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
                status = await run.io_bound(ollama_client.get_status)
                installed_models = list(status.installed_models)
            except Exception as error:
                logger.warning("Installed models check failed error=%s", str(error))
                installed_models = []
                status = None
            if model_select.is_deleted:
                logger.debug("Model list render skipped reason=%s", "page left")
                return
            initial_model = saved_model if saved_model in installed_models else None
            if (
                initial_model is None
                and status is not None
                and status.is_recommended_model_ready
            ):
                initial_model = RECOMMENDED_MODEL
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
