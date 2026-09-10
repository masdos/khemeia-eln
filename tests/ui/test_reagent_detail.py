from __future__ import annotations

from typing import Any, Sequence
from unittest.mock import MagicMock, patch

from app.services.inventory_service import InventoryService


class FakeReagentRepository:
    def __init__(self) -> None:
        self._reagents: dict[int, dict[str, Any]] = {}
        self._links: list[dict[str, Any]] = []
        self._next_id = 1

    def create(
        self,
        name: str,
        cas_number: str = "",
        smiles: str = "",
        in_stock: bool = True,
        lot_number: str = "",
        supplier: str = "",
        expiry_date: object = None,
        state: object = None,
        purity: object = None,
        is_explosive: bool = False,
        is_flammable: bool = False,
        is_oxidizer: bool = False,
        is_gas_under_pressure: bool = False,
        is_corrosive: bool = False,
        is_acute_toxic: bool = False,
        is_harmful_irritant: bool = False,
        is_health_hazard: bool = False,
        is_environmental_hazard: bool = False,
    ) -> int:
        rid = self._next_id
        self._next_id += 1
        self._reagents[rid] = {
            "id": rid,
            "name": name,
            "cas_number": cas_number,
            "smiles": smiles,
            "in_stock": in_stock,
            "lot_number": lot_number,
            "supplier": supplier,
            "expiry_date": expiry_date,
            "state": state,
            "purity": purity,
            "is_explosive": is_explosive,
            "is_flammable": is_flammable,
            "is_oxidizer": is_oxidizer,
            "is_gas_under_pressure": is_gas_under_pressure,
            "is_corrosive": is_corrosive,
            "is_acute_toxic": is_acute_toxic,
            "is_harmful_irritant": is_harmful_irritant,
            "is_health_hazard": is_health_hazard,
            "is_environmental_hazard": is_environmental_hazard,
        }
        return rid

    def get_by_id(self, reagent_id: int) -> dict[str, Any] | None:
        return self._reagents.get(reagent_id)

    def update(self, reagent_id: int, **fields: object) -> dict[str, Any] | None:
        reagent = self._reagents.get(reagent_id)
        if reagent is None:
            return None
        reagent.update(fields)
        return reagent

    def link_to_experiment(
        self, experiment_id: int, reagent_id: int, amount: float, unit: str
    ) -> None:
        self._links.append(
            {
                "experiment_id": experiment_id,
                "reagent_id": reagent_id,
                "amount_used": amount,
                "unit": unit,
            }
        )

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        return []

    def get_experiment_history(self, reagent_id: int) -> Sequence[dict[str, Any]]:
        return [
            {
                "id": link["experiment_id"],
                "title": f"Experiment {link['experiment_id']}",
                "created_at": "2026-01-01 00:00:00",
                "amount_used": link["amount_used"],
                "unit": link["unit"],
            }
            for link in self._links
            if link["reagent_id"] == reagent_id
        ]


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

    def update(
        self, equipment_id: int, **fields: object
    ) -> dict[str, Any] | None:
        equipment = self._equipment.get(equipment_id)
        if equipment is None:
            return None
        equipment.update(fields)
        return equipment

    def link_to_experiment(self, experiment_id: int, equipment_id: int) -> None:
        pass

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
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


def _mock_page_chrome(
    mock_ui: MagicMock,
    mock_forms_ui: MagicMock,
    mock_ghs_ui: MagicMock,
    mock_meta_ui: MagicMock,
) -> None:
    mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
    mock_ui.label.return_value = MagicMock()
    mock_ui.separator.return_value = MagicMock()
    mock_forms_ui.label.return_value = MagicMock()
    mock_forms_ui.row.return_value.__enter__ = MagicMock(
        return_value=MagicMock()
    )
    mock_forms_ui.row.return_value.__exit__ = MagicMock(return_value=False)
    mock_forms_ui.button.return_value = MagicMock()
    mock_ghs_ui.label.return_value = MagicMock()
    mock_ghs_ui.row.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_ghs_ui.row.return_value.__exit__ = MagicMock(return_value=False)
    mock_meta_ui.label.return_value = MagicMock()


def _mock_form_inputs(
    mock_ui: MagicMock, mock_ghs_ui: MagicMock
) -> dict[str, MagicMock]:
    mocks = {
        "name": _make_chainable("Ethanol"),
        "cas": _make_chainable("64-17-5"),
        "smiles": _make_chainable("CCO"),
        "lot": _make_chainable("LOT-1"),
        "supplier": _make_chainable("Sigma"),
        "expiry": _make_chainable(""),
        "purity": _make_chainable(""),
    }
    mock_ui.input = MagicMock(
        side_effect=[
            mocks["name"],
            mocks["cas"],
            mocks["smiles"],
            mocks["lot"],
            mocks["supplier"],
            mocks["expiry"],
            mocks["purity"],
        ]
    )
    mock_ui.select = MagicMock(return_value=_make_chainable("liquid"))
    checkbox_mock = MagicMock()
    checkbox_mock.value = False
    mock_ghs_ui.checkbox = MagicMock(return_value=checkbox_mock)
    return mocks


def test_detail_page_prefills_current_values() -> None:
    """Detail page must show current reagent values in inputs."""
    # given
    service = _make_service()
    reagent = service.add_reagent(
        name="Ethanol", cas_number="64-17-5", smiles="CCO"
    )

    with patch("app.ui.pages.reagent_detail._get_service", return_value=service):
        with patch("app.ui.pages.reagent_detail.ui") as mock_ui:
            with patch("app.ui.components.forms.ui") as mock_forms_ui:
                with patch("app.ui.components.ghs.ui") as mock_ghs_ui:
                    with patch("app.ui.components.meta.ui") as mock_meta_ui:
                        _mock_page_chrome(
                            mock_ui, mock_forms_ui, mock_ghs_ui, mock_meta_ui
                        )
                        _mock_form_inputs(mock_ui, mock_ghs_ui)

                        from app.ui.pages.reagent_detail import (
                            build_reagent_detail_page,
                        )

                        # when
                        build_reagent_detail_page(reagent["id"])

                        # then
                        input_values = [
                            call.kwargs["value"]
                            for call in mock_ui.input.call_args_list
                        ]
                        assert input_values[0] == "Ethanol"
                        assert input_values[1] == "64-17-5"
                        assert input_values[2] == "CCO"


def test_saving_from_detail_updates_reagent() -> None:
    """Saving from the detail page must persist the new values."""
    # given
    service = _make_service()
    reagent = service.add_reagent(name="Ethanol")

    with patch("app.ui.pages.reagent_detail._get_service", return_value=service):
        with patch("app.ui.pages.reagent_detail.ui") as mock_ui:
            with patch("app.ui.components.forms.ui") as mock_forms_ui:
                with patch("app.ui.components.ghs.ui") as mock_ghs_ui:
                    with patch("app.ui.components.meta.ui") as mock_meta_ui:
                        _mock_page_chrome(
                            mock_ui, mock_forms_ui, mock_ghs_ui, mock_meta_ui
                        )
                        mocks = _mock_form_inputs(mock_ui, mock_ghs_ui)
                        mocks["name"].value = "Renamed"

                        from app.ui.pages.reagent_detail import (
                            build_reagent_detail_page,
                        )

                        build_reagent_detail_page(reagent["id"])

                        # when - the Save button is clicked
                        save_button = None
                        for call in mock_forms_ui.button.call_args_list:
                            if call.args and call.args[0] == "Save":
                                save_button = call
                                break

                        assert save_button is not None
                        save_button.kwargs["on_click"]()

                        # then
                        assert service.get_reagent(reagent["id"])["name"] == (
                            "Renamed"
                        )
                        mock_ui.notify.assert_called_once_with(
                            "Reagent updated", type="positive"
                        )


def test_cas_and_smiles_locked_when_reagent_has_history() -> None:
    """CAS and SMILES must be disabled when the reagent was used."""
    # given
    service = _make_service()
    reagent = service.add_reagent(name="Ethanol")
    service.link_reagent_to_experiment(1, reagent["id"], amount=2.0, unit="g")

    with patch("app.ui.pages.reagent_detail._get_service", return_value=service):
        with patch("app.ui.pages.reagent_detail.ui") as mock_ui:
            with patch("app.ui.components.forms.ui") as mock_forms_ui:
                with patch("app.ui.components.ghs.ui") as mock_ghs_ui:
                    with patch("app.ui.components.meta.ui") as mock_meta_ui:
                        with patch("app.ui.components.tables.ui"):
                            _mock_page_chrome(
                                mock_ui, mock_forms_ui, mock_ghs_ui, mock_meta_ui
                            )
                            mocks = _mock_form_inputs(mock_ui, mock_ghs_ui)

                            from app.ui.pages.reagent_detail import (
                                build_reagent_detail_page,
                            )

                            # when
                            build_reagent_detail_page(reagent["id"])

                            # then
                            for key in ("cas", "smiles"):
                                props_calls = [
                                    call.args
                                    for call in mocks[key].props.call_args_list
                                ]
                                assert ("disable",) in props_calls


def test_cas_and_smiles_enabled_without_history() -> None:
    """CAS and SMILES must stay editable when the reagent is unused."""
    # given
    service = _make_service()
    reagent = service.add_reagent(name="Ethanol")

    with patch("app.ui.pages.reagent_detail._get_service", return_value=service):
        with patch("app.ui.pages.reagent_detail.ui") as mock_ui:
            with patch("app.ui.components.forms.ui") as mock_forms_ui:
                with patch("app.ui.components.ghs.ui") as mock_ghs_ui:
                    with patch("app.ui.components.meta.ui") as mock_meta_ui:
                        _mock_page_chrome(
                            mock_ui, mock_forms_ui, mock_ghs_ui, mock_meta_ui
                        )
                        mocks = _mock_form_inputs(mock_ui, mock_ghs_ui)

                        from app.ui.pages.reagent_detail import (
                            build_reagent_detail_page,
                        )

                        # when
                        build_reagent_detail_page(reagent["id"])

                        # then
                        for key in ("cas", "smiles"):
                            props_calls = [
                                call.args
                                for call in mocks[key].props.call_args_list
                            ]
                            assert ("disable",) not in props_calls


def test_back_button_returns_to_inventory() -> None:
    """Back button must navigate to the inventory page."""
    # given
    service = _make_service()
    reagent = service.add_reagent(name="Ethanol")

    with patch("app.ui.pages.reagent_detail._get_service", return_value=service):
        with patch("app.ui.pages.reagent_detail.ui") as mock_ui:
            with patch("app.ui.components.forms.ui") as mock_forms_ui:
                with patch(
                    "app.ui.components.forms.router"
                ) as mock_router:
                    with patch("app.ui.components.ghs.ui") as mock_ghs_ui:
                        with patch("app.ui.components.meta.ui") as mock_meta_ui:
                            _mock_page_chrome(
                                mock_ui, mock_forms_ui, mock_ghs_ui, mock_meta_ui
                            )
                            _mock_form_inputs(mock_ui, mock_ghs_ui)

                            from app.ui.pages.reagent_detail import (
                                build_reagent_detail_page,
                            )

                            build_reagent_detail_page(reagent["id"])

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
                                "inventory"
                            )


def test_detail_notifies_when_reagent_missing() -> None:
    """Detail page must notify when the reagent does not exist."""
    # given
    service = _make_service()

    with patch("app.ui.pages.reagent_detail._get_service", return_value=service):
        with patch("app.ui.pages.reagent_detail.ui") as mock_ui:
            from app.ui.pages.reagent_detail import build_reagent_detail_page

            # when
            build_reagent_detail_page(999)

            # then
            mock_ui.notify.assert_called_once_with(
                "Reagent not found", type="negative"
            )
