from __future__ import annotations

from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from app.services.inventory_service import InventoryService


class FakeReagentRepository:
    def get_by_id(self, reagent_id: int) -> dict[str, Any] | None:
        return None

    def link_to_experiment(
        self, experiment_id: int, reagent_id: int, amount: float, unit: str
    ) -> None:
        pass

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        return []

    def get_experiment_history(self, reagent_id: int) -> Sequence[dict[str, Any]]:
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
            "created_at": "2026-01-01",
        }
        return eid

    def get_by_id(self, equipment_id: int) -> dict[str, Any] | None:
        return self._equipment.get(equipment_id)

    def update(
        self, equipment_id: int, **fields: object
    ) -> dict[str, Any] | None:
        equipment = self._equipment.get(equipment_id)
        if equipment is None:
            return None
        equipment.update(fields)
        return equipment


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


def _mock_page_chrome(mock_ui: MagicMock) -> None:
    mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
    mock_ui.row.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ui.row.return_value.__exit__ = MagicMock(return_value=False)
    mock_ui.label.return_value = MagicMock()
    mock_ui.button.return_value = MagicMock()


def test_detail_page_prefills_current_values() -> None:
    """Detail page must show current name and description in inputs."""
    # given
    service = _make_service()
    equipment = service.add_equipment(name="HPLC", description="Chromatograph")

    with patch("app.ui.pages.equipment_detail._get_service", return_value=service):
        with patch("app.ui.pages.equipment_detail.ui") as mock_ui:
            _mock_page_chrome(mock_ui)
            mock_ui.input = MagicMock(return_value=_make_chainable("HPLC"))
            mock_ui.textarea = MagicMock(
                return_value=_make_chainable("Chromatograph")
            )

            from app.ui.pages.equipment_detail import build_equipment_detail_page

            # when
            build_equipment_detail_page(equipment["id"])

            # then
            assert mock_ui.input.call_args.kwargs["value"] == "HPLC"
            assert mock_ui.textarea.call_args.kwargs["value"] == "Chromatograph"


def test_saving_from_detail_updates_equipment() -> None:
    """Saving from the detail page must persist the new values."""
    # given
    service = _make_service()
    equipment = service.add_equipment(name="HPLC")

    with patch("app.ui.pages.equipment_detail._get_service", return_value=service):
        with patch("app.ui.pages.equipment_detail.ui") as mock_ui:
            _mock_page_chrome(mock_ui)
            mock_ui.input = MagicMock(return_value=_make_chainable("Renamed"))
            mock_ui.textarea = MagicMock(return_value=_make_chainable("New desc"))

            from app.ui.pages.equipment_detail import build_equipment_detail_page

            build_equipment_detail_page(equipment["id"])

            # when - the Save button is clicked
            save_button = None
            for call in mock_ui.button.call_args_list:
                if call.args and call.args[0] == "Save":
                    save_button = call
                    break

            assert save_button is not None
            save_button.kwargs["on_click"]()

            # then
            updated = service.get_equipment(equipment["id"])
            assert updated["name"] == "Renamed"
            assert updated["description"] == "New desc"
            mock_ui.notify.assert_called_once_with(
                "Equipment updated", type="positive"
            )


def test_back_button_returns_to_inventory() -> None:
    """Back button must navigate to the inventory page."""
    # given
    service = _make_service()
    equipment = service.add_equipment(name="HPLC")

    with patch("app.ui.pages.equipment_detail._get_service", return_value=service):
        with patch("app.ui.pages.equipment_detail.ui") as mock_ui:
            with patch("app.ui.pages.equipment_detail.router") as mock_router:
                _mock_page_chrome(mock_ui)
                mock_ui.input = MagicMock(return_value=_make_chainable("HPLC"))
                mock_ui.textarea = MagicMock(return_value=_make_chainable(""))

                from app.ui.pages.equipment_detail import build_equipment_detail_page

                build_equipment_detail_page(equipment["id"])

                # when - the back button is clicked
                back_button = None
                for call in mock_ui.button.call_args_list:
                    if call.kwargs.get("icon") == "arrow_back":
                        back_button = call
                        break

                assert back_button is not None
                back_button.kwargs["on_click"]()

                # then
                mock_router.navigate.assert_called_once_with("inventory")


def test_detail_notifies_when_equipment_missing() -> None:
    """Detail page must notify when the equipment does not exist."""
    # given
    service = _make_service()

    with patch("app.ui.pages.equipment_detail._get_service", return_value=service):
        with patch("app.ui.pages.equipment_detail.ui") as mock_ui:
            from app.ui.pages.equipment_detail import build_equipment_detail_page

            # when
            build_equipment_detail_page(999)

            # then
            mock_ui.notify.assert_called_once_with(
                "Equipment not found", type="negative"
            )
