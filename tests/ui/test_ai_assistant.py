from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from app.ui.pages import ai_assistant
from app.ui.pages.ai_assistant import (
    build_ai_assistant_page,
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
        self.calls: list[Any] = []

    def generate_report(self, experiments_data: Any) -> str | None:
        self.calls.append(list(experiments_data))
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


def _chainable(value: Any = None) -> MagicMock:
    mock = MagicMock()
    mock.value = value
    mock.text = ""
    mock.visible = True
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
        self.select = _chainable([1])
        self.draft = _chainable("")
        self.message = _chainable()
        self.warning = _container()
        self.buttons: dict[str, MagicMock] = {}

    def button_factory(self, *args: Any, **kwargs: Any) -> MagicMock:
        text = args[0] if args else kwargs.get("text", "")
        mock = _chainable()
        mock.text_value = text
        self.buttons[str(text)] = mock
        kwargs_on_click = kwargs.get("on_click")
        if kwargs_on_click is not None:
            mock.click = kwargs_on_click
        return mock


def _setup_ui(
    mock_ui: MagicMock, context: _UIContext, choices_value: Any = None
) -> None:
    if choices_value is not None:
        context.select.value = choices_value
    page_container = _container()
    pending = [page_container, context.warning]

    def make_column(*args: Any, **kwargs: Any) -> MagicMock:
        if pending:
            return pending.pop(0)
        return _container()

    def make_row(*args: Any, **kwargs: Any) -> MagicMock:
        return _container()

    mock_ui.column.side_effect = make_column
    mock_ui.row.side_effect = make_row
    mock_ui.label.side_effect = lambda *a, **k: _chainable()
    mock_ui.textarea.return_value = context.draft
    mock_ui.select.return_value = context.select
    mock_ui.button.side_effect = context.button_factory
    mock_ui.notify.return_value = None


def _build_page(
    mock_ui: MagicMock,
    context: _UIContext,
    experiments: list[dict[str, Any]] | None = None,
    draft: str | None = "# Draft",
    choices_value: Any = None,
) -> tuple[FakeExperimentService, FakeAIService, FakeExportService]:
    experiments = (
        experiments
        if experiments is not None
        else [{"id": 1, "title": "Exp A"}, {"id": 2, "title": "Exp B"}]
    )
    experiment_service = FakeExperimentService(experiments)
    ai_service = FakeAIService(draft)
    export_service = FakeExportService(Path("/tmp"))
    _setup_ui(mock_ui, context, choices_value)
    build_ai_assistant_page(
        experiment_service=experiment_service,  # type: ignore[arg-type]
        ai_service=ai_service,  # type: ignore[arg-type]
        export_service=export_service,  # type: ignore[arg-type]
    )
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
    with patch.object(ai_assistant, "ui") as mock_ui:
        _build_page(mock_ui, context)

        # then
        assert mock_ui.select.call_count == 1
        assert mock_ui.select.call_args.kwargs["multiple"] is True
        options = mock_ui.select.call_args.kwargs["options"]
        assert set(options) == {1, 2}


def test_generates_draft_into_editable_textarea() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_assistant, "ui") as mock_ui:
        _, ai_service, _ = _build_page(mock_ui, context, draft="# Report")
        context.buttons["Generate draft"].click()

        # then
        assert len(ai_service.calls) == 1
        assert context.draft.value == "# Report"
        assert context.warning.visible is False


def test_shows_warning_with_ai_reports_access_when_ai_not_ready() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_assistant, "ui") as mock_ui:
        _build_page(mock_ui, context, draft=None)
        with patch.object(ai_assistant.router, "navigate") as mock_navigate:
            context.buttons["Generate draft"].click()
            context.buttons["Go to AI Reports"].click()

            # then
            assert context.warning.visible is True
            mock_navigate.assert_called_once_with("ai_reports")
            assert context.draft.value == ""


def test_exports_edited_draft_to_markdown() -> None:
    # given
    context = _UIContext()

    # when
    with patch.object(ai_assistant, "ui") as mock_ui:
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
    with patch.object(ai_assistant, "ui") as mock_ui:
        _, _, export_service = _build_page(mock_ui, context)
        context.draft.value = "# Edited draft"
        context.buttons["Export PDF"].click()

        # then
        assert export_service.pdf_calls == [("# Edited draft", [1])]
        assert export_service.markdown_calls == []


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
    draft = generate_draft(ai_service, [{"id": 1}])  # type: ignore[arg-type]

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
