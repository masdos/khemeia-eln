from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.ui.components.export_location import (
    attachment_location_label,
    export_location_label,
    open_folder_in_explorer,
)


def test_creates_folder_before_opening(tmp_path: Path) -> None:
    # given
    target = tmp_path / "new_exports"

    # when
    with patch("app.ui.components.export_location.subprocess.Popen") as mock_popen:
        result = open_folder_in_explorer(target)

    # then
    assert result is True
    assert target.is_dir()
    assert mock_popen.call_count == 1


def test_opens_windows_explorer_in_foreground(tmp_path: Path) -> None:
    # given
    target = tmp_path / "exports"
    target.mkdir()

    # when
    with (
        patch("app.ui.components.export_location.os.name", "nt"),
        patch("app.ui.components.export_location.subprocess.Popen") as mock_popen,
    ):
        result = open_folder_in_explorer(target)

    # then
    assert result is True
    assert mock_popen.call_args.args[0] == ["explorer", str(target)]


def test_returns_false_when_folder_creation_fails(tmp_path: Path) -> None:
    # given
    target = tmp_path / "exports"

    # when
    with patch.object(Path, "mkdir", side_effect=OSError("denied")):
        result = open_folder_in_explorer(target)

    # then
    assert result is False


def test_returns_false_when_explorer_launch_fails(tmp_path: Path) -> None:
    # given
    target = tmp_path / "exports"
    target.mkdir()

    # when
    with patch(
        "app.ui.components.export_location.subprocess.Popen",
        side_effect=OSError("no explorer"),
    ):
        result = open_folder_in_explorer(target)

    # then
    assert result is False


def test_shows_classic_path_hint_with_click_to_open(tmp_path: Path) -> None:
    # given
    folder = tmp_path / "exports"

    # when
    with patch("app.ui.components.export_location.ui") as mock_ui:
        label_mock = MagicMock()
        label_mock.classes.return_value = label_mock
        mock_ui.label.return_value = label_mock
        export_location_label(folder)

    # then
    assert mock_ui.label.call_args.args[0] == f"Exports are stored in ({folder})"
    assert label_mock.on.call_count == 1
    assert label_mock.on.call_args.args[0] == "click"


def test_shows_attachments_path_hint_with_click_to_open(tmp_path: Path) -> None:
    # given
    folder = tmp_path / "attachments" / "1"

    # when
    with patch("app.ui.components.export_location.ui") as mock_ui:
        label_mock = MagicMock()
        label_mock.classes.return_value = label_mock
        mock_ui.label.return_value = label_mock
        attachment_location_label(folder)

    # then
    assert mock_ui.label.call_args.args[0] == f"Files are stored in ({folder})"
    assert label_mock.on.call_count == 1
    assert label_mock.on.call_args.args[0] == "click"
