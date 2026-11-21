from unittest.mock import MagicMock

from app.ui.components.tables import (
    add_view_actions,
    add_view_delete_actions,
    add_view_history_delete_actions,
)


def test_view_delete_actions_show_entity_tooltips() -> None:
    # given
    table = MagicMock()

    # when
    add_view_delete_actions(
        table,
        MagicMock(),
        MagicMock(),
        view_tooltip="View project",
        delete_tooltip="Delete project",
    )

    # then
    action_slot = table.add_slot.call_args.args[1]
    assert "<q-tooltip>View project</q-tooltip>" in action_slot
    assert "<q-tooltip v-else>Delete project</q-tooltip>" in action_slot
    assert "In use in experiments" in action_slot


def test_view_history_delete_actions_show_entity_tooltips() -> None:
    # given
    table = MagicMock()

    # when
    add_view_history_delete_actions(
        table,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        view_tooltip="View reagent",
        history_tooltip="View reagent history",
        delete_tooltip="Delete reagent",
    )

    # then
    action_slot = table.add_slot.call_args.args[1]
    assert "<q-tooltip>View reagent</q-tooltip>" in action_slot
    assert "<q-tooltip>View reagent history</q-tooltip>" in action_slot
    assert "<q-tooltip v-else>Delete reagent</q-tooltip>" in action_slot


def test_view_actions_show_entity_tooltip() -> None:
    # given
    table = MagicMock()

    # when
    add_view_actions(table, MagicMock(), view_tooltip="View experiment")

    # then
    action_slot = table.add_slot.call_args.args[1]
    assert "<q-tooltip>View experiment</q-tooltip>" in action_slot
