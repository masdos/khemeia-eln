import asyncio
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from app.config import clear_current_config, load_config, write_config
from app.ui.pages import ai_report_generator
from app.ui.pages.ai_report_generator import (
    build_ai_report_generator_page,
    collect_experiments_data,
    generate_draft,
    get_experiment_choices,
    get_project_choices,
    save_draft,
)


class FakeExperimentService:
    """Test double listing and returning experiments without SQLite."""

    def __init__(self, experiments: list[dict[str, Any]]) -> None:
        self._experiments = {experiment["id"]: experiment for experiment in experiments}

    def list_experiments(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        project_id = filters.get("project_id")
        experiments = list(self._experiments.values())
        if project_id is None:
            return experiments
        return [
            experiment
            for experiment in experiments
            if experiment.get("project_id") == project_id
        ]

    def get_experiment(self, experiment_id: int) -> dict[str, Any] | None:
        return self._experiments.get(experiment_id)


class FakeProjectRepo:
    """Test double listing projects without SQLite."""

    def __init__(self, projects: list[dict[str, Any]]) -> None:
        self._projects = projects

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._projects)


class FakeAIService:
    """Test double generating drafts without Ollama."""

    def __init__(self, draft: str | None) -> None:
        self._draft = draft
        self.calls: list[tuple[list[Any], str, str]] = []

    def generate_report(
        self,
        experiments_data: Any,
        model: str,
        language: str = "English",
        on_progress: Any = None,
    ) -> str | None:
        self.calls.append((list(experiments_data), model, language))
        if self._draft is not None and on_progress is not None:
            on_progress(self._draft[:5])
            on_progress(self._draft)
        return self._draft


class FakeExportService:
    """Test double saving and exporting drafts without filesystem or SQLite."""

    def __init__(self, base: Path) -> None:
        self._base = base
        self.save_calls: list[tuple[str, list[int]]] = []
        self.markdown_calls: list[str] = []
        self.pdf_calls: list[str] = []
        self._next_id = 1

    def save_report(
        self,
        markdown_content: str,
        experiment_ids: list[int],
        project_id: int,
        title: str,
    ) -> int:
        self.save_calls.append(
            (markdown_content, list(experiment_ids), project_id, title)
        )
        report_id = self._next_id
        self._next_id += 1
        return report_id

    def export_ai_report_markdown(self, markdown_content: str) -> Path:
        self.markdown_calls.append(markdown_content)
        return self._base / "report.md"

    def export_ai_report_pdf(self, markdown_content: str) -> Path:
        self.pdf_calls.append(markdown_content)
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
    mock.style.return_value = mock
    return mock


def _container() -> MagicMock:
    mock = _chainable()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class _UIContext:
    def __init__(self) -> None:
        self.project_select = _chainable(None)
        self.project_handler: Any = None
        self.experiment_select = _chainable([1])
        self.model_select = _chainable(None)
        self.language_select = _chainable(None)
        self.title_input = _chainable("")
        self.select_handler: Any = None
        self.draft = _chainable("")
        self.draft_handler: Any = None
        self.draft_handlers: list[Any] = []
        self.preview = _chainable("")
        self.preview.content = ""
        self.message = _chainable()
        self.warning = _container()
        self.progress = _container()
        self.progress.visible = False
        self.progress.is_deleted = False
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
    pending = [page_container, context.warning, context.progress]

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
        context.draft_handlers.append(handler)
        context.draft_handler = handler
        return MagicMock()

    def capture_project_handler(handler: Any) -> MagicMock:
        context.project_handler = handler
        return MagicMock()

    mock_ui.column.side_effect = make_column
    mock_ui.row.side_effect = make_row
    mock_ui.select.side_effect = [
        context.project_select,
        context.experiment_select,
        context.model_select,
        context.language_select,
    ]
    mock_ui.input.return_value = context.title_input
    mock_ui.textarea.return_value = context.draft
    mock_ui.button.side_effect = context.button_factory
    mock_ui.spinner.return_value = _chainable()
    mock_ui.notify.return_value = None
    context.project_select.on_value_change.side_effect = capture_project_handler
    context.model_select.on_value_change.side_effect = capture_select_handler
    context.draft.on_value_change.side_effect = capture_draft_handler


def _setup_component_ui(mock_comp_ui: MagicMock, context: _UIContext) -> None:
    """Wire the shared markdown editor doubles to the page context."""
    mock_comp_ui.label.return_value = _chainable()
    mock_comp_ui.button.side_effect = lambda *args, **kwargs: _chainable()
    mock_comp_ui.row.side_effect = lambda *args, **kwargs: _container()
    mock_comp_ui.textarea.return_value = context.draft
    mock_comp_ui.markdown.return_value = context.preview


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


def _click_generate(mock_ui: MagicMock, context: _UIContext) -> None:
    """Drive the Generate handler and pump progress until it finishes."""
    context.buttons["Generate draft"].click()
    if context.progress.visible:
        _pump_until_hidden(mock_ui, context)


def _progress_timer_callback(mock_ui: MagicMock) -> Any:
    """Return the generation progress timer callback registered on the page."""
    for call in mock_ui.timer.call_args_list:
        interval = call.args[0] if call.args else call.kwargs.get("interval")
        if interval == 0.2:
            return call.args[1] if len(call.args) > 1 else call.kwargs["callback"]
    raise AssertionError("progress timer not found")


def _pump_until_hidden(
    mock_ui: MagicMock, context: _UIContext, timeout: float = 5.0
) -> None:
    """Drive the progress poller until the worker finishes or time runs out."""
    callback = _progress_timer_callback(mock_ui)
    deadline = time.time() + timeout
    while context.progress.visible and time.time() < deadline:
        callback()
        time.sleep(0.01)
    assert context.progress.visible is False


def _build_page(
    mock_ui: MagicMock,
    context: _UIContext,
    experiments: list[dict[str, Any]] | None = None,
    draft: str | None = "# Draft",
    installed: tuple[str, ...] = ("qwen3:4b", "gemma3:4b"),
    chosen_model: str | None = "qwen3:4b",
    chosen_language: str | None = "English",
    chosen_project: int | None = 10,
    chosen_title: str | None = "Monthly report",
    projects: list[dict[str, Any]] | None = None,
    base_dir: Path | None = None,
) -> tuple[FakeExperimentService, FakeAIService, FakeExportService]:
    experiments = (
        experiments
        if experiments is not None
        else [
            {"id": 1, "title": "Exp A", "project_id": 10},
            {"id": 2, "title": "Exp B", "project_id": 10},
        ]
    )
    projects = (
        projects
        if projects is not None
        else [{"id": 10, "name": "Project X"}, {"id": 20, "name": "Project Y"}]
    )
    experiment_service = FakeExperimentService(experiments)
    ai_service = FakeAIService(draft)
    export_service = FakeExportService(Path("/tmp"))
    ollama_client = FakeOllamaClient(installed)
    project_repo = FakeProjectRepo(projects)
    _setup_ui(mock_ui, context)
    # Drive the background model load inline with a local run double so
    # outer run mocks used by generation tests stay untouched.
    with patch("app.ui.components.markdown_editor.ui") as mock_comp_ui:
        _setup_component_ui(mock_comp_ui, context)
        with patch("app.ui.pages.ai_report_generator.run") as loader_run:
            loader_run.io_bound.side_effect = _inline_io_bound
            build_ai_report_generator_page(
                base_dir,
                experiment_service=experiment_service,  # type: ignore[arg-type]
                ai_service=ai_service,  # type: ignore[arg-type]
                export_service=export_service,  # type: ignore[arg-type]
                ollama_client=ollama_client,  # type: ignore[arg-type]
                project_repo=project_repo,  # type: ignore[arg-type]
            )
            _run_model_loader(mock_ui, context)
    if chosen_project is not None:
        context.project_select.value = chosen_project
    if chosen_title is not None:
        context.title_input.value = chosen_title
    if chosen_model is not None:
        context.model_select.value = chosen_model
    if chosen_language is not None:
        context.language_select.value = chosen_language
    if context.select_handler is not None:
        context.select_handler()
    return experiment_service, ai_service, export_service


def test_lists_experiments_of_selected_project_in_selector() -> None:
    # given
    experiment_service = FakeExperimentService(
        [
            {"id": 1, "title": "Exp A", "project_id": 10},
            {"id": 2, "title": "Exp B", "project_id": 20},
        ]
    )

    # when
    choices = get_experiment_choices(experiment_service, 10)  # type: ignore[arg-type]

    # then
    assert set(choices) == {1}
    assert "Exp A" in choices[1]


def test_lists_project_names_in_project_selector() -> None:
    # given
    project_repo = FakeProjectRepo(
        [{"id": 10, "name": "Project X"}, {"id": 20, "name": "Project Y"}]
    )

    # when
    choices = get_project_choices(project_repo)  # type: ignore[arg-type]

    # then
    assert choices == {10: "Project X", 20: "Project Y"}


def test_builds_project_selector_before_experiment_selector() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)

        # then — project first, experiments start empty until chosen
        assert mock_ui.select.call_count == 4
        project_call = mock_ui.select.call_args_list[0]
        assert project_call.kwargs["label"] == "Project"
        assert set(project_call.kwargs["options"]) == {10, 20}
        experiment_call = mock_ui.select.call_args_list[1]
        assert experiment_call.kwargs["multiple"] is True
        assert dict(experiment_call.kwargs["options"]) == {}


def test_populates_experiments_when_project_is_chosen() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(
            mock_ui,
            context,
            experiments=[
                {"id": 1, "title": "Exp A", "project_id": 10},
                {"id": 2, "title": "Exp B", "project_id": 20},
            ],
            chosen_project=None,
        )
        context.project_select.value = 20
        context.project_handler()

        # then — only the chosen project experiments, selection cleared
        set_call = context.experiment_select.set_options.call_args
        assert set(set_call.args[0]) == {2}
        assert set_call.kwargs.get("value") == []


def test_populates_model_dropdown_with_installed_models() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, installed=("qwen3:4b", "gemma3:4b"))

        # then — empty at build, filled when the background load finishes
        model_call = mock_ui.select.call_args_list[2]
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
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, ai_service, _ = _build_page(
            mock_ui,
            context,
            draft="# Report",
            chosen_model="gemma3:4b",
            chosen_language="English",
        )
        _click_generate(mock_ui, context)

        # then
        assert ai_service.calls == [
            (
                [{"id": 1, "title": "Exp A", "project_id": 10}],
                "gemma3:4b",
                "English",
            )
        ]
        assert context.draft.value == "# Report"
        assert context.warning.visible is False
        assert context.buttons["Save report"].enable.called


def test_shows_warning_with_hub_access_when_ai_not_ready() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, draft=None)
        with patch.object(ai_report_generator.router, "navigate") as mock_navigate:
            _click_generate(mock_ui, context)
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
        patch("app.ui.pages.ai_report_generator.run"),
    ):
        _, ai_service, _ = _build_page(mock_ui, context, chosen_model=None)
        _click_generate(mock_ui, context)

        # then
        assert ai_service.calls == []
        assert context.progress.visible is False


def test_disables_save_button_until_draft_exists() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)

        # then — draft starts empty, so nothing can be saved yet
        assert context.buttons["Save report"].disable.called


def test_enables_save_button_once_draft_has_content() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)
        context.draft.value = "# Edited draft"
        context.draft_handler()

        # then
        assert context.buttons["Save report"].enable.called


def test_disables_save_button_when_draft_is_cleared() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)
        context.draft.value = "# Edited draft"
        context.draft_handler()
        context.buttons["Save report"].disable.reset_mock()
        context.draft.value = "   "
        context.draft_handler()

        # then
        assert context.buttons["Save report"].disable.called


def test_shows_progress_while_generating() -> None:
    # given
    context = _UIContext()
    entered = threading.Event()
    release = threading.Event()

    def gating_generate(
        ai_service: Any,
        experiments_data: Any,
        model: str,
        language: str,
        on_progress: Any = None,
    ) -> str | None:
        if on_progress is not None:
            on_progress("# Partial")
        entered.set()
        assert release.wait(timeout=5)
        return "# Draft"

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        with patch.object(
            ai_report_generator, "generate_draft", side_effect=gating_generate
        ):
            _build_page(mock_ui, context)
            context.buttons["Generate draft"].click()
            assert entered.wait(timeout=5)
            _progress_timer_callback(mock_ui)()

            # then — spinner feedback visible with live preview mid-generation
            assert context.progress.visible is True
            assert mock_ui.spinner.called
            assert context.draft.value == "# Partial"

            # when — the worker finishes
            release.set()
            _pump_until_hidden(mock_ui, context)

            # then — feedback hidden and draft is final
            assert context.progress.visible is False
            assert context.draft.value == "# Draft"


def test_saves_edited_draft_to_database() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, _, export_service = _build_page(mock_ui, context)
        context.draft.value = "# Edited draft"
        context.buttons["Save report"].click()

        # then — database-only save, no file is exported
        assert export_service.save_calls == [
            ("# Edited draft", [1], 10, "Monthly report")
        ]
        assert export_service.markdown_calls == []
        assert export_service.pdf_calls == []


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
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, chosen_model="gemma3:4b", base_dir=tmp_path)
        _click_generate(mock_ui, context)

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
    draft = generate_draft(ai_service, [{"id": 1}], "qwen3:4b", "English")  # type: ignore[arg-type]

    # then
    assert draft is None


def test_saves_draft_to_database_without_exporting(tmp_path: Path) -> None:
    # given
    export_service = FakeExportService(tmp_path)

    # when
    report_id = save_draft(export_service, "# Draft", [1], 10, "Monthly report")  # type: ignore[arg-type]

    # then
    assert report_id == 1
    assert export_service.save_calls == [("# Draft", [1], 10, "Monthly report")]
    assert export_service.markdown_calls == []
    assert export_service.pdf_calls == []


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


def test_builds_language_selector_with_spanish_and_english_options() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)

        # then
        language_call = mock_ui.select.call_args_list[3]
        assert language_call.kwargs["label"] == "Language"
        assert list(language_call.kwargs["options"]) == ["Spanish", "English"]


def test_sends_chosen_language_when_generating() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, ai_service, _ = _build_page(
            mock_ui,
            context,
            draft="# Report",
            chosen_model="gemma3:4b",
            chosen_language="Spanish",
        )
        _click_generate(mock_ui, context)

        # then
        assert ai_service.calls[0][2] == "Spanish"
        assert context.draft.value == "# Report"


def test_leaves_language_empty_for_user_to_decide() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, chosen_language=None)

        # then — no automatic detection, the user must choose
        language_call = mock_ui.select.call_args_list[3]
        assert language_call.kwargs["value"] is None


def test_requires_language_before_generating() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, ai_service, _ = _build_page(
            mock_ui, context, chosen_model="gemma3:4b", chosen_language=None
        )
        _click_generate(mock_ui, context)

        # then
        assert ai_service.calls == []
        assert context.progress.visible is False


def test_uses_shared_markdown_editor_for_draft() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)

        # then — the draft comes from the shared editor, not a plain textarea
        mock_ui.textarea.assert_not_called()
        assert len(context.draft_handlers) == 2


def test_updates_preview_when_draft_changes() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context, draft="# Report")
        _click_generate(mock_ui, context)
        for handler in context.draft_handlers:
            handler()

        # then — the live preview follows the editable draft
        assert context.preview.content == "# Report"


def test_requires_saved_draft_before_saving() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, _, export_service = _build_page(mock_ui, context)
        context.draft.value = "   "
        context.buttons["Save report"].click()

        # then
        assert export_service.save_calls == []
        assert export_service.markdown_calls == []
        assert export_service.pdf_calls == []


def test_requires_experiments_before_saving() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, _, export_service = _build_page(mock_ui, context)
        context.draft.value = "# Edited draft"
        context.experiment_select.value = []
        context.buttons["Save report"].click()

        # then — saving links the report, so experiments are required
        assert export_service.save_calls == []


def test_requires_project_before_saving() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, _, export_service = _build_page(mock_ui, context, chosen_project=None)
        context.draft.value = "# Edited draft"
        context.buttons["Save report"].click()

        # then
        assert export_service.save_calls == []


def test_requires_title_before_saving() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _, _, export_service = _build_page(mock_ui, context, chosen_title=None)
        context.draft.value = "# Edited draft"
        context.buttons["Save report"].click()

        # then
        assert export_service.save_calls == []


def test_places_save_button_right_of_generate_button() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_report_generator, "ui") as mock_ui:
        _build_page(mock_ui, context)

        # then
        texts = [
            call.args[0] if call.args else call.kwargs.get("text", "")
            for call in mock_ui.button.call_args_list
        ]
        assert texts.index("Save report") == texts.index("Generate draft") + 1
