from __future__ import annotations

from nicegui import ui


def _insert_text(textarea: ui.textarea | None, text: str) -> None:
    if textarea is not None:
        textarea.set_value((textarea.value or "") + text)


def markdown_editor(label: str, value: str = "") -> ui.textarea:
    """Create the standard markdown editor (toolbar + textarea + preview).

    Returns the textarea element holding the markdown content.
    """
    ui.label(label).classes("font-semibold mt-2")

    state = {"textarea": None}

    def _insert(text: str) -> None:
        _insert_text(state["textarea"], text)

    with ui.row().classes("w-full gap-1 mt-1"):
        ui.button("H1", on_click=lambda: _insert("\n# Title\n")).props("flat dense")
        ui.button("H2", on_click=lambda: _insert("\n## Subtitle\n")).props(
            "flat dense"
        )
        ui.button("H3", on_click=lambda: _insert("\n### Subsubtitle\n")).props(
            "flat dense"
        )
        ui.button("Bold", on_click=lambda: _insert(" **text** ")).props("flat dense")
        ui.button("Italic", on_click=lambda: _insert(" _text_ ")).props("flat dense")
        ui.button(
            "Table",
            on_click=lambda: _insert(
                "\n| Column 1 | Column 2 |\n| --- | --- |\n| Data | Data |\n"
            ),
        ).props("flat dense")
        ui.button("List", on_click=lambda: _insert("\n- Item 1\n- Item 2\n")).props(
            "flat dense"
        )

    with ui.row().classes("w-full gap-4 items-start no-wrap"):
        textarea = (
            ui.textarea(value=value, placeholder="Markdown content...")
            .props("outlined")
            .style("width: 50%")
        )
        state["textarea"] = textarea

        preview = (
            ui.markdown(value or "")
            .style("width: 50%")
            .classes("border rounded p-2 overflow-auto min-h-[8rem]")
        )

    def _update() -> None:
        preview.content = textarea.value or ""

    textarea.on_value_change(_update)
    return textarea
