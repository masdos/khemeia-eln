from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.ui import router


@pytest.fixture(name="router_state")
def router_state_fixture() -> None:
    saved_content = router._content
    saved_view = router._current_view
    saved_kwargs = dict(router._current_kwargs)
    saved_history = list(router._history)
    saved_listeners = list(router._navigate_listeners)
    saved_guard = router._leave_guard
    router._content = MagicMock()
    router._content.clear.return_value = None
    router._content.__enter__ = MagicMock(return_value=router._content)
    router._content.__exit__ = MagicMock(return_value=False)
    router._current_view = "dashboard"
    router._current_kwargs = {}
    router._history = []
    router._navigate_listeners = []
    router._leave_guard = None
    try:
        yield
    finally:
        router._content = saved_content
        router._current_view = saved_view
        router._current_kwargs = saved_kwargs
        router._history = saved_history
        router._navigate_listeners = saved_listeners
        router._leave_guard = saved_guard


def _element() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def _dialog_handlers(mock_button: MagicMock) -> dict[str, Any]:
    return {
        call.args[0]: call.kwargs["on_click"] for call in mock_button.call_args_list
    }


def test_back_returns_to_previous_view(router_state: None) -> None:
    # given
    with patch.object(router, "_render_current_view"):
        router.navigate("projects")
        router.navigate("project_detail", project_id=7)

    # when
    with patch.object(router, "_render_current_view"):
        router.back("projects")

    # then
    assert router.get_current_view() == "projects"
    assert router._history == [("dashboard", {})]


def test_back_restores_origin_arguments(router_state: None) -> None:
    # given
    with patch.object(router, "_render_current_view"):
        router.navigate("projects")
        router.navigate("project_detail", project_id=7)
        router.navigate("experiment_detail", experiment_id=3)

    # when
    with patch.object(router, "_render_current_view"):
        router.back("projects")

    # then
    assert router.get_current_view() == "project_detail"
    assert router._current_kwargs == {"project_id": 7}


def test_back_walks_project_experiment_reagent_chain(router_state: None) -> None:
    # given
    with patch.object(router, "_render_current_view"):
        router.navigate("projects")
        router.navigate("project_detail", project_id=1)
        router.navigate("experiment_detail", experiment_id=2)
        router.navigate("reagent_detail", reagent_id=3)

    # when
    with patch.object(router, "_render_current_view"):
        router.back("inventory")
        after_reagent = (router.get_current_view(), dict(router._current_kwargs))
        router.back("inventory")
        after_experiment = (router.get_current_view(), dict(router._current_kwargs))
        router.back("projects")

    # then
    assert after_reagent == ("experiment_detail", {"experiment_id": 2})
    assert after_experiment == ("project_detail", {"project_id": 1})
    assert router.get_current_view() == "projects"


def test_back_uses_fallback_without_history(router_state: None) -> None:
    # given
    router._current_view = "experiment_detail"
    router._current_kwargs = {"experiment_id": 2}
    router._history = []

    # when
    with patch.object(router, "_render_current_view"):
        router.back("dashboard")

    # then
    assert router.get_current_view() == "dashboard"
    assert router._history == []


def test_refresh_does_not_record_history(router_state: None) -> None:
    # given
    router._current_view = "projects"
    router._history = []

    # when
    with patch.object(router, "_render_current_view"):
        router.refresh()

    # then
    assert router._history == []


def test_navigating_to_same_view_does_not_record_history(router_state: None) -> None:
    # given
    with patch.object(router, "_render_current_view"):
        router.navigate("experiment_detail")

    # when
    with patch.object(router, "_render_current_view"):
        router.navigate("experiment_detail", experiment_id=5)
        router.back("dashboard")

    # then
    assert router.get_current_view() == "dashboard"
    assert router._history == []


def test_back_is_blocked_while_guard_reports_work(router_state: None) -> None:
    # given
    router._current_view = "project_detail"
    router._current_kwargs = {"project_id": 7}
    router._history = [("projects", {})]
    router.set_navigation_guard(lambda: True, MagicMock())

    # when
    with (
        patch.object(router, "_render_current_view") as render,
        patch("nicegui.ui.dialog", return_value=_element()),
        patch("nicegui.ui.card", return_value=_element()),
        patch("nicegui.ui.label"),
        patch("nicegui.ui.row", return_value=_element()),
        patch("nicegui.ui.button"),
    ):
        router.back("projects")

    # then
    assert router.get_current_view() == "project_detail"
    assert router._history == [("projects", {})]
    assert render.call_count == 0


def test_back_after_confirming_leave_pops_history(router_state: None) -> None:
    # given
    router._current_view = "project_detail"
    router._current_kwargs = {"project_id": 7}
    router._history = [("projects", {})]
    router.set_navigation_guard(lambda: True, MagicMock())

    # when
    with (
        patch.object(router, "_render_current_view") as render,
        patch("nicegui.ui.dialog", return_value=_element()),
        patch("nicegui.ui.card", return_value=_element()),
        patch("nicegui.ui.label"),
        patch("nicegui.ui.row", return_value=_element()),
        patch("nicegui.ui.button") as mock_button,
    ):
        router.back("projects")
        _dialog_handlers(mock_button)["Leave and discard"]()

    # then
    assert router.get_current_view() == "projects"
    assert router._history == []
    assert render.call_count == 1
