from pathlib import Path
from unittest.mock import MagicMock, patch

from app.config import (
    clear_current_config,
    get_current_config,
    set_current_config,
    validate_config,
)


def _setup_config() -> None:
    """Set up a valid config in memory for testing."""
    config = validate_config(
        {"user_name": "Ada Lovelace", "user_email": "ada@example.com"}
    )
    set_current_config(config)


def _make_chainable_input(label: str, value: str) -> MagicMock:
    """Create a mock input that supports .props().classes() chaining with .value."""
    mock = MagicMock()
    mock.value = value
    mock.props.return_value = mock
    mock.classes.return_value = mock
    return mock


def test_profile_page_displays_current_config_values(tmp_path: Path) -> None:
    """Profile page must show current user name and email as labels."""
    # given
    _setup_config()

    with (
        patch("app.ui.pages.profile.ui") as mock_ui,
        patch("app.ui.pages.profile.get_current_config") as mock_get,
    ):
        mock_get.return_value = get_current_config()
        mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.card.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.card.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.label.return_value = MagicMock()
        mock_ui.button.return_value = MagicMock()

        from app.ui.pages.profile import build_profile_page

        build_profile_page(base_dir=tmp_path)

        # then — label calls include the user name and email
        label_calls = [call.args[0] for call in mock_ui.label.call_args_list]
        assert "Ada Lovelace" in label_calls
        assert "ada@example.com" in label_calls

    clear_current_config()


def test_profile_edit_dialog_has_input_fields(tmp_path: Path) -> None:
    """Edit dialog inputs must be pre-filled with current config values."""
    # given
    _setup_config()

    name_mock = _make_chainable_input("Full name", "Ada Lovelace")
    email_mock = _make_chainable_input("Email", "ada@example.com")

    with (
        patch("app.ui.pages.profile.ui") as mock_ui,
        patch("app.ui.pages.profile.get_current_config") as mock_get,
    ):
        mock_get.return_value = get_current_config()
        mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.card.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.card.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.label.return_value = MagicMock()
        mock_ui.dialog.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.dialog.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.input = MagicMock(side_effect=[name_mock, email_mock])
        mock_ui.row.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.row.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.button.return_value = MagicMock()

        from app.ui.pages.profile import build_profile_page

        build_profile_page(base_dir=tmp_path)

        # Get the on_click callback from the "Edit profile" button
        edit_button_calls = [
            c for c in mock_ui.button.call_args_list if c.args[0] == "Edit profile"
        ]
        assert len(edit_button_calls) == 1
        edit_callback = edit_button_calls[0].kwargs["on_click"]

        # Simulate clicking "Edit profile" to open the dialog
        edit_callback()

        # then — dialog inputs are created with current config values
        calls = mock_ui.input.call_args_list
        assert calls[0].kwargs["value"] == "Ada Lovelace"
        assert calls[1].kwargs["value"] == "ada@example.com"

    clear_current_config()


def test_profile_save_writes_config_to_disk(tmp_path: Path) -> None:
    """Saving the profile must persist to config.json via write_config."""
    # given
    _setup_config()

    name_mock = _make_chainable_input("Full name", "Grace Hopper")
    email_mock = _make_chainable_input("Email", "grace@example.com")

    with (
        patch("app.ui.pages.profile.ui") as mock_ui,
        patch("app.ui.pages.profile.write_config") as mock_write,
    ):
        mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.card.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.card.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.label.return_value = MagicMock()
        mock_ui.dialog.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.dialog.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.input = MagicMock(side_effect=[name_mock, email_mock])
        mock_ui.row.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.row.return_value.__exit__ = MagicMock(return_value=False)

        # Capture buttons: first call is "Edit profile", then inside dialog
        button_mocks = []

        def button_side_effect(*args, **kwargs):
            m = MagicMock()
            m.props.return_value = m
            button_mocks.append((args, kwargs))
            return m

        mock_ui.button.side_effect = button_side_effect

        from app.ui.pages.profile import build_profile_page

        build_profile_page(base_dir=tmp_path)

        # Simulate opening the edit dialog
        edit_click = button_mocks[0][1]["on_click"]
        edit_click()

        # Find the Save button inside the dialog (second button created)
        save_click = button_mocks[2][1]["on_click"]
        save_click()

        # then
        mock_write.assert_called_once_with(
            {"user_name": "Grace Hopper", "user_email": "grace@example.com"},
            base_dir=tmp_path,
        )

    clear_current_config()


def test_profile_page_does_not_show_ai_provider_field(tmp_path: Path) -> None:
    """AI provider selector must NOT appear in the MVP profile page."""
    # given
    _setup_config()

    name_mock = _make_chainable_input("Full name", "Ada Lovelace")
    email_mock = _make_chainable_input("Email", "ada@example.com")

    with (
        patch("app.ui.pages.profile.ui") as mock_ui,
        patch("app.ui.pages.profile.get_current_config") as mock_get,
    ):
        mock_get.return_value = get_current_config()
        mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.card.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.card.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.label.return_value = MagicMock()
        mock_ui.dialog.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.dialog.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.input = MagicMock(side_effect=[name_mock, email_mock])
        mock_ui.row.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.row.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.button.return_value = MagicMock()

        from app.ui.pages.profile import build_profile_page

        build_profile_page(base_dir=tmp_path)

        # Simulate opening the edit dialog
        button_calls = [
            c for c in mock_ui.button.call_args_list if c.args[0] == "Edit profile"
        ]
        button_calls[0].kwargs["on_click"]()

        # then — only 2 inputs (name, email), no AI provider dropdown
        assert mock_ui.input.call_count == 2
        input_labels = [call.args[0] for call in mock_ui.input.call_args_list]
        assert "Full name" in input_labels
        assert "Email" in input_labels

    clear_current_config()
