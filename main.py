import logging
from pathlib import Path

from nicegui import ui

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


NAV_ITEMS = [
    ("Experiments", "dashboard", "science"),
    ("Projects", "projects", "folder"),
    ("Protocols", "protocols", "article"),
    ("Inventory", "inventory", "shelves"),
    ("AI Reports", "ai_reports", "smart_toy"),
    ("Profile", "profile", "contact_page"),
]


_sidebar_buttons: dict[str, ui.button] = {}


def _update_sidebar_active(view: str | None = None) -> None:
    current = view if view is not None else router.get_current_view()
    for item_view, btn in _sidebar_buttons.items():
        if item_view == current:
            btn.classes(add="bg-slate-100", remove="hover:bg-slate-100")
        else:
            btn.classes(add="hover:bg-slate-100", remove="bg-slate-100")


def _render_sidebar_content() -> None:
    _sidebar_buttons.clear()
    ui.image("app/ui/assets/logo.png").classes("w-36 mx-auto")
    for label, view, icon in NAV_ITEMS:
        btn = (
            ui.button(
                icon=icon,
                text=label,
                on_click=lambda v=view: router.navigate(v),
            )
            .props("flat color=black")
            .classes(
                "flex items-center gap-3 py-2 px-3 rounded-lg no-underline"
                " justify-start"
            )
        )
        _sidebar_buttons[view] = btn
    _update_sidebar_active()


def _build_sidebar() -> ui.column:
    sidebar = (
        ui.column()
        .classes("w-60 shrink-0 p-4 gap-1 sticky top-4 self-start")
        .style(
            "background-color: #FFFFFF; border-radius: 12px;"
            " box-shadow: 0 1px 3px rgba(0,0,0,0.08);"
            " border: 1px solid #E5E7EB;"
            " position: sticky; top: 1rem;"
            " max-height: calc(100vh - 2rem); overflow-y: auto"
        )
    )
    with sidebar:
        _render_sidebar_content()
    router.on_navigate(_update_sidebar_active)
    return sidebar


def _build_welcome_dialog(base_dir: Path) -> None:
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


def setup_ui(base_dir: Path) -> None:
    """Register the single page handler that routes between welcome and app.

    The handler checks config on every page load, so after the welcome form
    saves and triggers ``ui.navigate.reload()`` the main app is rendered
    immediately.
    """

    @ui.page("/")
    def main_page() -> None:
        config = load_config(base_dir, load_env_file=False)
        if config is None:
            _build_welcome_dialog(base_dir)
            return

        ui.query("body").classes("bg-slate-100")
        with ui.row().classes("w-full min-h-screen gap-4 p-4 items-start flex-nowrap"):
            _build_sidebar()
            content = (
                ui.column()
                .classes("flex-1 min-w-0 max-w-6xl p-6 rounded-xl")
                .style(
                    "background-color: #FFFFFF; border-radius: 12px;"
                    " box-shadow: 0 1px 3px rgba(0,0,0,0.08);"
                    " border: 1px solid #E5E7EB"
                )
            )
        router.setup(content, base_dir)
        router.navigate("dashboard")


def main() -> None:
    try:
        bootstrap_result = _initialize_app()
        setup_ui(bootstrap_result.base_dir)
        favicon_path = Path(__file__).parent / "app" / "ui" / "assets" / "favicon.ico"
        ui.run(
            native=True,
            title="Khemeia ELN",
            favicon=favicon_path,
            reload=False,
            fullscreen=False,
            window_size=(1600, 900),
        )
    except Exception as e:
        logger.critical("Application startup failed error=%s", str(e), exc_info=True)
        raise
    finally:
        close_connection()
        logger.info("Application shutdown complete")


if __name__ in ("__main__", "__mp_main__"):
    main()
