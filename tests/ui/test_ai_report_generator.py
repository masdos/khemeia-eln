import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from app.config import clear_current_config, load_config, write_config
from app.ui.pages import ai_report_generator
from app.ui.pages.ai_report_generator import (
    build_ai_report_generator_page,
    collect_experiments_data,
    export_draft,
    generate_draft,
    get_experiment_choices,
)


class FakeExperimentService:
    """Test double listing and returning experiments without SQLite."""

    def __init__(self, experiments: list[dict[str, Any]]) -> None:
        self._experiments = {experiment["id"]: experiment for experiment in experiments}

    def list_experiments(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        return list(self._experiments.values())

    def get_experiment(self, experiment_id: int) -> dict[str, Any] | None:
        return self._experiments.get(experiment_id)


class FakeAIService:
    """Test double generating drafts without Ollama."""

    def __init__(self, draft: str | None) -> None:
        self._draft = draft
        self.calls: list[tuple[list[Any], str]] = []

    def generate_report(self, experiments_data: Any, model: str) -> str | None:
        self.calls.append((list(experiments_data), model))
        return self._draft


class FakeExportService:
    """Test double exporting drafts without filesystem or SQLite."""

    def __init__(self, base: Path) -> None:
        self._base = base
        self.markdown_calls: list[tuple[str, list[int]]] = []
        self.pdf_calls: list[tuple[str, list[int]]] = []

    def export_ai_report_markdown(
        self, markdown_content: str, experiment_ids: list[int]
    ) -> Path:
        self.markdown_calls.append((markdown_content, list(experiment_ids)))
        return self._base / "report.md"

    def export_ai_report_pdf(
        self, markdown_content: str, experiment_ids: list[int]
    ) -> Path:
        self.pdf_calls.append((markdown_content, list(experiment_ids)))
        return self._base / "report.pdf"


class FakeOllamaClient:
    """Test double listing installed models without HTTP."""

    def __init__(self, installed: tuple[str, ...] = ("qwen3:4b", "gemma3:4b")) -> None:
        self._installed = installed

    def get_installed_models(self) -> tuple[str, ...]:
        return self._installed


def _chainable(value: Any = None) -> MagicMock:
    mock = MagicMock()
    mock.value = value
    mock.text = ""
    mock.visible = True
    mock.is_deleted = False
    mock.props.return_value = mock
    mock.classes.return_value = mock
    return mock


def _container() -> MagicMock:
    mock = _chainable()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class _UIContext:
    def __init__(self) -> None:
        self.experiment_select = _chainable([1])
        self.model_select = _chainable(None)
        self.select_handler: Any = None
        self.draft = _chainable("")
        self.draft_handler: Any = None
        self.message = _chainable()
        self.warning = _container()
        self.busy = _chainable()
        self.busy.visible = False
        self.buttons: dict[str, MagicMock] = {}

    def button_factory(self, *args: Any, **kwargs: Any) -> MagicMock:
        text = args[0] if args else kwargs.get("text", "")
        mock = _chainable()
        mock.text_value = text
        self.buttons[str(text)] = mock
        on_click = kwargs.get("on_click")
        if on_click is not None:
            mock.click = on_click
        return mock


def _setup_ui(mock_ui: MagicMock, context: _UIContext) -> None:
    page_container = _container()
    pending = [page_container, context.warning]

    def make_column(*args: Any, **kwargs: Any) -> MagicMock:
        if pending:
            return pending.pop(0)
        return _container()

    def make_row(*args: Any, **kwargs: Any) -> MagicMock:
        return _container()

    def capture_select_handler(handler: Any) -> MagicMock:
        context.select_handler = handler
        return MagicMock()

    def capture_draft_handler(handler: Any) -> MagicMock:
        context.draft_handler = handler
        return MagicMock()

    mock_ui.column.side_effect = make_column
    mock_ui.row.side_effect = make_row
    mock_ui.select.side_effect = [context.experiment_select, context.model_select]
    mock_ui.textarea.return_value = context.draft
    mock_ui.button.side_effect = context.button_factory
    mock_ui.spinner.return_value = context.busy
    mock_ui.notify.return_value = None
    context.model_select.on_value_change.side_effect = capture_select_handler
    context.draft.on_value_change.side_effect = capture_draft_handler


async def _inline_io_bound(function, *args):
    """Run worker calls inline so async generation can be tested."""
    return function(*args)


def _run_model_loader(mock_ui: MagicMock, context: _UIContext) -> None:
    """Drive the background model loader inline like the timer would."""
    timer_call = mock_ui.timer.call_args
    assert timer_call is not None
    if len(timer_call.args) > 1:
        loader = timer_call.args[1]
    else:
        loader = timer_call.kwargs["callback"]
    asyncio.run(loader())
    # Emulate set_options applying the value on the real element.
    set_call = context.model_select.set_options.call_args
    if set_call is not None:
        context.model_select.value = set_call.kwargs.get("value")


def _click_generate(mock_run: MagicMock, context: _UIContext) -> None:
    """Drive the async Generate handler with inline worker execution."""
    mock_run.io_bound.side_effect = _inline_io_bound
    asyncio.run(context.buttons["Generate draft"].click())


def _build_page(
    mock_ui: MagicMock,
    context: _UIContext,
    experiments: list[dict[str, Any]] | None = None,
    draft: str | None = "# Draft",
    installed: tuple[str, ...] = ("qwen3:4b", "gemma3:4b"),
    chosen_model: str | None = "qwen3:4b",
    base_dir: Path | None = None,
) -> tuple[FakeExperimentService, FakeAIService, FakeExportService]:
    experiments = (
        experiments
        if experiments is not None
        else [{"id": 1, "title": "Exp A"}, {"id": 2, "title": "Exp B"}]
    )
    experiment_service = FakeExperimentService(experiments)
    ai_service = FakeAIService(draft)
    export_service = FakeExportService(Path("/tmp"))
    ollama_client = FakeOllamaClient(installed)
    _setup_ui(mock_ui, context)
    # Drive the background model load inline with a local run double so
    # outer run mocks used by generation tests stay untouched.
    with patch("app.ui.pages.ai_report_generator.run") as loader_run:
        loader_run.io_bound.side_effect = _inline_io_bound
        build_ai_report_generator_page(
            base_dir,
            experiment_service=experiment_service,  # type: ignore[arg-type]
            ai_service=ai_service,  # type: ignore[arg-type]
            export_service=export_service,  # type: ignore[arg-type]
            ollama_client=ollama_client,  # type: ignore[arg-type]
        )
        _run_model_loader(mock_ui, context)
    if chosen_model is not None:
        context.model_select.value = chosen_model
    if context.select_handler is not None:
        context.select_handler()
    return experiment_service, ai_service, export_service


def test_lists_all_experiments_in_multiple_selector() -> None:
    # given
    experiment_service = FakeExperimentService(
        [{"id": 1, "title": "Exp A"}, {"id": 2, "title": "Exp B"}]
    )

    # when
    choices = get_experiment_choices(experiment_service)  # type: ignore[arg-type]

    # then
    assert set(choices) == {1, 2}
    assert "Exp A" in choices[1]


def test_builds_page_with_multiple_experiment_selector() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)

        # then
        assert mock_ui.select.call_count == 2
        experiment_call = mock_ui.select.call_args_list[0]
        assert experiment_call.kwargs["multiple"] is True
        assert set(experiment_call.kwargs["options"]) == {1, 2}


def test_populates_model_dropdown_with_installed_models() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, installed=("qwen3:4b", "gemma3:4b"))

        # then — empty at build, filled when the background load finishes
        model_call = mock_ui.select.call_args_list[1]
        assert list(model_call.kwargs["options"]) == []
        set_call = context.model_select.set_options.call_args
        assert list(set_call.args[0]) == ["qwen3:4b", "gemma3:4b"]


def test_loads_models_in_background_without_blocking_build() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)

        # then — model probe deferred to a one-shot timer, page builds first
        mock_ui.timer.assert_called_once()
        assert mock_ui.timer.call_args.kwargs.get("once") is True


def test_leaves_model_dropdown_empty_without_preselection() -> None:
    # given
    context = _UIContext()
    clear_current_config()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, chosen_model=None)

        # then
        set_call = context.model_select.set_options.call_args
        assert set_call.kwargs.get("value") is None


def test_disables_generate_button_without_model_selection() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, chosen_model=None)

        # then
        generate_button = context.buttons["Generate draft"]
        assert generate_button.disable.called


def test_enables_generate_button_once_model_is_chosen() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, chosen_model=None)
        generate_button = context.buttons["Generate draft"]
        generate_button.enable.reset_mock()
        context.model_select.value = "gemma3:4b"
        context.select_handler()

        # then
        assert generate_button.enable.called


def test_generates_draft_into_editable_textarea_with_chosen_model() -> None:
    # given
    context = _UIContext()

    # when
    with (
        patch.object(ai_report_generator, "ui") as mock_ui,
        patch("app.ui.pages.ai_report_generator.run") as mock_run,
    ):
        _, ai_service, _ = _build_page(
            mock_ui, context, draft="# Report", chosen_model="gemma3:4b"
        )
        _click_generate(mock_run, context)

        # then
        assert ai_service.calls == [([{"id": 1, "title": "Exp A"}], "gemma3:4b")]
        assert context.draft.value == "# Report"
        assert context.warning.visible is False
        assert context.buttons["Export Markdown"].enable.called
        assert context.buttons["Export PDF"].enable.called


def test_shows_warning_with_hub_access_when_ai_not_ready() -> None:
    # given
    context = _UIContext()

    # when
    with (
        patch.object(ai_report_generator, "ui") as mock_ui,
        patch("app.ui.pages.ai_report_generator.run") as mock_run,
    ):
        _build_page(mock_ui, context, draft=None)
        with patch.object(ai_report_generator.router, "navigate") as mock_navigate:
            _click_generate(mock_run, context)
            context.buttons["Go to AI Assistant"].click()

            # then
            assert context.warning.visible is True
            mock_navigate.assert_called_once_with("ai_assistant")
            assert context.draft.value == ""


def test_requires_model_before_generating() -> None:
    # given
    context = _UIContext()

    # when
    with (
        patch.object(ai_report_generator, "ui") as mock_ui,
        patch("app.ui.pages.ai_report_generator.run") as mock_run,
    ):
        _, ai_service, _ = _build_page(mock_ui, context, chosen_model=None)
        _click_generate(mock_run, context)

        # then
        assert ai_service.calls == []
        assert mock_run.io_bound.call_count == 0


def test_disables_export_buttons_until_draft_exists() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)

        # then — draft starts empty, so nothing can be exported yet
        assert context.buttons["Export Markdown"].disable.called
        assert context.buttons["Export PDF"].disable.called


def test_enables_export_buttons_once_draft_has_content() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)
        context.draft.value = "# Edited draft"
        context.draft_handler()

        # then
        assert context.buttons["Export Markdown"].enable.called
        assert context.buttons["Export PDF"].enable.called


def test_disables_export_buttons_when_draft_is_cleared() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)
        context.draft.value = "# Edited draft"
        context.draft_handler()
        context.buttons["Export Markdown"].disable.reset_mock()
        context.draft.value = "   "
        context.draft_handler()

        # then
        assert context.buttons["Export Markdown"].disable.called


def test_shows_spinner_while_generating() -> None:
    # given
    context = _UIContext()
    seen: dict[str, Any] = {}

    async def observing(function, *args):
        seen["busy"] = context.busy.visible
        return function(*args)

    # when
    with (
        patch.object(ai_report_generator, "ui") as mock_ui,
        patch("app.ui.pages.ai_report_generator.run") as mock_run,
    ):
        _build_page(mock_ui, context)
        generate_button = context.buttons["Generate draft"]
        generate_button.disable.reset_mock()
        mock_run.io_bound.side_effect = observing
        asyncio.run(generate_button.click())

        # then — feedback shown during work, restored after
        assert seen["busy"] is True
        assert context.busy.visible is False
        assert generate_button.disable.called
        assert generate_button.enable.called


def test_exports_edited_draft_to_markdown() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, _, export_service = _build_page(mock_ui, context)
        context.draft.value = "# Edited draft"
        context.buttons["Export Markdown"].click()

        # then
        assert export_service.markdown_calls == [("# Edited draft", [1])]
        assert export_service.pdf_calls == []


def test_exports_edited_draft_to_pdf() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, _, export_service = _build_page(mock_ui, context)
        context.draft.value = "# Edited draft"
        context.buttons["Export PDF"].click()

        # then
        assert export_service.pdf_calls == [("# Edited draft", [1])]
        assert export_service.markdown_calls == []


def test_shows_empty_dropdown_when_no_model_installed() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, installed=(), chosen_model=None)

        # then
        set_call = context.model_select.set_options.call_args
        assert list(set_call.args[0]) == []
        assert set_call.kwargs.get("value") is None
        assert context.buttons["Generate draft"].disable.called


def test_discards_saved_model_when_no_longer_installed(tmp_path: Path) -> None:
    # given
    context = _UIContext()
    write_config(
        {
            "user_name": "Ada",
            "user_email": "ada@example.com",
            "last_used_model": "qwen3:4b",
        },
        base_dir=tmp_path,
    )

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(
            mock_ui,
            context,
            installed=("gemma3:4b",),
            chosen_model=None,
            base_dir=tmp_path,
        )

        # then — stale preference ignored, no automatic substitution
        set_call = context.model_select.set_options.call_args
        assert set_call.kwargs.get("value") is None
    clear_current_config()


def test_persists_last_used_model_after_successful_generation(
    tmp_path: Path,
) -> None:
    # given
    context = _UIContext()
    write_config(
        {"user_name": "Ada", "user_email": "ada@example.com"}, base_dir=tmp_path
    )

    # when
    with (
        patch.object(ai_report_generator, "ui") as mock_ui,
        patch("app.ui.pages.ai_report_generator.run") as mock_run,
    ):
        _build_page(mock_ui, context, chosen_model="gemma3:4b", base_dir=tmp_path)
        _click_generate(mock_run, context)

    # then
    saved = load_config(base_dir=tmp_path, load_env_file=False)
    assert saved is not None
    assert saved.last_used_model == "gemma3:4b"
    clear_current_config()


def test_skips_missing_experiments_when_collecting_data() -> None:
    # given
    experiment_service = FakeExperimentService([{"id": 1, "title": "Exp A"}])

    # when
    collected = collect_experiments_data(experiment_service, [1, 999])  # type: ignore[arg-type]

    # then
    assert [experiment["id"] for experiment in collected] == [1]


def test_returns_none_when_ai_reports_nothing() -> None:
    # given
    ai_service = FakeAIService(None)

    # when
    draft = generate_draft(ai_service, [{"id": 1}], "qwen3:4b")  # type: ignore[arg-type]

    # then
    assert draft is None


def test_dispatches_export_by_selected_format(tmp_path: Path) -> None:
    # given
    export_service = FakeExportService(tmp_path)

    # when
    markdown_path = export_draft(export_service, "# Draft", [1], "md")  # type: ignore[arg-type]
    pdf_path = export_draft(export_service, "# Draft", [1], "pdf")  # type: ignore[arg-type]

    # then
    assert markdown_path.name == "report.md"
    assert pdf_path.name == "report.pdf"


def test_restores_saved_model_when_still_installed(tmp_path: Path) -> None:
    # given
    context = _UIContext()
    write_config(
        {
            "user_name": "Ada",
            "user_email": "ada@example.com",
            "last_used_model": "gemma3:4b",
        },
        base_dir=tmp_path,
    )

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(
            mock_ui,
            context,
            installed=("qwen3:4b", "gemma3:4b"),
            chosen_model=None,
            base_dir=tmp_path,
        )

        # then — valid preference restored, nothing else substituted
        set_call = context.model_select.set_options.call_args
        assert set_call.kwargs.get("value") == "gemma3:4b"
    clear_current_config()


def test_back_button_returns_to_hub() -> None:
    # given
    context = _UIContext()

    # when
    with (
        patch.object(ai_report_generator, "ui") as mock_ui,
        patch("app.ui.components.forms.ui") as forms_ui,
    ):
        captured: dict[str, Any] = {}

        def capture_button(*args: Any, **kwargs: Any) -> MagicMock:
            captured["on_click"] = kwargs.get("on_click")
            return _chainable()

        forms_ui.button.side_effect = capture_button
        _build_page(mock_ui, context)
        with patch.object(ai_report_generator.router, "navigate") as mock_navigate:
            captured["on_click"]()

            # then
            mock_navigate.assert_called_once_with("ai_assistant")
