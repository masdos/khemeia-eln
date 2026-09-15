from __future__ import annotations

import logging

from nicegui import ui

from app.services.ollama_client import OllamaClient
from app.ui import router
from app.ui.pages.ai_reports import (
    OLLAMA_DOWNLOAD_URL,
    QWEN_PULL_COMMAND,
    SERVE_COMMAND,
    refresh_status_display,
)

logger = logging.getLogger(__name__)

HUB_INTRO = (
    "AI Assistant drafts scientific reports from your experiments using "
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


def _step_header(prefix: str, link_text: str, url: str) -> None:
    """Render a step title with the docs link in parentheses before colon."""
    with ui.row().classes("items-baseline gap-1 flex-nowrap"):
        ui.label(prefix)
        ui.label("(")
        ui.link(link_text, url, new_tab=True)
        ui.label("):")


def build_ai_assistant_page(ollama_client: OllamaClient | None = None) -> None:
    """Build the AI Assistant hub with guidance, status and feature menu."""
    client = ollama_client or OllamaClient()

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        ui.label("AI Assistant").classes("text-2xl font-semibold")
        ui.label(HUB_INTRO).classes("text-slate-600 mt-2")
        ui.label(HUB_TRUST).classes("text-slate-600 mt-2")

        with ui.row().classes("w-full gap-12 mt-4 items-start"):
            with ui.column().classes("flex-1"):
                ui.label("Requirements").classes("text-xl font-semibold")
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
                        await refresh_status_display(client, status_container)
                    finally:
                        busy.visible = False
                        check_button.enable()

                with ui.row().classes("w-full items-center gap-2 mt-4"):
                    check_button = ui.button(
                        "Check requirements", on_click=refresh
                    ).props("color=primary")
                    busy = ui.spinner()
                    busy.visible = False

            with ui.column().classes("flex-1"):
                ui.label("Features").classes("text-xl font-semibold")
                with ui.card().classes("w-full mt-2"):
                    ui.label("Report generator").classes("font-semibold")
                    ui.label(REPORTS_SUMMARY).classes("text-slate-600 text-sm")
                    ui.button(
                        "Open",
                        on_click=lambda: router.navigate("ai_report_generator"),
                    ).props("color=primary")
