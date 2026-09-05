"""Central navigation module for the SPA shell.

Provides ``navigate`` and ``refresh`` helpers that the page builders
call instead of ``ui.navigate.to`` / ``ui.navigate.reload``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nicegui import ui

logger = logging.getLogger(__name__)

_content: ui.column | None = None
_current_view: str = "dashboard"
_current_kwargs: dict = {}
_base_dir: Path | None = None


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
    logger.info("Navigated to view=%s kwargs=%s", view, kwargs)


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
    from app.ui.pages.dashboard import build_dashboard_page
    from app.ui.pages.experiment_detail import build_experiment_detail_page
    from app.ui.pages.inventory import build_inventory_page
    from app.ui.pages.profile import build_profile_page
    from app.ui.pages.projects import build_projects_page
    from app.ui.pages.protocols import build_protocols_page

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
    elif view == "profile":
        build_profile_page(base_dir=_base_dir)
    else:
        from nicegui import ui as _ui

        _ui.label(f"Unknown view: {view}").classes("text-negative")
