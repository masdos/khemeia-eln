from __future__ import annotations

from collections.abc import Callable

from nicegui import ui


def search_toolbar(
    *,
    placeholder: str,
    action_label: str,
    on_action: Callable[[], None],
    top_margin: bool = True,
) -> ui.input:
    """Create the standard toolbar row (search left, action right)."""
    margin = " mt-4" if top_margin else ""
    with ui.row().classes(f"w-full items-center gap-4{margin}"):
        search = (
            ui.input(placeholder=placeholder)
            .props("outlined dense")
            .classes("flex-1")
        )
        ui.button(action_label, on_click=on_action).props("color=primary")
    return search
