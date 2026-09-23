from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from app.services.report_service import ReportService


class FakeExportService:
    """Test double exporting saved reports without filesystem."""

    def __init__(self) -> None:
        self.markdown_calls: list[int] = []
        self.docx_calls: list[int] = []
        self.pdf_calls: list[int] = []

    def export_report_markdown(self, report_id: int) -> Path:
        self.markdown_calls.append(report_id)
        return Path(f"report_{report_id}.md")

    def export_report_docx(self, report_id: int) -> Path:
        self.docx_calls.append(report_id)
        return Path(f"report_{report_id}.docx")

    def export_report_pdf(self, report_id: int) -> Path:
        self.pdf_calls.append(report_id)
        return Path(f"report_{report_id}.pdf")


class FakeReportRepository:
    """In-memory fake for ReportService tests."""

    def __init__(self) -> None:
        self._reports: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def seed(self, project_id: int, title: str, content_markdown: str = "") -> int:
        report_id = self._next_id
        self._next_id += 1
        self._reports[report_id] = {
            "id": report_id,
            "project_id": project_id,
            "title": title,
            "content_markdown": content_markdown,
            "project_name": f"Project {project_id}",
            "created_at": "2026-01-01",
            "modified_at": "2026-01-02",
        }
        return report_id

    def get_all(
        self,
        project_id: int | None = None,
        search_text: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        return list(self._reports.values())

    def get_by_id(self, report_id: int) -> dict[str, Any] | None:
        return self._reports.get(report_id)

    def update(self, report_id: int, **fields: object) -> dict[str, Any] | None:
        report = self._reports.get(report_id)
        if report is None:
            return None
        report.update(fields)
        return report

    def delete(self, report_id: int) -> None:
        del self._reports[report_id]


def _make_chainable(value: str = "") -> MagicMock:
    """Create a mock that supports .props().classes() chaining."""
    mock = MagicMock()
    mock.value = value
    mock.text = ""
    mock.content = ""
    mock.props.return_value = mock
    mock.classes.return_value = mock
    mock.style.return_value = mock
    return mock


def _make_container() -> MagicMock:
    mock = _make_chainable()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def _mock_page_chrome(mock_ui: MagicMock) -> None:
    mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
    mock_ui.row.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ui.row.return_value.__exit__ = MagicMock(return_value=False)
    mock_ui.label.return_value = MagicMock()
    mock_ui.button.return_value = MagicMock()


def _build_with_mocks(mock_ui: MagicMock, report_id: int) -> MagicMock:
    """Build the detail page with component doubles, returning the draft mock."""
    draft = _make_chainable("# Content")
    with patch("app.ui.components.forms.ui") as mock_forms_ui:
        with patch("app.ui.components.meta.ui") as mock_meta_ui:
            with patch("app.ui.components.markdown_editor.ui") as mock_editor_ui:
                _mock_page_chrome(mock_ui)
                mock_forms_ui.label.return_value = MagicMock()
                mock_forms_ui.button.return_value = MagicMock()
                mock_meta_ui.label.return_value = MagicMock()
                mock_editor_ui.label.return_value = MagicMock()
                mock_editor_ui.button.side_effect = lambda *args, **kwargs: (
                    _make_chainable()
                )
                mock_editor_ui.row.side_effect = lambda *args, **kwargs: (
                    _make_container()
                )
                mock_editor_ui.textarea.return_value = draft
                mock_editor_ui.markdown.return_value = _make_chainable()
                mock_ui.input = MagicMock(return_value=_make_chainable("Report A"))

                from app.ui.pages.report_detail import build_report_detail_page

                with patch(
                    "app.ui.pages.report_detail.export_location_label",
                    return_value=None,
                ):
                    build_report_detail_page(report_id)
    return draft


def test_detail_page_prefills_title_and_content() -> None:
    """Detail page must show current title and content in inputs."""
    # given
    repo = FakeReportRepository()
    service = ReportService(repo)
    report_id = repo.seed(1, "Report A", "# Content")

    with patch("app.ui.pages.report_detail._get_service", return_value=service):
        with patch("app.ui.pages.report_detail.ui") as mock_ui:
            # when
            _build_with_mocks(mock_ui, report_id)

            # then
            assert mock_ui.input.call_args.kwargs["value"] == "Report A"
            assert mock_ui.input.call_args.args[0] == "Title *"


def test_saving_from_detail_updates_report() -> None:
    """Saving from the detail page must persist the new values."""
    # given
    repo = FakeReportRepository()
    service = ReportService(repo)
    report_id = repo.seed(1, "Report A", "# Old")

    with patch("app.ui.pages.report_detail._get_service", return_value=service):
        with patch("app.ui.pages.report_detail.ui") as mock_ui:
            with patch("app.ui.components.forms.ui") as mock_forms_ui:
                with patch("app.ui.components.meta.ui") as mock_meta_ui:
                    with patch(
                        "app.ui.components.markdown_editor.ui"
                    ) as mock_editor_ui:
                        _mock_page_chrome(mock_ui)
                        mock_forms_ui.label.return_value = MagicMock()
                        mock_forms_ui.row.return_value.__enter__ = MagicMock(
                            return_value=MagicMock()
                        )
                        mock_forms_ui.row.return_value.__exit__ = MagicMock(
                            return_value=False
                        )
                        save_handler: list = []

                        def capture_button(*args: Any, **kwargs: Any) -> MagicMock:
                            if args and args[0] == "Save":
                                save_handler.append(kwargs.get("on_click"))
                            return MagicMock()

                        mock_forms_ui.button.side_effect = capture_button
                        mock_meta_ui.label.return_value = MagicMock()
                        mock_editor_ui.label.return_value = MagicMock()
                        mock_editor_ui.button.side_effect = lambda *args, **kwargs: (
                            _make_chainable()
                        )
                        mock_editor_ui.row.side_effect = lambda *args, **kwargs: (
                            _make_container()
                        )
                        draft = _make_chainable("# Edited")
                        mock_editor_ui.textarea.return_value = draft
                        mock_editor_ui.markdown.return_value = _make_chainable()
                        title_input = _make_chainable("Edited title")
                        mock_ui.input = MagicMock(return_value=title_input)

                        from app.ui.pages.report_detail import (
                            build_report_detail_page,
                        )

                        with patch(
                            "app.ui.pages.report_detail.export_location_label",
                            return_value=None,
                        ):
                            build_report_detail_page(report_id)

                        # when - the Save button is pressed
                        assert len(save_handler) == 1
                        save_handler[0]()

                        # then
                        assert repo.get_by_id(report_id)["title"] == "Edited title"
                        assert (
                            repo.get_by_id(report_id)["content_markdown"] == "# Edited"
                        )


def test_detail_notifies_when_report_missing() -> None:
    """Missing report must notify without building the form."""
    # given
    service = ReportService(FakeReportRepository())

    with patch("app.ui.pages.report_detail._get_service", return_value=service):
        with patch("app.ui.pages.report_detail.ui") as mock_ui:
            from app.ui.pages.report_detail import build_report_detail_page

            # when
            build_report_detail_page(999)

            # then
            mock_ui.notify.assert_called_once_with("Report not found", type="negative")
            mock_ui.input.assert_not_called()


def _build_for_export(
    mock_ui: MagicMock, service: ReportService, report_id: int
) -> tuple[FakeExportService, MagicMock, dict[str, MagicMock], list[Any]]:
    """Build the page capturing buttons and content handlers for export tests."""
    export_service = FakeExportService()
    draft = _make_chainable("# Content")
    buttons: dict[str, MagicMock] = {}
    content_handlers: list[Any] = []

    def button_factory(*args: Any, **kwargs: Any) -> MagicMock:
        mock = _make_chainable()
        buttons[str(args[0]) if args else ""] = mock
        mock.click = kwargs.get("on_click")
        return mock

    with patch("app.ui.components.forms.ui") as mock_forms_ui:
        with patch("app.ui.components.meta.ui") as mock_meta_ui:
            with patch("app.ui.components.markdown_editor.ui") as mock_editor_ui:
                _mock_page_chrome(mock_ui)
                mock_forms_ui.label.return_value = MagicMock()
                mock_forms_ui.button.return_value = MagicMock()
                mock_meta_ui.label.return_value = MagicMock()
                mock_editor_ui.label.return_value = MagicMock()
                mock_editor_ui.button.side_effect = lambda *args, **kwargs: (
                    _make_chainable()
                )
                mock_editor_ui.row.side_effect = lambda *args, **kwargs: (
                    _make_container()
                )
                mock_editor_ui.textarea.return_value = draft

                def capture_content_handler(handler: Any) -> MagicMock:
                    content_handlers.append(handler)
                    return MagicMock()

                draft.on_value_change.side_effect = capture_content_handler
                mock_editor_ui.markdown.return_value = _make_chainable()
                mock_ui.input = MagicMock(return_value=_make_chainable("Report A"))
                mock_ui.button.side_effect = button_factory

                from app.ui.pages.report_detail import build_report_detail_page

                with patch(
                    "app.ui.pages.report_detail.export_location_label",
                    return_value=None,
                ) as mock_picker:
                    build_report_detail_page(
                        report_id,
                        export_service=export_service,  # type: ignore[arg-type]
                    )
                    buttons["__display_mock__"] = mock_picker
    return export_service, draft, buttons, content_handlers


def test_shows_exports_location_hint() -> None:
    """Export section must show a clickable folder path hint."""
    # given
    repo = FakeReportRepository()
    service = ReportService(repo)
    report_id = repo.seed(1, "Report A", "# Content")

    with patch("app.ui.pages.report_detail._get_service", return_value=service):
        with patch("app.ui.pages.report_detail.ui") as mock_ui:
            # when
            _, _, buttons, _ = _build_for_export(mock_ui, service, report_id)

            # then
            assert "__display_mock__" in buttons
            assert buttons["__display_mock__"].call_count == 1


def test_exports_saved_report_to_markdown_by_id() -> None:
    """Markdown export must export the saved report by identifier."""
    # given
    repo = FakeReportRepository()
    service = ReportService(repo)
    report_id = repo.seed(1, "Report A", "# Content")

    with patch("app.ui.pages.report_detail._get_service", return_value=service):
        with patch("app.ui.pages.report_detail.ui") as mock_ui:
            # when
            export_service, draft, buttons, _ = _build_for_export(
                mock_ui, service, report_id
            )
            draft.value = "# Edited"
            buttons["Markdown"].click()

            # then
            assert export_service.markdown_calls == [report_id]
            assert export_service.docx_calls == []
            assert export_service.pdf_calls == []
            mock_ui.notify.assert_called_with(
                f"Exported to report_{report_id}.md", type="positive"
            )


def test_exports_saved_report_to_docx_by_id() -> None:
    """DOCX export must export the saved report by identifier."""
    # given
    repo = FakeReportRepository()
    service = ReportService(repo)
    report_id = repo.seed(1, "Report A", "# Content")

    with patch("app.ui.pages.report_detail._get_service", return_value=service):
        with patch("app.ui.pages.report_detail.ui") as mock_ui:
            # when
            export_service, draft, buttons, _ = _build_for_export(
                mock_ui, service, report_id
            )
            draft.value = "# Edited"
            buttons["DOCX"].click()

            # then
            assert export_service.docx_calls == [report_id]
            assert export_service.markdown_calls == []
            assert export_service.pdf_calls == []
            mock_ui.notify.assert_called_with(
                f"Exported to report_{report_id}.docx", type="positive"
            )


def test_exports_saved_report_to_pdf_by_id() -> None:
    """PDF export must export the saved report by identifier."""
    # given
    repo = FakeReportRepository()
    service = ReportService(repo)
    report_id = repo.seed(1, "Report A", "# Content")

    with patch("app.ui.pages.report_detail._get_service", return_value=service):
        with patch("app.ui.pages.report_detail.ui") as mock_ui:
            # when
            export_service, draft, buttons, _ = _build_for_export(
                mock_ui, service, report_id
            )
            draft.value = "# Edited"
            buttons["PDF"].click()

            # then
            assert export_service.pdf_calls == [report_id]
            assert export_service.markdown_calls == []
            assert export_service.docx_calls == []
