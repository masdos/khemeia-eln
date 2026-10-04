import asyncio
import logging
import warnings
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import main
from main import _cleanup_native_resources, _safe_log_info, _shutdown_event_loop


@pytest.fixture(name="isolated_event_loop")
def isolated_event_loop_fixture() -> Iterator[asyncio.AbstractEventLoop]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            previous = asyncio.get_event_loop_policy().get_event_loop()
        except RuntimeError:
            previous = None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        asyncio.set_event_loop(previous)


def test_closes_event_loop_with_pending_tasks(
    isolated_event_loop: asyncio.AbstractEventLoop,
) -> None:
    # given
    async def never_ends() -> None:
        await asyncio.sleep(3600)

    isolated_event_loop.create_task(never_ends())

    # when
    _shutdown_event_loop()

    # then
    assert isolated_event_loop.is_closed()


def test_skips_shutdown_when_loop_already_closed(
    isolated_event_loop: asyncio.AbstractEventLoop,
) -> None:
    # given
    isolated_event_loop.close()

    # when
    _shutdown_event_loop()

    # then
    assert isolated_event_loop.is_closed()


def test_emits_no_warnings_without_event_loop() -> None:
    # given
    asyncio.set_event_loop(None)

    try:
        # when
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            _shutdown_event_loop()

        # then
        assert [
            warning
            for warning in records
            if issubclass(warning.category, DeprecationWarning)
        ] == []
    finally:
        asyncio.set_event_loop(None)


def test_tolerates_native_cleanup_errors(monkeypatch) -> None:
    # given
    from nicegui.native import native

    def _boom() -> None:
        raise RuntimeError("gone")

    monkeypatch.setattr(native, "remove_queues", _boom)

    # when / then
    assert _cleanup_native_resources() is None


def test_tolerates_missing_native_api(monkeypatch) -> None:
    # given
    from nicegui.native import native

    monkeypatch.delattr(native, "remove_queues", raising=False)

    # when / then
    assert _cleanup_native_resources() is None


def test_logs_shutdown_message_without_teardown_noise(monkeypatch) -> None:
    # given
    failing = MagicMock(spec=logging.Logger)
    failing.info.side_effect = RuntimeError("teardown noise")
    monkeypatch.setattr(main, "logger", failing)

    # when / then
    assert _safe_log_info("Application shutdown complete") is None


def test_logs_nothing_when_interrupted_again(monkeypatch) -> None:
    # given
    failing = MagicMock(spec=logging.Logger)
    failing.info.side_effect = KeyboardInterrupt
    monkeypatch.setattr(main, "logger", failing)

    # when / then
    assert _safe_log_info("Application shutdown complete") is None


def test_survives_interrupt_during_shutdown_cleanup(monkeypatch) -> None:
    # given — closing the native window makes NiceGUI inject
    # KeyboardInterrupt into the main thread at any point
    monkeypatch.setattr(
        main, "_initialize_app", lambda: SimpleNamespace(base_dir=Path("/tmp"))
    )
    monkeypatch.setattr(main, "setup_ui", lambda base_dir: None)
    calls: list[str] = []

    def _interrupted_close() -> None:
        calls.append("close")
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "close_connection", _interrupted_close)
    monkeypatch.setattr(main.ui, "run", lambda *args, **kwargs: calls.append("run"))

    # when
    result = main.main()

    # then
    assert result is None
    assert calls == ["run", "close"]
