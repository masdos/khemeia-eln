"""Central navigation module for the SPA shell.

Provides ``navigate`` and ``refresh`` helpers that the page builders
call instead of ``ui.navigate.to`` / ``ui.navigate.reload``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nicegui import ui

logger = logging.getLogger(__name__)

_content: ui.column | None = None
_current_view: str = "dashboard"
_current_kwargs: dict = {}
_base_dir: Path | None = None
_navigate_listeners: list[Callable[[str], None]] = []


def setup(content: ui.column, base_dir: Path) -> None:
    """Register the content column and base_dir used by page builders."""
    global _content, _base_dir
    _content = content
    _base_dir = base_dir
    logger.info("Router initialized view=%s", _current_view)


def navigate(view: str, **kwargs: object) -> None:
    """Clear the content column and render the requested view.

    Args:
        view: View name matching a key in ``_VIEW_MAP``.
        **kwargs: Extra arguments forwarded to the page builder
            (e.g. ``experiment_id``, ``base_dir``).
    """
    global _current_view, _current_kwargs
    _current_view = view
    _current_kwargs = kwargs
    _refresh_internal()
    for listener in _navigate_listeners:
        listener(view)
    logger.info("Navigated to view=%s kwargs=%s", view, kwargs)


def on_navigate(callback: Callable[[str], None]) -> None:
    """Register a callback invoked after each navigation.

    Used by the SPA shell to update persistent chrome (e.g. sidebar
    active state) without rebuilding it.
    """
    if callback not in _navigate_listeners:
        _navigate_listeners.append(callback)
    logger.info("Navigate listener registered listener=%s", callback)


def get_current_view() -> str:
    """Return the name of the currently active view."""
    return _current_view


def refresh() -> None:
    """Re-render the current view with the same arguments.

    Drop-in replacement for ``ui.navigate.reload()``.
    """
    _refresh_internal()
    logger.info("Refreshed view=%s", _current_view)


def _refresh_internal() -> None:
    if _content is None:
        raise RuntimeError("Router not initialised. Call setup() first.")
    _content.clear()
    with _content:
        _render_current_view()


def _render_current_view() -> None:
    from app.ui.pages.ai_reports import build_ai_reports_page
    from app.ui.pages.dashboard import build_dashboard_page
    from app.ui.pages.equipment_detail import build_equipment_detail_page
    from app.ui.pages.experiment_detail import build_experiment_detail_page
    from app.ui.pages.inventory import build_inventory_page
    from app.ui.pages.profile import build_profile_page
    from app.ui.pages.project_detail import build_project_detail_page
    from app.ui.pages.projects import build_projects_page
    from app.ui.pages.protocol_detail import build_protocol_detail_page
    from app.ui.pages.protocols import build_protocols_page
    from app.ui.pages.reagent_detail import build_reagent_detail_page

    view = _current_view
    kwargs = _current_kwargs

    if view == "dashboard":
        build_dashboard_page()
    elif view == "projects":
        build_projects_page()
    elif view == "protocols":
        build_protocols_page()
    elif view == "inventory":
        build_inventory_page()
    elif view == "experiment_detail":
        build_experiment_detail_page(
            experiment_id=kwargs["experiment_id"],
            base_dir=_base_dir,
        )
    elif view == "project_detail":
        build_project_detail_page(project_id=kwargs["project_id"])
    elif view == "protocol_detail":
        build_protocol_detail_page(protocol_id=kwargs["protocol_id"])
    elif view == "reagent_detail":
        build_reagent_detail_page(reagent_id=kwargs["reagent_id"])
    elif view == "equipment_detail":
        build_equipment_detail_page(equipment_id=kwargs["equipment_id"])
    elif view == "profile":
        build_profile_page(base_dir=_base_dir)
    elif view == "ai_reports":
        build_ai_reports_page()
    else:
        from nicegui import ui as _ui

        _ui.label(f"Unknown view: {view}").classes("text-negative")
