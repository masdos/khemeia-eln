from multiprocessing import freeze_support

from nicegui import ui

from database.connection import close_connection, get_connection


def build_ui() -> None:
    ui.label("Khemeia ELN")


def main() -> None:
    get_connection()
    build_ui()
    try:
        ui.run(native=True, title="Khemeia ELN")
    finally:
        close_connection()


if __name__ in ("__main__", "__mp_main__"):
    freeze_support()
    main()
