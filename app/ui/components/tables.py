from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

VIEW_DELETE_SLOT = """
<q-td :props="props">
    <q-btn flat dense icon="visibility"
            @click="() => $parent.$emit('view', props.row)" />
    <q-btn flat dense icon="delete" color="negative"
            @click="() => $parent.$emit('delete', props.row)" />
</q-td>
"""


def entity_table(columns: list, rows: list) -> ui.table:
    """Create the standard records table."""
    return ui.table(
        columns=columns, rows=rows, row_key="id", pagination=10
    ).classes("w-full")


VIEW_SLOT = """
<q-td :props="props">
    <q-btn flat dense icon="visibility"
            @click="() => $parent.$emit('view', props.row)" />
</q-td>
"""

VIEW_HISTORY_SLOT = """
<q-td :props="props">
    <q-btn flat dense icon="visibility"
            @click="() => $parent.$emit('view', props.row)" />
    <q-btn flat dense icon="history"
            @click="() => $parent.$emit('history', props.row)" />
</q-td>
"""

STATE_BADGE_SLOT = """
<q-td :props="props">
    <q-badge :color="props.row.state === 'Running' ? 'blue' :
                      props.row.state === 'Success' ? 'green' : 'red'"
             :label="props.row.state" />
</q-td>
"""

EXPERIMENT_ACTIONS_SLOT = """
<q-td :props="props">
    <q-btn flat dense icon="visibility"
            @click.stop="$parent.$emit('view', props.row)" />
    <q-btn flat dense icon="delete" color="negative"
            @click.stop="$parent.$emit('request-delete', props.row)" />
</q-td>
"""


def add_view_delete_actions(
    table: ui.table,
    on_view: Callable[[object], None],
    on_delete: Callable[[object], None],
) -> None:
    """Add the standard view/delete actions column handlers."""
    table.add_slot("body-cell-actions", VIEW_DELETE_SLOT)
    table.on("view", on_view)
    table.on("delete", on_delete)


def add_view_actions(
    table: ui.table,
    on_view: Callable[[object], None],
) -> None:
    """Add the view-only actions column handler."""
    table.add_slot("body-cell-actions", VIEW_SLOT)
    table.on("view", on_view)


def add_view_history_actions(
    table: ui.table,
    on_view: Callable[[object], None],
    on_history: Callable[[object], None],
) -> None:
    """Add the view/history actions column handlers."""
    table.add_slot("body-cell-actions", VIEW_HISTORY_SLOT)
    table.on("view", on_view)
    table.on("history", on_history)


def add_state_badge(table: ui.table) -> None:
    """Add the experiment state badge column rendering."""
    table.add_slot("body-cell-state", STATE_BADGE_SLOT)


def add_experiment_actions(
    table: ui.table,
    on_view: Callable[[object], None],
    on_request_delete: Callable[[object], None],
) -> None:
    """Add the experiment list actions column handlers."""
    table.add_slot("body-cell-actions", EXPERIMENT_ACTIONS_SLOT)
    table.on("view", on_view)
    table.on("request-delete", on_request_delete)
