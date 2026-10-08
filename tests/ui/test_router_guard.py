from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.ui import router


@pytest.fixture(name="router_state")
def router_state_fixture() -> None:
    saved_content = router._content
    saved_view = router._current_view
    saved_kwargs = dict(router._current_kwargs)
    saved_listeners = list(router._navigate_listeners)
    saved_guard = router._leave_guard
    router._content = MagicMock()
    router._content.clear.return_value = None
    router._content.__enter__ = MagicMock(return_value=router._content)
    router._content.__exit__ = MagicMock(return_value=False)
    router._current_view = "dashboard"
    router._current_kwargs = {}
    router._navigate_listeners = []
    router._leave_guard = None
    try:
        yield
    finally:
        router._content = saved_content
        router._current_view = saved_view
        router._current_kwargs = saved_kwargs
        router._navigate_listeners = saved_listeners
        router._leave_guard = saved_guard


def _element() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_navigates_directly_without_guard(
    router_state: None,
) -> None:
    # given — no guard registered

    # when
    with patch.object(router, "_render_current_view") as render:
        router.navigate("projects")

    # then
    assert router.get_current_view() == "projects"
    assert router._content.clear.called
    assert render.call_count == 1


def test_navigates_directly_when_guard_reports_no_work(
    router_state: None,
) -> None:
    # given
    router.set_navigation_guard(lambda: False, MagicMock())

    # when
    with (
        patch.object(router, "_render_current_view") as render,
        patch("nicegui.ui.dialog") as mock_dialog,
    ):
        router.navigate("projects")

    # then
    assert router.get_current_view() == "projects"
    assert render.call_count == 1
    assert mock_dialog.call_count == 0


def test_navigates_when_guard_check_raises(
    router_state: None,
) -> None:
    # given
    def broken() -> bool:
        raise RuntimeError("boom")

    router.set_navigation_guard(broken, MagicMock())

    # when
    with (
        patch.object(router, "_render_current_view") as render,
        patch("nicegui.ui.dialog") as mock_dialog,
    ):
        router.navigate("projects")

    # then — fail open, never trap the user
    assert router.get_current_view() == "projects"
    assert render.call_count == 1
    assert mock_dialog.call_count == 0


def test_blocks_navigation_and_asks_when_guard_reports_work(
    router_state: None,
) -> None:
    # given
    on_leave = MagicMock()
    router.set_navigation_guard(lambda: True, on_leave)

    # when
    with (
        patch.object(router, "_render_current_view") as render,
        patch("nicegui.ui.dialog", return_value=_element()),
        patch("nicegui.ui.card", return_value=_element()),
        patch("nicegui.ui.label"),
        patch("nicegui.ui.row", return_value=_element()),
        patch("nicegui.ui.button") as mock_button,
    ):
        router.navigate("projects", project_id=10)

    # then — view untouched, dialog offered instead
    assert router.get_current_view() == "dashboard"
    assert render.call_count == 0
    assert on_leave.call_count == 0
    texts = [call.args[0] for call in mock_button.call_args_list]
    assert "Stay" in texts
    assert "Leave and discard" in texts


def _dialog_handlers(mock_button: MagicMock) -> dict[str, Any]:
    return {
        call.args[0]: call.kwargs["on_click"] for call in mock_button.call_args_list
    }


def test_staying_keeps_current_view(router_state: None) -> None:
    # given
    on_leave = MagicMock()
    router.set_navigation_guard(lambda: True, on_leave)

    # when
    with (
        patch.object(router, "_render_current_view") as render,
        patch("nicegui.ui.dialog", return_value=_element()),
        patch("nicegui.ui.card", return_value=_element()),
        patch("nicegui.ui.label"),
        patch("nicegui.ui.row", return_value=_element()),
        patch("nicegui.ui.button") as mock_button,
    ):
        router.navigate("projects")
        _dialog_handlers(mock_button)["Stay"]()

    # then
    assert router.get_current_view() == "dashboard"
    assert render.call_count == 0
    assert on_leave.call_count == 0
    assert router._leave_guard is not None


def test_leaving_discards_work_and_navigates(
    router_state: None,
) -> None:
    # given
    on_leave = MagicMock()
    router.set_navigation_guard(lambda: True, on_leave)

    # when
    with (
        patch.object(router, "_render_current_view") as render,
        patch("nicegui.ui.dialog", return_value=_element()),
        patch("nicegui.ui.card", return_value=_element()),
        patch("nicegui.ui.label"),
        patch("nicegui.ui.row", return_value=_element()),
        patch("nicegui.ui.button") as mock_button,
    ):
        router.navigate("projects", project_id=10)
        _dialog_handlers(mock_button)["Leave and discard"]()

    # then — cleanup ran, guard released, requested view rendered
    assert on_leave.call_count == 1
    assert router._leave_guard is None
    assert router.get_current_view() == "projects"
    assert router._current_kwargs == {"project_id": 10}
    assert render.call_count == 1


def test_cleared_guard_allows_navigation(router_state: None) -> None:
    # given
    router.set_navigation_guard(lambda: True, MagicMock())
    router.clear_navigation_guard()

    # when
    with (
        patch.object(router, "_render_current_view") as render,
        patch("nicegui.ui.dialog") as mock_dialog,
    ):
        router.navigate("projects")

    # then
    assert router.get_current_view() == "projects"
    assert render.call_count == 1
    assert mock_dialog.call_count == 0
