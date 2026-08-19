from collections.abc import Sequence
from datetime import date
from typing import Any

import pytest

from app.services.inventory_service import (
    EquipmentNotFoundError,
    InventoryNameError,
    InventoryService,
    ReagentNotFoundError,
)


class InMemoryReagentRepository:
    """Test double implementing ReagentRepository without SQLite."""

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
        expiry_date: date | None = None,
        state: str | None = None,
        purity: float | None = None,
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
        reagent_id = self._next_id
        self._next_id += 1
        self._reagents[reagent_id] = {
            "id": reagent_id,
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
        return reagent_id

    def get_by_id(self, reagent_id: int) -> dict[str, Any] | None:
        return self._reagents.get(reagent_id)

    def link_to_experiment(
        self,
        experiment_id: int,
        reagent_id: int,
        amount: float,
        unit: str,
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
        return [
            self._reagents[link["reagent_id"]]
            | {key: link[key] for key in ("amount_used", "unit")}
            for link in self._links
            if link["experiment_id"] == experiment_id
        ]

    def get_experiment_history(self, reagent_id: int) -> Sequence[dict[str, Any]]:
        return [
            {
                "id": link["experiment_id"],
                "title": f"Experiment {link['experiment_id']}",
                "state": "Running",
                "created_at": "2026-01-01 00:00:00",
                "amount_used": link["amount_used"],
                "unit": link["unit"],
            }
            for link in self._links
            if link["reagent_id"] == reagent_id
        ]


class InMemoryEquipmentRepository:
    """Test double implementing EquipmentRepository without SQLite."""

    def __init__(self) -> None:
        self._equipment: dict[int, dict[str, Any]] = {}
        self._links: dict[int, list[int]] = {}
        self._next_id = 1

    def create(self, name: str, description: str = "") -> int:
        equipment_id = self._next_id
        self._next_id += 1
        self._equipment[equipment_id] = {
            "id": equipment_id,
            "name": name,
            "description": description,
            "created_at": "2026-01-01 00:00:00",
            "modified_at": "2026-01-01 00:00:00",
        }
        return equipment_id

    def get_by_id(self, equipment_id: int) -> dict[str, Any] | None:
        return self._equipment.get(equipment_id)

    def link_to_experiment(self, experiment_id: int, equipment_id: int) -> None:
        self._links.setdefault(experiment_id, []).append(equipment_id)

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        return [
            self._equipment[equipment_id]
            for equipment_id in self._links.get(experiment_id, [])
        ]


@pytest.fixture(name="reagent_repository")
def reagent_repository_fixture() -> InMemoryReagentRepository:
    return InMemoryReagentRepository()


@pytest.fixture(name="equipment_repository")
def equipment_repository_fixture() -> InMemoryEquipmentRepository:
    return InMemoryEquipmentRepository()


@pytest.fixture(name="service")
def service_fixture(
    reagent_repository: InMemoryReagentRepository,
    equipment_repository: InMemoryEquipmentRepository,
) -> InventoryService:
    return InventoryService(reagent_repository, equipment_repository)


class TestAddReagent:
    def test_adds_reagent_and_returns_its_data(self, service: InventoryService) -> None:
        # when
        reagent = service.add_reagent(name="Sodium Chloride")

        # then
        assert reagent["name"] == "Sodium Chloride"
        assert reagent["in_stock"] is True
        assert reagent["id"] > 0

    def test_adds_reagent_with_full_ghs_hazard_fields(
        self, service: InventoryService
    ) -> None:
        # when
        reagent = service.add_reagent(
            name="Diethyl ether",
            cas_number="60-29-7",
            smiles="CCOCC",
            in_stock=True,
            lot_number="LOT-42",
            supplier="Sigma",
            expiry_date=date(2027, 5, 1),
            state="liquid",
            purity=99.9,
            is_flammable=True,
            is_explosive=False,
            is_oxidizer=True,
        )

        # then
        assert reagent["cas_number"] == "60-29-7"
        assert reagent["is_flammable"] is True
        assert reagent["is_oxidizer"] is True
        assert reagent["is_explosive"] is False
        assert reagent["purity"] == 99.9

    def test_rejects_blank_name(self, service: InventoryService) -> None:
        # when / then
        with pytest.raises(InventoryNameError, match="Reagent name cannot be blank"):
            service.add_reagent(name="   ")


class TestAddEquipment:
    def test_adds_equipment_and_returns_its_data(
        self, service: InventoryService
    ) -> None:
        # when
        equipment = service.add_equipment(
            name="Rotary evaporator", description="Büchi R-100"
        )

        # then
        assert equipment["name"] == "Rotary evaporator"
        assert equipment["description"] == "Büchi R-100"

    def test_rejects_blank_name(self, service: InventoryService) -> None:
        # when / then
        with pytest.raises(InventoryNameError, match="Equipment name cannot be blank"):
            service.add_equipment(name="")


class TestLinkReagentToExperiment:
    def test_links_reagent_with_amount_and_unit(
        self,
        service: InventoryService,
        reagent_repository: InMemoryReagentRepository,
    ) -> None:
        # given
        reagent_id = service.add_reagent(name="Acetic acid")["id"]

        # when
        service.link_reagent_to_experiment(1, reagent_id, amount=5.0, unit="mL")

        # then
        resources = service.get_experiment_resources(1)
        assert len(resources["reagents"]) == 1
        assert resources["reagents"][0]["amount_used"] == 5.0
        assert resources["reagents"][0]["unit"] == "mL"

    def test_rejects_linking_missing_reagent(self, service: InventoryService) -> None:
        # when / then
        with pytest.raises(ReagentNotFoundError, match="does not exist"):
            service.link_reagent_to_experiment(1, 999, amount=1.0, unit="g")


class TestLinkEquipmentToExperiment:
    def test_links_equipment_to_experiment(
        self,
        service: InventoryService,
    ) -> None:
        # given
        equipment_id = service.add_equipment(name="Hotplate stirrer")["id"]

        # when
        service.link_equipment_to_experiment(1, equipment_id)

        # then
        resources = service.get_experiment_resources(1)
        assert len(resources["equipment"]) == 1
        assert resources["equipment"][0]["name"] == "Hotplate stirrer"

    def test_rejects_linking_missing_equipment(self, service: InventoryService) -> None:
        # when / then
        with pytest.raises(EquipmentNotFoundError, match="does not exist"):
            service.link_equipment_to_experiment(1, 999)


class TestGetReagentHistory:
    def test_returns_experiments_where_reagent_was_used(
        self, service: InventoryService
    ) -> None:
        # given
        reagent_id = service.add_reagent(name="Sodium hydroxide")["id"]
        service.link_reagent_to_experiment(1, reagent_id, amount=2.0, unit="g")
        service.link_reagent_to_experiment(2, reagent_id, amount=0.5, unit="g")

        # when
        history = service.get_reagent_history(reagent_id)

        # then
        assert len(history) == 2
        assert {entry["id"] for entry in history} == {1, 2}
        assert all(entry["amount_used"] is not None for entry in history)

    def test_returns_empty_history_when_reagent_unused(
        self, service: InventoryService
    ) -> None:
        # given
        reagent_id = service.add_reagent(name="Unused reagent")["id"]

        # when
        history = service.get_reagent_history(reagent_id)

        # then
        assert history == []

    def test_rejects_history_for_missing_reagent(
        self, service: InventoryService
    ) -> None:
        # when / then
        with pytest.raises(ReagentNotFoundError, match="does not exist"):
            service.get_reagent_history(999)


class TestGetExperimentResources:
    def test_returns_empty_resources_for_unknown_experiment(
        self, service: InventoryService
    ) -> None:
        # when
        resources = service.get_experiment_resources(999)

        # then
        assert resources["reagents"] == []
        assert resources["equipment"] == []

    def test_returns_both_reagents_and_equipment(
        self, service: InventoryService
    ) -> None:
        # given
        reagent_id = service.add_reagent(name="Toluene")["id"]
        equipment_id = service.add_equipment(name="Separatory funnel")["id"]
        service.link_reagent_to_experiment(5, reagent_id, amount=20.0, unit="mL")
        service.link_equipment_to_experiment(5, equipment_id)

        # when
        resources = service.get_experiment_resources(5)

        # then
        assert len(resources["reagents"]) == 1
        assert resources["reagents"][0]["name"] == "Toluene"
        assert len(resources["equipment"]) == 1
        assert resources["equipment"][0]["name"] == "Separatory funnel"
