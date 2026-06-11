from nicegui import ui

from config import AI_PROVIDERS, load_config, write_config
from database.connection import close_connection, get_connection


def build_ui() -> None:
    if load_config() is None:
        build_welcome_form()
        return

    build_app_ui()


def build_app_ui() -> None:
    ui.query("body").classes("bg-slate-50")
    ui.label("Khemeia ELN")


def build_welcome_form() -> None:
    dialog = ui.dialog().props("persistent")

    with dialog, ui.card().classes("w-[32rem] max-w-full"):
        ui.label("Welcome to Khemeia ELN").classes("text-2xl font-semibold")
        ui.label("Create your local profile to continue.").classes("text-slate-600")

        user_name = ui.input("Name").props("outlined").classes("w-full")
        user_email = ui.input("Email").props("outlined").classes("w-full")
        base_dir = ui.input("Data folder").props("outlined").classes("w-full")
        ai_provider = (
            ui.select(
                options=list(AI_PROVIDERS),
                value="lmstudio",
                label="AI provider",
            )
            .props("outlined")
            .classes("w-full")
        )
        message = ui.label().classes("text-negative")

        def save_profile() -> None:
            try:
                write_config(
                    {
                        "user_name": user_name.value,
                        "user_email": user_email.value,
                        "base_dir": base_dir.value,
                        "ai_provider": ai_provider.value,
                    }
                )
            except ValueError as error:
                message.text = str(error)
                return

            dialog.close()
            ui.notify("Profile saved", type="positive")
            ui.navigate.reload()

        ui.button("Save profile", on_click=save_profile).classes("w-full")

    dialog.open()


def main() -> None:
    get_connection()
    build_ui()
    try:
        ui.run(native=True, title="Khemeia ELN")
    finally:
        close_connection()


if __name__ in ("__main__", "__mp_main__"):
    main()
