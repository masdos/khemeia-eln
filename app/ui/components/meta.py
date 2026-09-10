from __future__ import annotations

from nicegui import ui


def entity_meta(created_at: str | None, modified_at: str | None = None) -> None:
    """Create the standard Created/Modified meta line of detail pages."""
    meta = f"Created: {(created_at or '')[:10]}"
    if modified_at:
        meta += f"  ·  Modified: {modified_at[:10]}"
    ui.label(meta).classes("text-sm text-slate-500")
