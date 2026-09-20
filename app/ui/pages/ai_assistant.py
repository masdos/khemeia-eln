from __future__ import annotations

import logging

from nicegui import run, ui

from app.services.ollama_client import OllamaClient
from app.ui import router
from app.ui.pages.ai_reports import (
    OLLAMA_DOWNLOAD_URL,
    QWEN_PULL_COMMAND,
    SERVE_COMMAND,
    describe_status,
    get_readiness,
)

logger = logging.getLogger(__name__)

HUB_INTRO = (
    "AI Assistant helps with your experiments using "
    "Ollama, a free program that runs AI models directly on your lab computer."
)
HUB_TRUST = (
    "Because everything runs locally, your unpublished research data never "
    "leaves this machine: no accounts, no fees, no data sent to third-party "
    "APIs, and it works offline."
)
MODEL_DOWNLOAD_URL = "https://docs.ollama.com/cli#download-a-model"
START_SERVER_URL = "https://docs.ollama.com/cli#start-ollama"
COMPATIBILITY_URL = "https://www.canirun.ai/tier"
OLLAMA_SEARCH_URL = "https://ollama.com/search"
NOT_CHECKED_HINT = "Press Check requirements to verify the setup."
REPORTS_SUMMARY = (
    "Generate editable scientific report drafts from one or several "
    "experiments and export them to Markdown or PDF."
)

FEATURES = [
    {
        "title": "Report generator",
        "icon": "description",
        "summary": REPORTS_SUMMARY,
        "route": "ai_report_generator",
    },
]


def _step_header(prefix: str, link_text: str, url: str) -> None:
    """Render a step title with the docs link in parentheses before colon."""
    with ui.row().classes("items-baseline gap-1 flex-nowrap"):
        ui.label(prefix)
        ui.label("(")
        ui.link(link_text, url, new_tab=True)
        ui.label("):")


def _render_badge(container: ui.column, state: str) -> None:
    """Render the header badge for a readiness state."""
    container.clear()
    with container:
        if state == "ready":
            ui.badge("Ready", color="green")
        elif state == "not_checked":
            ui.badge("Not checked", color="grey")
        else:
            ui.badge("Not ready", color="red")


def _render_status_detail(container: ui.column, state: str, message: str) -> None:
    """Render the detailed status badge and message in the setup tab."""
    container.clear()
    with container:
        if state == "ready":
            ui.badge("Ready", color="green")
        else:
            ui.badge("Not ready", color="red")
        ui.label(message)


def _feature_card(feature: dict[str, str]) -> None:
    """Render a single feature card inside the features grid."""
    with ui.card().classes("w-full"):
        with ui.row().classes("items-center gap-2"):
            ui.icon(feature["icon"]).classes("text-2xl text-slate-600")
            ui.label(feature["title"]).classes("font-semibold")
        ui.label(feature["summary"]).classes("text-slate-600 text-sm")
        ui.button(
            "Open",
            on_click=lambda route=feature["route"]: router.navigate(route),
        ).props("color=primary")


def build_ai_assistant_page(ollama_client: OllamaClient | None = None) -> None:
    """Build the AI Assistant hub with tabs, grid and status indicator."""
    client = ollama_client or OllamaClient()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("AI Assistant").classes("text-2xl font-semibold")
            with ui.row().classes("items-center gap-2"):
                ui.label("Setup status:").classes("text-slate-600 text-sm")
                header_status = ui.column().classes("gap-0")
                with header_status:
                    ui.badge("Not checked", color="grey")

        with ui.tabs().classes("w-full mt-2 justify-start").props("align=left") as tabs:
            features_tab = ui.tab("Assistant Features")
            setup_tab = ui.tab("Setup & Configuration")

        with ui.tab_panels(tabs, value=features_tab).classes("w-full"):
            with ui.tab_panel(features_tab):
                ui.label(HUB_INTRO).classes("text-slate-600 mt-2")
                ui.label(HUB_TRUST).classes("text-slate-600 mt-2")
                ui.label("Features").classes("text-xl font-semibold mt-4")
                with ui.grid(columns=3).classes("w-full gap-4 mt-2"):
                    for feature in FEATURES:
                        _feature_card(feature)

            with ui.tab_panel(setup_tab):
                ui.label("Setup & Configuration").classes("text-xl font-semibold mt-2")
                with ui.column().classes("w-full gap-5 mt-2"):
                    with ui.column().classes("w-full gap-1"):
                        ui.label("1. Install Ollama from the official page:")
                        ui.link(
                            OLLAMA_DOWNLOAD_URL,
                            OLLAMA_DOWNLOAD_URL,
                            new_tab=True,
                        )
                    with ui.column().classes("w-full gap-1"):
                        ui.label(
                            "2. Check which local model is compatible with "
                            "your machine (a light one like Qwen or Gemma "
                            "is recommended):"
                        )
                        ui.link(
                            COMPATIBILITY_URL,
                            COMPATIBILITY_URL,
                            new_tab=True,
                        )
                    with ui.column().classes("w-full gap-1"):
                        ui.label("3. Find the model on Ollama:")
                        ui.link(
                            OLLAMA_SEARCH_URL,
                            OLLAMA_SEARCH_URL,
                            new_tab=True,
                        )
                    with ui.column().classes("w-full gap-1"):
                        _step_header(
                            "4. Download the chosen model",
                            "see the docs",
                            MODEL_DOWNLOAD_URL,
                        )
                        ui.code(QWEN_PULL_COMMAND).classes("w-auto").style(
                            "min-width: 260px; padding-right: 2.5rem;"
                        )
                    with ui.column().classes("w-full gap-1"):
                        _step_header(
                            "5. Start the local Ollama server",
                            "see the docs",
                            START_SERVER_URL,
                        )
                        ui.code(SERVE_COMMAND).classes("w-auto").style(
                            "min-width: 260px; padding-right: 2.5rem;"
                        )

                status_container = ui.column().classes("w-full mt-4")
                with status_container:
                    ui.badge("Not checked", color="grey")
                    ui.label(NOT_CHECKED_HINT)

                async def refresh() -> None:
                    check_button.disable()
                    busy.visible = True
                    try:
                        readiness = await run.io_bound(get_readiness, client)
                        if readiness is None:
                            logger.debug("AI readiness check cancelled")
                            return
                        if status_container.is_deleted:
                            logger.debug(
                                "AI readiness render skipped reason=%s", "page left"
                            )
                            return
                        state, message = describe_status(readiness)
                        try:
                            _render_status_detail(status_container, state, message)
                            _render_badge(header_status, state)
                        except RuntimeError as error:
                            logger.debug(
                                "AI readiness render skipped error=%s", str(error)
                            )
                            return
                        logger.info("AI readiness refreshed state=%s", state)
                    finally:
                        busy.visible = False
                        check_button.enable()

                with ui.row().classes("w-full items-center gap-2 mt-4"):
                    check_button = ui.button(
                        "Check requirements", on_click=refresh
                    ).props("color=primary")
                    busy = ui.spinner()
                    busy.visible = False
