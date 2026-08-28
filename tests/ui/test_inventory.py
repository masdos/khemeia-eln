from __future__ import annotations

from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from app.services.inventory_service import InventoryService


class FakeReagentRepository:
    def __init__(self) -> None:
        self._reagents: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def create(self, name: str, *args: object, **kwargs: object) -> int:
        rid = self._next_id
        self._next_id += 1
        self._reagents[rid] = {"id": rid, "name": name, **kwargs}
        return rid

    def get_by_id(self, reagent_id: int) -> dict[str, Any] | None:
        return self._reagents.get(reagent_id)

    def get_all(self) -> Sequence[dict[str, Any]]:
        return list(self._reagents.values())

    def link_to_experiment(
        self, experiment_id: int, reagent_id: int, amount: float, unit: str
    ) -> None:
        pass

    def get_by_experiment(
        self, experiment_id: int
    ) -> Sequence[dict[str, Any]]:
        return []

    def get_experiment_history(
        self, reagent_id: int
    ) -> Sequence[dict[str, Any]]:
        return []


class FakeEquipmentRepository:
    def __init__(self) -> None:
        self._equipment: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def create(self, name: str, description: str = "") -> int:
        eid = self._next_id
        self._next_id += 1
        self._equipment[eid] = {
            "id": eid,
            "name": name,
            "description": description,
        }
        return eid

    def get_by_id(self, equipment_id: int) -> dict[str, Any] | None:
        return self._equipment.get(equipment_id)

    def get_all(self) -> Sequence[dict[str, Any]]:
        return list(self._equipment.values())

    def link_to_experiment(
        self, experiment_id: int, equipment_id: int
    ) -> None:
        pass

    def get_by_experiment(
        self, experiment_id: int
    ) -> Sequence[dict[str, Any]]:
        return []


def _make_chainable(value: str = "") -> MagicMock:
    mock = MagicMock()
    mock.value = value
    mock.props.return_value = mock
    mock.classes.return_value = mock
    return mock


def _make_service() -> InventoryService:
    return InventoryService(
        reagent_repo=FakeReagentRepository(),
        equipment_repo=FakeEquipmentRepository(),
    )


def test_inventory_page_renders_tabs() -> None:
    """Inventory page should render with Reagents and Equipment tabs."""
    service = _make_service()

    with patch(
        "app.ui.pages.inventory._get_service", return_value=service
    ):
        with patch("app.ui.pages.inventory.ui") as mock_ui:
            mock_ui.column.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.column.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.tabs.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.tabs.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.tab.return_value = MagicMock()
            mock_ui.tab_panels.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.tab_panels.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.tab_panel.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.tab_panel.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_ui.label.return_value = MagicMock()
            mock_ui.button.return_value = MagicMock()

            from app.ui.pages.inventory import build_inventory_page

            build_inventory_page()

            # Tabs were created
            assert mock_ui.tabs.called


def test_add_reagent_via_dialog() -> None:
    """Adding a reagent should call service.add_reagent."""
    service = _make_service()

    with patch(
        "app.ui.pages.inventory._get_service", return_value=service
    ):
        with patch("app.ui.pages.inventory.ui") as mock_ui:
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

            # Return different chainables per input call
            input_values = iter(["Ethanol", "", "", "", "", "", "", ""])
            mock_ui.input.side_effect = lambda *a, **kw: _make_chainable(
                next(input_values, "")
            )
            mock_ui.textarea.return_value = _make_chainable("")
            mock_ui.select.return_value = _make_chainable("liquid")
            # Each checkbox mock needs to support .value
            checkbox_mock = MagicMock()
            checkbox_mock.value = False
            mock_ui.checkbox.return_value = checkbox_mock
            mock_ui.label.return_value = MagicMock()
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )

            from app.ui.pages.inventory import _open_reagent_dialog

            refresh = MagicMock()
            _open_reagent_dialog(service, refresh)

            button_calls = mock_ui.button.call_args_list
            save_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Save":
                    save_button = call
                    break

            assert save_button is not None
            save_button.kwargs["on_click"]()

            reagents = service._reagent_repo.get_all()
            assert len(reagents) == 1
            assert reagents[0]["name"] == "Ethanol"


def test_add_equipment_via_dialog() -> None:
    """Adding equipment should call service.add_equipment."""
    service = _make_service()

    with patch(
        "app.ui.pages.inventory._get_service", return_value=service
    ):
        with patch("app.ui.pages.inventory.ui") as mock_ui:
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

            mock_ui.input.return_value = _make_chainable("HPLC")
            mock_ui.textarea.return_value = _make_chainable(
                "High perf. liquid chromatograph"
            )
            mock_ui.label.return_value = MagicMock()

            from app.ui.pages.inventory import (
                _open_equipment_dialog,
            )

            refresh = MagicMock()
            _open_equipment_dialog(service, refresh)

            button_calls = mock_ui.button.call_args_list
            save_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Save":
                    save_button = call
                    break

            assert save_button is not None
            save_button.kwargs["on_click"]()

            equipment = service._equipment_repo.get_all()
            assert len(equipment) == 1
            assert equipment[0]["name"] == "HPLC"


def test_rejects_blank_reagent_name() -> None:
    """Blank reagent name should show error."""
    service = _make_service()

    with patch(
        "app.ui.pages.inventory._get_service", return_value=service
    ):
        with patch("app.ui.pages.inventory.ui") as mock_ui:
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

            input_values = iter(["", "", "", "", "", "", "", ""])
            mock_ui.input.side_effect = lambda *a, **kw: _make_chainable(
                next(input_values, "")
            )
            mock_ui.textarea.return_value = _make_chainable("")
            mock_ui.select.return_value = _make_chainable("")
            checkbox_mock = MagicMock()
            checkbox_mock.value = False
            mock_ui.checkbox.return_value = checkbox_mock
            mock_ui.label.return_value = MagicMock()
            mock_ui.row.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_ui.row.return_value.__exit__ = MagicMock(
                return_value=False
            )

            from app.ui.pages.inventory import _open_reagent_dialog

            refresh = MagicMock()
            _open_reagent_dialog(service, refresh)

            button_calls = mock_ui.button.call_args_list
            save_button = None
            for call in button_calls:
                if call.args and call.args[0] == "Save":
                    save_button = call
                    break

            assert save_button is not None
            save_button.kwargs["on_click"]()

            reagents = service._reagent_repo.get_all()
            assert len(reagents) == 0
