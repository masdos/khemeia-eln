from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from app.services.protocol_service import ProtocolService


class FakeProtocolRepository:
    """In-memory fake for ProtocolService tests."""

    def __init__(self) -> None:
        self._protocols: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def create(self, name: str, content_markdown: str) -> int:
        protocol_id = self._next_id
        self._next_id += 1
        self._protocols[protocol_id] = {
            "id": protocol_id,
            "name": name,
            "content_markdown": content_markdown,
            "created_at": "2026-01-01",
        }
        return protocol_id

    def get_by_id(self, protocol_id: int) -> dict[str, Any] | None:
        return self._protocols.get(protocol_id)

    def update(self, protocol_id: int, **fields: object) -> dict[str, Any] | None:
        protocol = self._protocols.get(protocol_id)
        if protocol is None:
            return None
        protocol.update(fields)
        return protocol


def _make_chainable(value: str = "") -> MagicMock:
    mock = MagicMock()
    mock.value = value
    mock.props.return_value = mock
    mock.classes.return_value = mock
    mock.style.return_value = mock
    return mock


def _make_service() -> ProtocolService:
    return ProtocolService(FakeProtocolRepository())


def _mock_page_chrome(mock_ui: MagicMock) -> None:
    mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
    mock_ui.label.return_value = MagicMock()


def _mock_editor_chrome(mock_editor_ui: MagicMock, content: str) -> None:
    mock_editor_ui.label.return_value = MagicMock()
    mock_editor_ui.row.return_value.__enter__ = MagicMock(
        return_value=MagicMock()
    )
    mock_editor_ui.row.return_value.__exit__ = MagicMock(return_value=False)
    mock_editor_ui.button.return_value = MagicMock()
    mock_editor_ui.textarea = MagicMock(return_value=_make_chainable(content))
    mock_editor_ui.markdown.return_value = MagicMock()


def test_detail_page_prefills_current_values() -> None:
    """Detail page must show current name and content in inputs."""
    # given
    service = _make_service()
    protocol = service.create_protocol("SOP-A", "# Content A")

    with patch("app.ui.pages.protocol_detail._get_service", return_value=service):
        with patch("app.ui.pages.protocol_detail.ui") as mock_ui:
            with patch("app.ui.components.forms.ui") as mock_forms_ui:
                with patch("app.ui.components.meta.ui") as mock_meta_ui:
                    with patch(
                        "app.ui.components.markdown_editor.ui"
                    ) as mock_editor_ui:
                        _mock_page_chrome(mock_ui)
                        mock_forms_ui.label.return_value = MagicMock()
                        mock_meta_ui.label.return_value = MagicMock()
                        mock_ui.input = MagicMock(
                            return_value=_make_chainable("SOP-A")
                        )
                        _mock_editor_chrome(mock_editor_ui, "# Content A")

                        from app.ui.pages.protocol_detail import (
                            build_protocol_detail_page,
                        )

                        # when
                        build_protocol_detail_page(protocol["id"])

                        # then
                        assert mock_ui.input.call_args.kwargs["value"] == "SOP-A"
                        assert mock_editor_ui.textarea.call_args.kwargs[
                            "value"
                        ] == "# Content A"


def test_saving_from_detail_updates_protocol() -> None:
    """Saving from the detail page must persist the new values."""
    # given
    service = _make_service()
    protocol = service.create_protocol("SOP-A", "# Content A")

    with patch("app.ui.pages.protocol_detail._get_service", return_value=service):
        with patch("app.ui.pages.protocol_detail.ui") as mock_ui:
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
                        mock_forms_ui.button.return_value = MagicMock()
                        mock_meta_ui.label.return_value = MagicMock()
                        mock_ui.input = MagicMock(
                            return_value=_make_chainable("SOP-B")
                        )
                        _mock_editor_chrome(mock_editor_ui, "# Content B")

                        from app.ui.pages.protocol_detail import (
                            build_protocol_detail_page,
                        )

                        build_protocol_detail_page(protocol["id"])

                        # when - the Save button is clicked
                        save_button = None
                        for call in mock_forms_ui.button.call_args_list:
                            if call.args and call.args[0] == "Save":
                                save_button = call
                                break

                        assert save_button is not None
                        save_button.kwargs["on_click"]()

                        # then
                        updated = service.get_protocol(protocol["id"])
                        assert updated["name"] == "SOP-B"
                        assert updated["content_markdown"] == "# Content B"
                        mock_ui.notify.assert_called_once_with(
                            "Protocol updated", type="positive"
                        )


def test_back_button_returns_to_protocols_list() -> None:
    """Back button must navigate to the protocols list."""
    # given
    service = _make_service()
    protocol = service.create_protocol("SOP-A", "# Content A")

    with patch("app.ui.pages.protocol_detail._get_service", return_value=service):
        with patch("app.ui.pages.protocol_detail.ui") as mock_ui:
            with patch("app.ui.components.forms.ui") as mock_forms_ui:
                with patch(
                    "app.ui.components.forms.router"
                ) as mock_router:
                    with patch("app.ui.components.meta.ui") as mock_meta_ui:
                        with patch(
                            "app.ui.components.markdown_editor.ui"
                        ) as mock_editor_ui:
                            _mock_page_chrome(mock_ui)
                            mock_forms_ui.label.return_value = MagicMock()
                            mock_forms_ui.button.return_value = MagicMock()
                            mock_meta_ui.label.return_value = MagicMock()
                            mock_ui.input = MagicMock(
                                return_value=_make_chainable("SOP-A")
                            )
                            _mock_editor_chrome(mock_editor_ui, "# Content A")

                            from app.ui.pages.protocol_detail import (
                                build_protocol_detail_page,
                            )

                            build_protocol_detail_page(protocol["id"])

                            # when - the back button is clicked
                            back_button = None
                            for call in mock_forms_ui.button.call_args_list:
                                if call.kwargs.get("icon") == "arrow_back":
                                    back_button = call
                                    break

                            assert back_button is not None
                            back_button.kwargs["on_click"]()

                            # then
                            mock_router.navigate.assert_called_once_with(
                                "protocols"
                            )


def test_detail_notifies_when_protocol_missing() -> None:
    """Detail page must notify when the protocol does not exist."""
    # given
    service = _make_service()

    with patch("app.ui.pages.protocol_detail._get_service", return_value=service):
        with patch("app.ui.pages.protocol_detail.ui") as mock_ui:
            from app.ui.pages.protocol_detail import build_protocol_detail_page

            # when
            build_protocol_detail_page(999)

            # then
            mock_ui.notify.assert_called_once_with(
                "Protocol not found", type="negative"
            )
