import logging
from pathlib import Path

from nicegui import app, ui

from app.bootstrap import run_bootstrap
from app.config import load_config, write_config
from app.database.connection import close_connection, get_connection
from app.ui.pages.dashboard import build_dashboard_page
from app.ui.pages.experiment_detail import build_experiment_detail_page
from app.ui.pages.inventory import build_inventory_page
from app.ui.pages.profile import build_profile_page
from app.ui.pages.projects import build_projects_page
from app.ui.pages.protocols import build_protocols_page

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
    """Build the main application UI with sidebar navigation and page routes.

    Args:
        base_dir: Application data directory (from BootstrapResult.base_dir)
    """

    NAV_ITEMS = [
        ("Experiments", "/", "science"),
        ("Projects", "/projects", "folder"),
        ("Protocols", "/protocols", "article"),
        ("Inventory", "/inventory", "shelves"),
        ("Profile", "/profile", "contact_page"),
    ]

    def _build_sidebar() -> ui.column:
        sidebar = ui.column().classes("w-60 min-h-screen border-r p-4 gap-1")
        with sidebar:
            ui.image("app/ui/assets/logo.png").classes("w-36 mb-4")
            for label, href, icon in NAV_ITEMS:
                with ui.link("", href).classes(
                    "flex items-center gap-3 py-2 px-3 rounded no-underline"
                    " hover:bg-slate-100"
                ):
                    ui.icon(icon, size="24px")
                    ui.label(label).classes("text-base")
        return sidebar

    @ui.page("/")
    def index_page() -> None:
        ui.query("body").classes("bg-slate-50")
        with ui.row().classes("w-full min-h-screen"):
            _build_sidebar()
            with ui.column().classes("flex-1 p-6"):
                build_dashboard_page()

    @ui.page("/projects")
    def projects_page() -> None:
        ui.query("body").classes("bg-slate-50")
        with ui.row().classes("w-full min-h-screen"):
            _build_sidebar()
            with ui.column().classes("flex-1 p-6"):
                build_projects_page()

    @ui.page("/inventory")
    def inventory_page() -> None:
        ui.query("body").classes("bg-slate-50")
        with ui.row().classes("w-full min-h-screen"):
            _build_sidebar()
            with ui.column().classes("flex-1 p-6"):
                build_inventory_page()

    @ui.page("/protocols")
    def protocols_page() -> None:
        ui.query("body").classes("bg-slate-50")
        with ui.row().classes("w-full min-h-screen"):
            _build_sidebar()
            with ui.column().classes("flex-1 p-6 overflow-auto"):
                build_protocols_page()

    @ui.page("/experiments/new")
    def experiment_new_page() -> None:
        ui.query("body").classes("bg-slate-50")
        with ui.row().classes("w-full min-h-screen"):
            _build_sidebar()
            with ui.column().classes("flex-1 p-6"):
                build_experiment_detail_page(experiment_id=None, base_dir=base_dir)

    @ui.page("/experiments/{experiment_id}")
    def experiment_detail_page(experiment_id: int) -> None:
        ui.query("body").classes("bg-slate-50")
        with ui.row().classes("w-full min-h-screen"):
            _build_sidebar()
            with ui.column().classes("flex-1 p-6"):
                build_experiment_detail_page(
                    experiment_id=experiment_id, base_dir=base_dir
                )

    @ui.page("/profile")
    def profile_page() -> None:
        ui.query("body").classes("bg-slate-50")
        with ui.row().classes("w-full min-h-screen"):
            _build_sidebar()
            with ui.column().classes("flex-1 p-6"):
                build_profile_page(base_dir)


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
