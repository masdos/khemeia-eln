from __future__ import annotations

import logging
from dataclasses import dataclass

from nicegui import run, ui

from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

OLLAMA_DOWNLOAD_URL = "https://ollama.com/download"
MODELS_LIBRARY_URL = "https://ollama.com/library"
QWEN_MODEL_URL = "https://ollama.com/library/qwen3"
GEMMA_MODEL_URL = "https://ollama.com/library/gemma3"
QWEN_PULL_COMMAND = "ollama pull qwen3"
GEMMA_PULL_COMMAND = "ollama pull gemma3"

CHECKING_MESSAGE = "Checking Ollama status..."

READY = "ready"
MISSING_OLLAMA = "missing_ollama"
MISSING_MODEL = "missing_model"
MODEL_STOPPED = "model_stopped"


@dataclass(frozen=True)
class Readiness:
    """Ollama availability with installed and running local models."""

    is_available: bool
    installed_models: tuple[str, ...] = ()
    running_models: tuple[str, ...] = ()

    @property
    def state(self) -> str:
        """Return ready, missing_ollama, missing_model or model_stopped."""
        if not self.is_available:
            return MISSING_OLLAMA
        if not self.installed_models:
            return MISSING_MODEL
        if not self.running_models:
            return MODEL_STOPPED
        return READY


def get_readiness(client: OllamaClient | None = None) -> Readiness:
    """Return Ollama readiness without raising when the endpoint fails."""
    ollama = client or OllamaClient()
    try:
        status = ollama.get_status()
    except Exception as error:
        logger.warning("AI readiness check failed error=%s", str(error))
        return Readiness(is_available=False)
    if not status.is_available:
        return Readiness(is_available=False)
    try:
        running = ollama.get_running_models()
    except Exception as error:
        logger.warning("Running models check failed error=%s", str(error))
        running = ()
    return Readiness(
        is_available=True,
        installed_models=status.installed_models,
        running_models=running,
    )


def describe_status(readiness: Readiness) -> tuple[str, str]:
    """Return state and user-facing message for a readiness."""
    if readiness.state == MISSING_OLLAMA:
        return MISSING_OLLAMA, (
            "Ollama is not responding. Download it from the official page "
            "and install it outside the application."
        )
    if readiness.state == MISSING_MODEL:
        return MISSING_MODEL, (
            "Ollama is responding but no local model was detected. "
            "Download one from the model library "
            "(qwen or gemma are recommended) "
            "by running one of these commands in a terminal:"
        )
    if readiness.state == MODEL_STOPPED:
        count = len(readiness.installed_models)
        return MODEL_STOPPED, (
            f"{count} local model(s) detected but none is running. "
            "Start the one you want in a terminal, for example:"
        )
    return READY, (
        f"Ollama is responding and {readiness.running_models[0]} is running. Ready."
    )


async def refresh_status_display(
    client: OllamaClient, status_container: ui.column
) -> None:
    """Check Ollama off the event loop and render the result.

    The network probe can take seconds when Ollama is not running, so it
    runs in a worker thread to keep the UI responsive. When the user leaves
    the page mid-check, the worker result is discarded silently.
    """
    readiness = await run.io_bound(get_readiness, client)
    if readiness is None:
        logger.debug("AI readiness check cancelled")
        return
    if status_container.is_deleted:
        logger.debug("AI readiness render skipped reason=%s", "page left")
        return
    state, message = describe_status(readiness)
    try:
        _render_status(status_container, readiness, state, message)
    except RuntimeError as error:
        logger.debug("AI readiness render skipped error=%s", str(error))
        return
    logger.info("AI readiness refreshed state=%s", state)


def _render_status(
    status_container: ui.column,
    readiness: Readiness,
    state: str,
    message: str,
) -> None:
    """Render the readiness state into the status container."""
    status_container.clear()
    with status_container:
        if state == READY:
            ui.badge("Ready", color="green")
            ui.label(message)
        elif state == MISSING_OLLAMA:
            ui.badge("Not ready", color="red")
            ui.label(message)
            ui.link("Download Ollama", OLLAMA_DOWNLOAD_URL, new_tab=True)
        elif state == MISSING_MODEL:
            ui.badge("Not ready", color="red")
            ui.label(message)
            ui.link("Ollama model library", MODELS_LIBRARY_URL, new_tab=True)
            ui.link("qwen (recommended)", QWEN_MODEL_URL, new_tab=True)
            ui.code(QWEN_PULL_COMMAND)
            ui.link("gemma (recommended)", GEMMA_MODEL_URL, new_tab=True)
            ui.code(GEMMA_PULL_COMMAND)
        else:
            ui.badge("Idle", color="orange")
            ui.label(message)
            for name in readiness.installed_models:
                ui.label(f"- {name}")
            ui.label("Example with the first model; use any from the list:")
            ui.code(f"ollama run {readiness.installed_models[0]}")


def build_ai_reports_page(ollama_client: OllamaClient | None = None) -> None:
    """Build the AI Reports readiness page without blocking the UI."""
    client = ollama_client or OllamaClient()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("AI Reports").classes("text-2xl font-semibold")
        ui.label(
            "Install Ollama and download any local model "
            "to generate scientific report drafts."
        ).classes("text-slate-600 mt-2")

        ui.label(
            "Setup happens outside the application. Links open in your default browser."
        ).classes("text-slate-500")

        status_container = ui.column().classes("w-full mt-4")
        with status_container:
            ui.badge("Checking...", color="grey")
            ui.label(CHECKING_MESSAGE)

        async def refresh() -> None:
            await refresh_status_display(client, status_container)

        ui.button("Refresh status", on_click=refresh).props("color=primary")
        ui.timer(0.1, refresh, once=True)
