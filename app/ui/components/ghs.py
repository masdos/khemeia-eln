from __future__ import annotations

from typing import Any

from nicegui import ui


def ghs_checkboxes(
    fields: list, initial: dict[str, Any] | None = None
) -> dict[str, ui.checkbox]:
    """Create the standard GHS hazards checkbox group.

    Args:
        fields: GHS field definitions as (field, code, label) tuples.
        initial: Optional entity dict to prefill checkbox values from.

    Returns:
        Mapping of field name to checkbox element.
    """
    initial = initial or {}
    ui.label("GHS Hazards").classes("font-semibold mt-4")
    checkboxes = {}
    with ui.row().classes("flex-wrap gap-4"):
        for field, code, label in fields:
            checkboxes[field] = ui.checkbox(
                f"{code} - {label}", value=bool(initial.get(field, False))
            )
    return checkboxes
