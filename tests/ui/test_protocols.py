from __future__ import annotations

from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from app.services.protocol_service import (
    ProtocolDeletionError,
    ProtocolService,
)


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

    def get_all(
        self, search_text: str | None = None
    ) -> Sequence[dict[str, Any]]:
        results = list(self._protocols.values())
        if search_text:
            results = [
                p for p in results
                if search_text.lower() in p["name"].lower()
            ]
        return results

    def update(
        self, protocol_id: int, **fields: object
    ) -> dict[str, Any] | None:
        protocol = self._protocols.get(protocol_id)
        if protocol is None:
            return None
        protocol.update(fields)
        return protocol

    def delete(self, protocol_id: int) -> None:
        del self._protocols[protocol_id]


def _make_chainable(value: str = "") -> MagicMock:
    mock = MagicMock()
    mock.value = value
    mock.props.return_value = mock
    mock.classes.return_value = mock
    return mock


def _make_chainable_label() -> MagicMock:
    mock = MagicMock()
    mock.classes.return_value = mock
    return mock


def _make_service() -> tuple[ProtocolService, FakeProtocolRepository]:
    repo = FakeProtocolRepository()
    return ProtocolService(repo), repo


def test_protocols_page_lists_protocols() -> None:
    """Page should call list_protocols and render a table."""
    service, repo = _make_service()
    repo.create("SOP-A", "Content A")

    with patch(
        "app.ui.pages.protocols._get_service", return_value=service
    ):
        with patch("app.ui.pages.protocols.ui") as mock_ui:
            mock_ui.column.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.column.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.input.return_value = _make_chainable("")
            mock_ui.button.return_value = MagicMock()
            mock_ui.label.return_value = MagicMock()

            from app.ui.pages.protocols import build_protocols_page

            build_protocols_page()

            result = service.list_protocols()
            assert len(result) == 1


def test_create_protocol_via_dialog() -> None:
    """Creating a protocol should call service.create_protocol."""
    service, _repo = _make_service()

    with patch(
        "app.ui.pages.protocols._get_service", return_value=service
    ):
        with patch("app.ui.pages.protocols.ui") as mock_ui:
            mock_ui.column.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.column.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.input.return_value = _make_chainable("Test Protocol")
            mock_ui.textarea.return_value = _make_chainable("# SOP")
            mock_ui.button.return_value = MagicMock()
            mock_ui.label.return_value = MagicMock()
            mock_ui.markdown.return_value = MagicMock()

            from app.ui.pages.protocols import _open_create_dialog

            refresh = MagicMock()
            _open_create_dialog(service, refresh)

            button_calls = mock_ui.button.call_args_list
            create_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Create":
                    create_button = call
                    break

            assert create_button is not None
            create_button.kwargs["on_click"]()

            protocols = service.list_protocols()
            assert len(protocols) == 1


def test_edit_protocol_via_dialog() -> None:
    """Editing a protocol should call service.update_protocol."""
    service, _repo = _make_service()
    protocol = service.create_protocol("Original", "# Original")

    with patch(
        "app.ui.pages.protocols._get_service", return_value=service
    ):
        with patch("app.ui.pages.protocols.ui") as mock_ui:
            mock_ui.dialog.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.dialog.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.card.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.card.return_value.__exit__ = MagicMock(
                return_value=False
            )
            name_mock = _make_chainable("Updated")
            content_mock = _make_chainable("# Updated")
            mock_ui.input = MagicMock(return_value=name_mock)
            mock_ui.textarea = MagicMock(return_value=content_mock)
            mock_ui.label.return_value = MagicMock()
            mock_ui.markdown.return_value = MagicMock()

            from app.ui.pages.protocols import _open_edit_dialog

            refresh = MagicMock()
            _open_edit_dialog(service, protocol["id"], refresh)

            button_calls = mock_ui.button.call_args_list
            save_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Save":
                    save_button = call
                    break

            assert save_button is not None
            save_button.kwargs["on_click"]()

            updated = service.get_protocol(protocol["id"])
            assert updated["name"] == "Updated"


def test_delete_protocol_shows_error_for_linked_experiments() -> None:
    """Delete with linked experiments should show error message."""
    service, _repo = _make_service()
    protocol = service.create_protocol("Doomed", "# Doomed")

    def failing_delete(protocol_id: int) -> None:
        raise ProtocolDeletionError("Cannot delete")

    service.delete_protocol = failing_delete

    with patch(
        "app.ui.pages.protocols._get_service", return_value=service
    ):
        with patch("app.ui.pages.protocols.ui") as mock_ui:
            mock_ui.dialog.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.dialog.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.card.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.card.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.label.return_value = _make_chainable_label()
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )

            from app.ui.pages.protocols import _open_delete_dialog

            refresh = MagicMock()
            _open_delete_dialog(
                service, protocol["id"], "Doomed", refresh
            )

            button_calls = mock_ui.button.call_args_list
            delete_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Delete":
                    delete_button = call
                    break

            assert delete_button is not None
            delete_button.kwargs["on_click"]()

            message_label = mock_ui.label.return_value
            assert message_label.text == (
                "Cannot delete this protocol because it has "
                "associated experiments. Remove them first."
            )


def test_delete_protocol_succeeds() -> None:
    """Successful delete should close dialog and notify."""
    service, _repo = _make_service()
    protocol = service.create_protocol("ToDelete", "# Delete me")

    with patch(
        "app.ui.pages.protocols._get_service", return_value=service
    ):
        with patch("app.ui.pages.protocols.ui") as mock_ui:
            mock_ui.dialog.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.dialog.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.card.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.card.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.label.return_value = MagicMock()
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )

            from app.ui.pages.protocols import _open_delete_dialog

            refresh = MagicMock()
            _open_delete_dialog(
                service, protocol["id"], "ToDelete", refresh
            )

            button_calls = mock_ui.button.call_args_list
            delete_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Delete":
                    delete_button = call
                    break

            assert delete_button is not None
            delete_button.kwargs["on_click"]()

            protocols = service.list_protocols()
            assert len(protocols) == 0


def test_create_protocol_rejects_blank_name() -> None:
    """Creating with blank name should show error."""
    service, _repo = _make_service()

    with patch(
        "app.ui.pages.protocols._get_service", return_value=service
    ):
        with patch("app.ui.pages.protocols.ui") as mock_ui:
            mock_ui.column.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.column.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.input.return_value = _make_chainable("")
            mock_ui.textarea.return_value = _make_chainable("# Content")
            mock_ui.button.return_value = MagicMock()
            mock_ui.label.return_value = MagicMock()
            mock_ui.markdown.return_value = MagicMock()

            from app.ui.pages.protocols import _open_create_dialog

            refresh = MagicMock()
            _open_create_dialog(service, refresh)

            button_calls = mock_ui.button.call_args_list
            create_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Create":
                    create_button = call
                    break

            assert create_button is not None
            create_button.kwargs["on_click"]()

            protocols = service.list_protocols()
            assert len(protocols) == 0
