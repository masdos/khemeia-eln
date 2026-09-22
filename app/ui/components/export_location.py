from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from nicegui import ui

logger = logging.getLogger(__name__)


def open_folder_in_explorer(folder: Path | str) -> bool:
    """Open folder in the OS file explorer, return True on success."""
    target = Path(folder).expanduser()
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        logger.error(
            "Export folder creation failed path=%s error=%s", target, str(error)
        )
        return False
    try:
        if os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys_platform() == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except Exception as error:
        logger.error("Export folder open failed path=%s error=%s", target, str(error))
        return False
    logger.info("Export folder opened path=%s", target)
    return True


def sys_platform() -> str:
    """Return sys.platform separately for test patching."""
    import sys

    return sys.platform


def export_location_label(folder: Path | str) -> None:
    """Render the classic path hint as a clickable label opening the folder."""
    clickable_folder_label(f"Exports are stored in ({Path(folder)})", folder)


def attachment_location_label(folder: Path | str) -> None:
    """Render the attachments path hint as a clickable label."""
    clickable_folder_label(f"Files are stored in ({Path(folder)})", folder)


def clickable_folder_label(text: str, folder: Path | str) -> None:
    """Render any folder path hint as a clickable label opening the folder."""
    folder_path = Path(folder)

    label = ui.label(text).classes(
        "text-xs text-slate-400 cursor-pointer hover:underline"
    )
    label.on("click", lambda: _on_open(folder_path))


def _on_open(folder: Path) -> None:
    """Open the export folder in the file explorer."""
    if not open_folder_in_explorer(folder):
        ui.notify(f"Could not open {folder}", type="negative")
