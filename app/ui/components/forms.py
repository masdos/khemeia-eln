from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from app.ui import router


def form_message() -> ui.label:
    """Create the standard validation message label under a form."""
    return ui.label().classes("text-negative mt-2")


def dialog_actions(
    primary_label: str,
    on_primary: Callable[[], None],
    on_close: Callable[[], None],
    *,
    secondary_label: str = "Cancel",
    primary_props: str = "color=primary",
    secondary_props: str = "outline",
) -> None:
    """Create the standard dialog button row (primary first)."""
    with ui.row().classes("w-full justify-end gap-2 mt-4"):
        ui.button(primary_label, on_click=on_primary).props(primary_props)
        ui.button(secondary_label, on_click=on_close).props(secondary_props)


def detail_save_row(on_save: Callable[[], None]) -> None:
    """Create the right-aligned Save row used by detail pages."""
    with ui.row().classes("w-full justify-end mt-4"):
        ui.button("Save", on_click=on_save).props("color=primary")


def back_button(target_view: str) -> None:
    """Create the back button returning to a parent list view."""
    ui.button(
        icon="arrow_back",
        on_click=lambda: router.navigate(target_view),
    ).props("flat round").classes("mt-4")
