import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

from app.services.ollama_client import OllamaStatus
from app.ui.pages import ai_assistant as hub
from app.ui.pages.ai_assistant import (
    COMPATIBILITY_URL,
    MODEL_DOWNLOAD_URL,
    OLLAMA_SEARCH_URL,
    START_SERVER_URL,
    build_ai_assistant_page,
)
from app.ui.pages.ai_reports import (
    OLLAMA_DOWNLOAD_URL,
    QWEN_PULL_COMMAND,
    SERVE_COMMAND,
)
from main import NAV_ITEMS


class FakeOllamaClient:
    """Test double for OllamaClient without HTTP."""

    def __init__(
        self,
        status: OllamaStatus,
        status_error: Exception | None = None,
    ) -> None:
        self._status = status
        self._status_error = status_error
        self.status_calls = 0

    def get_status(self) -> OllamaStatus:
        self.status_calls += 1
        if self._status_error is not None:
            raise self._status_error
        return self._status

    def get_installed_models(self) -> tuple[str, ...]:
        return self.get_status().installed_models


async def _inline_io_bound(function, *args):
    """Run worker calls inline so async refresh can be tested."""
    return function(*args)


def _container() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.classes.return_value = mock
    mock.is_deleted = False
    return mock


class _UIContext:
    def __init__(self) -> None:
        self.busy = MagicMock()
        self.busy.visible = False
        self.buttons: dict[str, MagicMock] = {}
        self.tabs_container = _container()

    def button_factory(self, *args: Any, **kwargs: Any) -> MagicMock:
        text = args[0] if args else kwargs.get("text", "")
        mock = MagicMock()
        self.buttons[str(text)] = mock
        on_click = kwargs.get("on_click")
        if on_click is not None:
            mock.click = on_click
        return mock


def _setup_ui(mock_ui: MagicMock, context: _UIContext) -> None:
    mock_ui.column.side_effect = lambda *a, **k: _container()
    mock_ui.row.side_effect = lambda *a, **k: _container()
    mock_ui.card.side_effect = lambda *a, **k: _container()
    mock_ui.tabs.side_effect = lambda *a, **k: context.tabs_container
    mock_ui.tab.side_effect = lambda *a, **k: _container()
    mock_ui.tab_panels.side_effect = lambda *a, **k: _container()
    mock_ui.tab_panel.side_effect = lambda *a, **k: _container()
    mock_ui.grid.side_effect = lambda *a, **k: _container()
    mock_ui.icon.return_value = MagicMock()
    mock_ui.label.return_value = MagicMock()
    mock_ui.badge.return_value = MagicMock()
    mock_ui.link.return_value = MagicMock()
    mock_ui.code.return_value = MagicMock()
    mock_ui.button.side_effect = context.button_factory
    mock_ui.spinner.return_value = context.busy
    mock_ui.timer.return_value = MagicMock()


def _build_hub(
    mock_ui: MagicMock, context: _UIContext, client: FakeOllamaClient
) -> None:
    _setup_ui(mock_ui, context)
    build_ai_assistant_page(client)  # type: ignore[arg-type]


def test_sidebar_has_single_ai_entry_with_robot_icon() -> None:
    # given
    views = [view for _, view, _ in NAV_ITEMS]
    labels = [label for label, _, _ in NAV_ITEMS]

    # when / then
    assert ("AI Assistant", "ai_assistant", "smart_toy") in NAV_ITEMS
    assert "ai_reports" not in views
    assert "AI Reports" not in labels


def test_renders_guidance_steps_and_menu_without_blocking() -> None:
    # given
    context = _UIContext()
    client = FakeOllamaClient(status=OllamaStatus(True, ("qwen3:4b",)))

    # when
    with (
        patch.object(hub, "ui") as mock_ui,
        patch.object(hub, "run"),
        patch("app.ui.pages.ai_reports.ui", mock_ui),
        patch("app.ui.pages.ai_reports.run"),
    ):
        _build_hub(mock_ui, context, client)

        # then — no network call during build, placeholder shown instead
        assert client.status_calls == 0
        labels = [call.args[0] for call in mock_ui.label.call_args_list]
        assert any("Ollama" in label for label in labels)
        assert any("never leaves this machine" in label for label in labels)
        assert any("Setup status:" in label for label in labels)
        assert any("Grid of Features" in label for label in labels)
        assert "Report generator" in labels
        mock_ui.tabs.assert_called_once()
        context.tabs_container.classes.assert_called_once_with(
            "w-full mt-2 justify-start"
        )
        context.tabs_container.props.assert_called_once_with("align=left")
        assert mock_ui.tab.call_count == 2
        tab_names = [call.args[0] for call in mock_ui.tab.call_args_list]
        assert "Assistant Features" in tab_names
        assert "Setup & Configuration" in tab_names
        mock_ui.tab_panels.assert_called_once()
        assert mock_ui.tab_panel.call_count == 2
        mock_ui.grid.assert_called_once()
        mock_ui.link.assert_any_call(
            OLLAMA_DOWNLOAD_URL, OLLAMA_DOWNLOAD_URL, new_tab=True
        )
        mock_ui.link.assert_any_call(COMPATIBILITY_URL, COMPATIBILITY_URL, new_tab=True)
        mock_ui.link.assert_any_call(OLLAMA_SEARCH_URL, OLLAMA_SEARCH_URL, new_tab=True)
        mock_ui.link.assert_any_call("see the docs", MODEL_DOWNLOAD_URL, new_tab=True)
        mock_ui.link.assert_any_call("see the docs", START_SERVER_URL, new_tab=True)
        mock_ui.code.assert_any_call(QWEN_PULL_COMMAND)
        mock_ui.code.assert_any_call(SERVE_COMMAND)
        mock_ui.code.return_value.classes.assert_called_with("w-auto")
        mock_ui.badge.assert_any_call("Not checked", color="grey")
        assert mock_ui.badge.call_count >= 2
        mock_ui.timer.assert_not_called()


def test_check_button_shows_spinner_and_refreshes_to_ready() -> None:
    # given
    context = _UIContext()
    client = FakeOllamaClient(status=OllamaStatus(True, ("qwen3:4b",)))
    seen: dict[str, Any] = {}

    async def observing(function, *args):
        seen["busy"] = context.busy.visible
        return function(*args)

    # when
    with (
        patch.object(hub, "ui") as mock_ui,
        patch.object(hub, "run") as mock_run,
        patch("app.ui.pages.ai_reports.ui", mock_ui),
        patch("app.ui.pages.ai_reports.run"),
    ):
        _build_hub(mock_ui, context, client)
        mock_ui.badge.reset_mock()
        mock_run.io_bound.side_effect = observing
        asyncio.run(context.buttons["Check requirements"].click())

        # then — feedback during work, green indicator after
        assert seen["busy"] is True
        assert context.busy.visible is False
        mock_run.io_bound.assert_called_once()
        mock_ui.badge.assert_called_with("Ready", color="green")


def test_open_report_generator_navigates_to_form() -> None:
    # given
    context = _UIContext()
    client = FakeOllamaClient(status=OllamaStatus(True, ("qwen3:4b",)))

    # when
    with (
        patch.object(hub, "ui") as mock_ui,
        patch.object(hub, "run"),
        patch("app.ui.pages.ai_reports.ui", mock_ui),
        patch("app.ui.pages.ai_reports.run"),
        patch.object(hub.router, "navigate") as mock_navigate,
    ):
        _build_hub(mock_ui, context, client)
        context.buttons["Open"].click()

        # then
        mock_navigate.assert_called_once_with("ai_report_generator")


def test_renders_single_feature_card_in_grid() -> None:
    # given
    context = _UIContext()
    client = FakeOllamaClient(status=OllamaStatus(True, ("qwen3:4b",)))

    # when
    with (
        patch.object(hub, "ui") as mock_ui,
        patch.object(hub, "run"),
        patch("app.ui.pages.ai_reports.ui", mock_ui),
        patch("app.ui.pages.ai_reports.run"),
    ):
        _build_hub(mock_ui, context, client)

        # then — grid with the only real feature
        assert len(hub.FEATURES) == 1
        assert hub.FEATURES[0]["route"] == "ai_report_generator"
        mock_ui.grid.assert_called_once()
        assert "Open" in context.buttons


def test_shows_short_status_without_repeating_resources() -> None:
    # given
    context = _UIContext()
    client = FakeOllamaClient(status=OllamaStatus(False, ()))

    # when
    with (
        patch.object(hub, "ui") as mock_ui,
        patch.object(hub, "run") as mock_run,
        patch("app.ui.pages.ai_reports.ui", mock_ui),
        patch("app.ui.pages.ai_reports.run"),
    ):
        _build_hub(mock_ui, context, client)
        links_before = mock_ui.link.call_count
        codes_before = mock_ui.code.call_count
        mock_ui.badge.reset_mock()
        mock_run.io_bound.side_effect = _inline_io_bound
        refresh = context.buttons["Check requirements"].click
        asyncio.run(refresh())

        # then — badge plus short message only, resources live in the steps
        mock_ui.badge.assert_called_with("Not ready", color="red")
        assert mock_ui.link.call_count == links_before
        assert mock_ui.code.call_count == codes_before
