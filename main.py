from nicegui import ui


def build_ui() -> None:
    ui.label("Khemeia ELN")


def main() -> None:
    build_ui()
    ui.run(native=True, title="Khemeia ELN")


if __name__ in ("__main__", "__mp_main__"):
    main()
