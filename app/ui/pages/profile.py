from pathlib import Path

from nicegui import ui

from app.config import get_current_config, write_config


def build_profile_page(base_dir: Path) -> None:
    """Build the profile settings page.

    Displays a form to edit user_name and user_email.
    AI provider selector is NOT shown in this MVP phase.
    """
    config = get_current_config()

    with ui.card().classes("w-full max-w-lg mx-auto mt-8 p-6"):
        ui.label("Profile Settings").classes("text-2xl font-semibold mb-4")
        ui.label("Edit your profile information.").classes("text-slate-600 mb-4")

        user_name = ui.input(
            "Full name",
            value=config.user_name,
        ).props("outlined").classes("w-full")

        user_email = ui.input(
            "Email",
            value=config.user_email,
        ).props("outlined").classes("w-full")

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
                message.text = ""
                ui.notify("Profile updated successfully", type="positive")
            except ValueError as error:
                message.text = str(error)

        ui.button("Save changes", on_click=save).classes("w-full mt-2")
