import logging
from pathlib import Path

from nicegui import app, ui

from app.bootstrap import run_bootstrap
from app.config import load_config, write_config
from app.database.connection import close_connection, get_connection
from app.ui import router

logger = logging.getLogger(__name__)


def _initialize_app() -> object:
    """Initialize application: bootstrap directories and database.

    Returns:
        BootstrapResult with base_dir, db_path, config_path, config, and
        config_complete flag
    """
    # Step 1: Bootstrap (prepare directories)
    bootstrap_result = run_bootstrap()
    logger.info("Bootstrap completed base_dir=%s", bootstrap_result.base_dir)

    # Step 2: Connect to database (applies schema if database doesn't exist)
    get_connection(bootstrap_result.db_path)
    logger.info("Database connection established db_path=%s", bootstrap_result.db_path)

    return bootstrap_result


def build_ui(base_dir: Path) -> None:
    """Build UI: show welcome form if config incomplete, otherwise show app.

    Args:
        base_dir: Application data directory (from BootstrapResult.base_dir)
    """
    config = load_config(base_dir, load_env_file=False)
    if config is None:
        logger.info("UI building started config_complete=false (showing welcome form)")
        build_welcome_form(base_dir)
        return

    logger.info("UI building started config_complete=true (showing app)")
    build_app_ui(base_dir)


def build_app_ui(base_dir: Path) -> None:
    """Build the main application UI with sidebar navigation and SPA shell.

    A single ``@ui.page("/")`` handler renders the persistent sidebar and a
    content column.  Navigation clears only the content column and redraws
    the requested view — no full-page rebuild.

    Args:
        base_dir: Application data directory (from BootstrapResult.base_dir)
    """

    NAV_ITEMS = [
        ("Experiments", "dashboard", "science"),
        ("Projects", "projects", "folder"),
        ("Protocols", "protocols", "article"),
        ("Inventory", "inventory", "shelves"),
        ("Profile", "profile", "contact_page"),
    ]

    def _build_sidebar() -> ui.column:
        sidebar = (
            ui.column()
            .classes("w-60 h-full p-4 gap-1")
            .style(
                "background-color: #FFFFFF; border-radius: 12px;"
                " box-shadow: 0 1px 3px rgba(0,0,0,0.08);"
                " border: 1px solid #E5E7EB"
            )
        )
        with sidebar:
            ui.image("app/ui/assets/logo.png").classes("w-36 mb-4")
            for label, view, icon in NAV_ITEMS:
                ui.button(
                    icon=icon,
                    text=label,
                    on_click=lambda v=view: router.navigate(v),
                ).classes(
                    "flex items-center gap-3 py-2 px-3 rounded-lg no-underline"
                    " hover:bg-slate-100 justify-start"
                ).props("flat color=black")
        return sidebar

    @ui.page("/")
    def main_page() -> None:
        ui.query("body").classes("bg-slate-100")
        with ui.row().classes("w-full min-h-screen gap-4 p-4"):
            _build_sidebar()
            content = (
                ui.column()
                .classes("w-fit p-6 rounded-xl")
                .style(
                    "background-color: #FFFFFF; border-radius: 12px;"
                    " box-shadow: 0 1px 3px rgba(0,0,0,0.08);"
                    " border: 1px solid #E5E7EB"
                )
            )
        router.setup(content, base_dir)
        router.navigate("dashboard")


def build_welcome_form(base_dir: Path) -> None:
    """Show blocking welcome form for initial profile setup.

    Args:
        base_dir: Application data directory (from BootstrapResult.base_dir)
    """
    dialog = ui.dialog().props("persistent")

    with dialog, ui.card().classes("w-[32rem] max-w-full"):
        ui.label("Welcome to Khemeia ELN").classes("text-2xl font-semibold")
        ui.label("Create your local profile to continue.").classes("text-slate-600")

        user_name = ui.input("Full name").props("outlined").classes("w-full")
        user_email = ui.input("Email").props("outlined").classes("w-full")
        message = ui.label().classes("text-negative")

        def save_profile() -> None:
            try:
                write_config(
                    {
                        "user_name": user_name.value,
                        "user_email": user_email.value,
                    },
                    base_dir=base_dir,
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
    try:
        bootstrap_result = _initialize_app()
        build_ui(bootstrap_result.base_dir)
        app.on_connect(lambda: app.native.main_window.maximize())
        ui.run(
            title="Khemeia ELN",
            reload=False,
            native=True,
        )
    except Exception as e:
        logger.critical("Application startup failed error=%s", str(e), exc_info=True)
        raise
    finally:
        close_connection()
        logger.info("Application shutdown complete")


if __name__ in ("__main__", "__mp_main__"):
    main()
