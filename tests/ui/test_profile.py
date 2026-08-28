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


def test_profile_page_loads_current_config_values(tmp_path: Path) -> None:
    """Profile form must display values from the current config."""
    # given
    _setup_config()

    name_mock = _make_chainable_input("Full name", "Ada Lovelace")
    email_mock = _make_chainable_input("Email", "ada@example.com")

    with (
        patch("app.ui.pages.profile.ui") as mock_ui,
        patch("app.ui.pages.profile.get_current_config") as mock_get,
    ):
        mock_get.return_value = get_current_config()
        mock_ui.input = MagicMock(side_effect=[name_mock, email_mock])
        mock_ui.card.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.card.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.label.return_value = MagicMock()
        mock_ui.button.return_value = MagicMock()

        from app.ui.pages.profile import build_profile_page

        build_profile_page(base_dir=tmp_path)

        # then — form inputs are created with current config values
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
        mock_ui.input = MagicMock(side_effect=[name_mock, email_mock])
        mock_ui.card.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.card.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.label.return_value = MagicMock()
        mock_ui.button.return_value = MagicMock()

        from app.ui.pages.profile import build_profile_page

        build_profile_page(base_dir=tmp_path)

        # Simulate the save callback
        save_callback = mock_ui.button.call_args.kwargs["on_click"]
        save_callback()

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

    with (
        patch("app.ui.pages.profile.ui") as mock_ui,
        patch("app.ui.pages.profile.get_current_config") as mock_get,
    ):
        mock_get.return_value = get_current_config()
        mock_ui.input = MagicMock()
        mock_ui.card.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.card.return_value.__exit__ = MagicMock(return_value=False)
        mock_ui.label.return_value = MagicMock()
        mock_ui.button.return_value = MagicMock()

        from app.ui.pages.profile import build_profile_page

        build_profile_page(base_dir=tmp_path)

        # then — only 2 inputs (name, email), no AI provider dropdown
        assert mock_ui.input.call_count == 2
        input_labels = [call.args[0] for call in mock_ui.input.call_args_list]
        assert "Full name" in input_labels
        assert "Email" in input_labels

    clear_current_config()
