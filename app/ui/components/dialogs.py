from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from app.ui.components.forms import dialog_actions, form_message


class ConfirmBlocked(Exception):
    """Raise from a delete confirmation to show an inline error."""


def confirm_delete_dialog(
    *,
    title: str,
    question: str,
    success_message: str,
    on_confirm: Callable[[], None],
    on_success: Callable[[], None] | None = None,
    confirm_label: str = "Delete",
) -> None:
    """Open the standard delete confirmation dialog.

    ``on_confirm`` performs the deletion and raises ``ConfirmBlocked``
    with an error message when it must be shown inline instead.
    ``on_success`` runs after a successful deletion (e.g. refresh).
    """
    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[28rem] max-w-full"):
        ui.label(title).classes("text-xl font-semibold")
        ui.label(question).classes("text-slate-600 mt-2")
        message = form_message()

        def confirm() -> None:
            try:
                on_confirm()
            except ConfirmBlocked as error:
                message.text = str(error)
                return
            dialog.close()
            ui.notify(success_message, type="positive")
            if on_success is not None:
                on_success()

        dialog_actions(
            confirm_label, confirm, dialog.close, secondary_props="flat"
        )

    dialog.open()
