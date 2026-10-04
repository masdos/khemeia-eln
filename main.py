import asyncio
import logging
import warnings
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
    ("Reports", "reports", "description"),
    ("Protocols", "protocols", "menu_book"),
    ("Inventory", "inventory", "shelves"),
    ("AI Assistant", "ai_assistant", "smart_toy"),
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
        institution = (
            ui.input("Institution (optional)").props("outlined").classes("w-full")
        )
        message = ui.label().classes("text-negative")

        def save_profile() -> None:
            try:
                write_config(
                    {
                        "user_name": user_name.value,
                        "user_email": user_email.value,
                        "institution": institution.value,
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


def _shutdown_event_loop() -> None:
    """Cancel pending tasks and close the main event loop best-effort.

    When Ctrl+C aborts the server, the Windows proactor loop can be left
    with pending overlapped operations. If they reach garbage collection
    in that state, the interpreter raises "still has pending operation at
    deallocation", so drain and close the loop explicitly here instead.
    """
    with warnings.catch_warnings():
        # Fetching the loop when none exists warns and creates an empty
        # one: silence both, there is nothing to drain in that case.
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            loop = asyncio.get_event_loop_policy().get_event_loop()
        except RuntimeError:
            return
    if loop.is_closed():
        return
    try:
        if not loop.is_running():
            for task in asyncio.all_tasks(loop):
                task.cancel()
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.run_until_complete(loop.shutdown_asyncgens())
    except (RuntimeError, KeyboardInterrupt):
        logger.debug("Event loop drain interrupted")
    finally:
        try:
            loop.close()
        except (RuntimeError, KeyboardInterrupt):
            logger.debug("Event loop close interrupted")


def _cleanup_native_resources() -> None:
    """Close NiceGUI native-mode queues and pipes best-effort.

    In native mode the UI relays calls through multiprocessing queues and
    a pipe, which hold Windows pipe handles. Closing them explicitly
    avoids noisy teardown errors when the server stops abruptly.
    """
    try:
        from nicegui.native import native
    except ImportError:
        return
    remove_queues = getattr(native, "remove_queues", None)
    if remove_queues is None:
        return
    try:
        remove_queues()
    except KeyboardInterrupt:
        logger.debug("Native cleanup interrupted")
    except Exception as error:
        logger.warning("Native cleanup skipped error=%s", str(error))


def _safe_log_info(message: str) -> None:
    """Log a shutdown message without letting teardown noise escape.

    Closing the native window makes NiceGUI inject KeyboardInterrupt into
    the main thread at any point, and abandoned Windows pipe handles can
    surface as RuntimeError during garbage collection. The process is
    exiting, so neither is actionable here.
    """
    try:
        logger.info(message)
    except (KeyboardInterrupt, RuntimeError):
        pass


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
    except KeyboardInterrupt:
        _safe_log_info("Application closed by user")
    except Exception as e:
        logger.critical("Application startup failed error=%s", str(e), exc_info=True)
        raise
    finally:
        _shutdown_event_loop()
        _cleanup_native_resources()
        try:
            close_connection()
        except (KeyboardInterrupt, RuntimeError):
            _safe_log_info("Application shutdown interrupted by user")
        _safe_log_info("Application shutdown complete")


if __name__ in ("__main__", "__mp_main__"):
    main()
