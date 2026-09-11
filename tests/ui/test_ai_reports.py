import asyncio
from unittest.mock import MagicMock, patch

from app.services.ollama_client import OllamaStatus
from app.ui.pages.ai_reports import (
    CHECKING_MESSAGE,
    GEMMA_MODEL_URL,
    GEMMA_PULL_COMMAND,
    MODELS_LIBRARY_URL,
    OLLAMA_DOWNLOAD_URL,
    QWEN_MODEL_URL,
    QWEN_PULL_COMMAND,
    build_ai_reports_page,
    describe_status,
    get_readiness,
)


class FakeOllamaClient:
    """Test double for OllamaClient without HTTP."""

    def __init__(
        self,
        status: OllamaStatus,
        running: tuple[str, ...] = (),
        status_error: Exception | None = None,
        running_error: Exception | None = None,
    ) -> None:
        self._status = status
        self._running = running
        self._status_error = status_error
        self._running_error = running_error
        self.status_calls = 0
        self.running_calls = 0

    def get_status(self) -> OllamaStatus:
        self.status_calls += 1
        if self._status_error is not None:
            raise self._status_error
        return self._status

    def get_running_models(self) -> tuple[str, ...]:
        self.running_calls += 1
        if self._running_error is not None:
            raise self._running_error
        return self._running


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


def _setup_ui_mock(mock_ui: MagicMock) -> tuple[MagicMock, MagicMock]:
    """Configure ui mocks and return (page_container, status_container)."""
    page_container = _container()
    status_container = _container()
    mock_ui.column.side_effect = [page_container, status_container]
    mock_ui.label.return_value = MagicMock()
    mock_ui.link.return_value = MagicMock()
    mock_ui.code.return_value = MagicMock()
    mock_ui.badge.return_value = MagicMock()
    mock_ui.button.return_value = MagicMock()
    mock_ui.timer.return_value = MagicMock()
    return page_container, status_container


def _run_refresh(mock_ui: MagicMock, mock_run: MagicMock) -> None:
    """Drive the scheduled refresh callback with inline worker execution."""
    mock_run.io_bound.side_effect = _inline_io_bound
    refresh = mock_ui.timer.call_args.args[1]
    asyncio.run(refresh())


def test_accepts_any_running_model_as_ready() -> None:
    # given
    readiness = get_readiness(
        FakeOllamaClient(
            status=OllamaStatus(True, ("qwen2.5:7b",)), running=("qwen2.5:7b",)
        )  # type: ignore[arg-type]
    )

    # when
    state, message = describe_status(readiness)

    # then
    assert state == "ready"
    assert "qwen2.5:7b" in message
    assert "is running" in message


def test_describes_missing_ollama_with_download_guidance() -> None:
    # given
    readiness = get_readiness(
        FakeOllamaClient(status=OllamaStatus(False, ()))  # type: ignore[arg-type]
    )

    # when
    state, message = describe_status(readiness)

    # then
    assert state == "missing_ollama"
    assert "not responding" in message
    assert "outside the application" in message


def test_describes_missing_model_with_library_guidance() -> None:
    # given
    readiness = get_readiness(
        FakeOllamaClient(status=OllamaStatus(True, ()))  # type: ignore[arg-type]
    )

    # when
    state, message = describe_status(readiness)

    # then
    assert state == "missing_model"
    assert "model library" in message
    assert "qwen" in message
    assert "gemma" in message


def test_describes_stopped_model_with_run_guidance() -> None:
    # given
    readiness = get_readiness(
        FakeOllamaClient(
            status=OllamaStatus(True, ("gemma3:4b", "qwen2.5:7b")), running=()
        )  # type: ignore[arg-type]
    )

    # when
    state, message = describe_status(readiness)

    # then
    assert state == "model_stopped"
    assert "none is running" in message
    assert "for example" in message


def test_returns_unavailable_when_status_check_raises() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(False, ()),
        status_error=ConnectionError("refused"),
    )

    # when
    readiness = get_readiness(client)  # type: ignore[arg-type]

    # then
    assert readiness.is_available is False
    assert readiness.state == "missing_ollama"


def test_keeps_available_when_running_check_raises() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(True, ("gemma3:4b",)),
        running_error=ConnectionError("refused"),
    )

    # when
    readiness = get_readiness(client)  # type: ignore[arg-type]

    # then
    assert readiness.is_available is True
    assert readiness.state == "model_stopped"


def test_renders_instantly_without_blocking_on_network() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(True, ("gemma3:4b",)), running=("gemma3:4b",)
    )

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run"),
    ):
        _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]

        # then — no network call during build, placeholder shown instead
        assert client.status_calls == 0
        assert client.running_calls == 0
        mock_ui.badge.assert_called_with("Checking...", color="grey")
        labels = [call.args[0] for call in mock_ui.label.call_args_list]
        assert CHECKING_MESSAGE in labels
        mock_ui.timer.assert_called_once()
        assert mock_ui.timer.call_args.kwargs["once"] is True


def test_hides_setup_links_until_status_is_known() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(True, ("gemma3:4b",)), running=("gemma3:4b",)
    )

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run"),
    ):
        _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]

        # then — download guidance only appears with its own state
        assert mock_ui.link.call_count == 0
        assert mock_ui.code.call_count == 0
        labels = [call.args[0] for call in mock_ui.label.call_args_list]
        assert any("outside the application" in label for label in labels)
        assert any("default browser" in label for label in labels)


def test_shows_green_indicator_for_running_model() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(True, ("gemma3:4b",)), running=("gemma3:4b",)
    )

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run") as mock_run,
    ):
        _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]
        mock_ui.badge.reset_mock()
        _run_refresh(mock_ui, mock_run)

        # then
        mock_ui.badge.assert_called_with("Ready", color="green")


def test_shows_download_link_only_when_ollama_missing() -> None:
    # given
    client = FakeOllamaClient(status=OllamaStatus(False, ()))

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run") as mock_run,
    ):
        _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]
        mock_ui.badge.reset_mock()
        mock_ui.link.reset_mock()
        _run_refresh(mock_ui, mock_run)

        # then
        mock_ui.badge.assert_called_with("Not ready", color="red")
        mock_ui.link.assert_called_once_with(
            "Download Ollama", OLLAMA_DOWNLOAD_URL, new_tab=True
        )


def test_shows_model_recommendations_only_when_no_model_detected() -> None:
    # given
    client = FakeOllamaClient(status=OllamaStatus(True, ()))

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run") as mock_run,
    ):
        _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]
        mock_ui.badge.reset_mock()
        mock_ui.link.reset_mock()
        mock_ui.code.reset_mock()
        _run_refresh(mock_ui, mock_run)

        # then
        mock_ui.badge.assert_called_with("Not ready", color="red")
        mock_ui.link.assert_any_call(
            "Ollama model library", MODELS_LIBRARY_URL, new_tab=True
        )
        mock_ui.link.assert_any_call("qwen (recommended)", QWEN_MODEL_URL, new_tab=True)
        mock_ui.link.assert_any_call(
            "gemma (recommended)", GEMMA_MODEL_URL, new_tab=True
        )
        mock_ui.code.assert_any_call(QWEN_PULL_COMMAND)
        mock_ui.code.assert_any_call(GEMMA_PULL_COMMAND)


def test_shows_run_command_only_when_model_is_stopped() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(True, ("qwen2.5:7b", "gemma3:4b")), running=()
    )

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run") as mock_run,
    ):
        _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]
        mock_ui.badge.reset_mock()
        mock_ui.link.reset_mock()
        mock_ui.code.reset_mock()
        mock_ui.label.reset_mock()
        _run_refresh(mock_ui, mock_run)

        # then
        mock_ui.badge.assert_called_with("Idle", color="orange")
        assert mock_ui.link.call_count == 0
        labels = [call.args[0] for call in mock_ui.label.call_args_list]
        assert "- qwen2.5:7b" in labels
        assert "- gemma3:4b" in labels
        assert any("Example" in label for label in labels)
        mock_ui.code.assert_called_once_with("ollama run qwen2.5:7b")


def test_refreshes_status_manually_without_restart() -> None:
    # given
    client = FakeOllamaClient(status=OllamaStatus(False, ()))

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run") as mock_run,
    ):
        _, status_container = _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]
        _run_refresh(mock_ui, mock_run)

        client._status = OllamaStatus(True, ("gemma3:4b",))
        client._running = ("gemma3:4b",)
        refresh_button = mock_ui.button.call_args.kwargs["on_click"]
        mock_run.io_bound.side_effect = _inline_io_bound
        status_container.clear.reset_mock()
        mock_ui.badge.reset_mock()
        asyncio.run(refresh_button())

        # then
        assert status_container.clear.called
        mock_ui.badge.assert_called_with("Ready", color="green")


async def _none_io_bound(function, *args):
    """Simulate a cancelled worker, which NiceGUI reports as None."""
    return None


def test_discards_cancelled_check_silently() -> None:
    # given
    client = FakeOllamaClient(status=OllamaStatus(False, ()))

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run") as mock_run,
    ):
        _, status_container = _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]
        mock_run.io_bound.side_effect = _none_io_bound
        refresh = mock_ui.timer.call_args.args[1]
        asyncio.run(refresh())

        # then — no crash, container untouched
        assert status_container.clear.call_count == 0


def test_skips_render_when_page_was_left() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(True, ("gemma3:4b",)), running=("gemma3:4b",)
    )

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run") as mock_run,
    ):
        _, status_container = _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]
        status_container.is_deleted = True
        mock_ui.badge.reset_mock()
        _run_refresh(mock_ui, mock_run)

        # then — no render into the deleted container
        assert status_container.clear.call_count == 0
        assert mock_ui.badge.call_count == 0


def test_skips_render_when_container_is_gone_mid_check() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(True, ("gemma3:4b",)), running=("gemma3:4b",)
    )

    # when
    with (
        patch("app.ui.pages.ai_reports.ui") as mock_ui,
        patch("app.ui.pages.ai_reports.run") as mock_run,
    ):
        _, status_container = _setup_ui_mock(mock_ui)
        build_ai_reports_page(client)  # type: ignore[arg-type]
        status_container.clear.side_effect = RuntimeError("deleted")
        _run_refresh(mock_ui, mock_run)

        # then — deleted slot never crashes the timer
        assert status_container.clear.call_count == 1
