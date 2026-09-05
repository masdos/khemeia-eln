from pathlib import Path

from nicegui import ui

from app.config import get_current_config, write_config


def build_profile_page(base_dir: Path) -> None:
    """Build the profile settings page.

    Displays user information in read-only mode with an Edit button
    that opens a dialog to modify the profile.
    """
    container = ui.column().classes("w-full max-w-6xl mt-8 px-4")

    def refresh() -> None:
        config = get_current_config()
        container.clear()
        with container:
            ui.label("Profile").classes("text-2xl font-semibold")

            ui.label("Name").classes("text-sm text-slate-500 mt-4")
            ui.label(config.user_name).classes("text-lg mb-4")

            ui.label("Email").classes("text-sm text-slate-500")
            ui.label(config.user_email).classes("text-lg mb-4")

            ui.button(
                "Edit profile",
                on_click=lambda: _open_edit_dialog(base_dir, refresh),
            ).props("color=primary")

    refresh()


def _open_edit_dialog(base_dir: Path, refresh) -> None:
    config = get_current_config()

    dialog = ui.dialog()

    with dialog, ui.card().classes("w-[32rem] max-w-full"):
        ui.label("Edit profile").classes("text-xl font-semibold")

        user_name = (
            ui.input("Full name", value=config.user_name)
            .props("outlined")
            .classes("w-full")
        )
        user_email = (
            ui.input("Email", value=config.user_email)
            .props("outlined")
            .classes("w-full")
        )

        message = ui.label().classes("text-negative mt-2")

        def save() -> None:
            try:
                write_config(
                    {
                        "user_name": user_name.value,
                        "user_email": user_email.value,
                    },
                    base_dir=base_dir,
                )
                dialog.close()
                ui.notify("Profile updated", type="positive")
                refresh()
            except ValueError as error:
                message.text = str(error)

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close)
            ui.button("Save", on_click=save).props("color=primary")

    dialog.open()
