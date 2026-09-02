from __future__ import annotations

import logging
import sqlite3
from collections.abc import Sequence
from datetime import date
from typing import Any, Protocol

from app.repositories import equipment_repository, reagent_repository

logger = logging.getLogger(__name__)


class ReagentNotFoundError(ValueError):
    """Raised when linking an experiment to a reagent that does not exist."""


class EquipmentNotFoundError(ValueError):
    """Raised when linking an experiment to equipment that does not exist."""


class InventoryNameError(ValueError):
    """Raised when a reagent or equipment is created with a blank name."""


class ReagentRepository(Protocol):
    """Data access contract for reagents required by InventoryService."""

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
    ) -> int: ...

    def get_by_id(self, reagent_id: int) -> dict[str, Any] | None: ...

    def link_to_experiment(
        self,
        experiment_id: int,
        reagent_id: int,
        amount: float,
        unit: str,
    ) -> None: ...

    def unlink_from_experiment(
        self,
        experiment_id: int,
        reagent_id: int,
    ) -> None: ...

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]: ...

    def get_experiment_history(self, reagent_id: int) -> Sequence[dict[str, Any]]: ...


class EquipmentRepository(Protocol):
    """Data access contract for equipment required by InventoryService."""

    def create(self, name: str, description: str = "") -> int: ...

    def get_by_id(self, equipment_id: int) -> dict[str, Any] | None: ...

    def link_to_experiment(self, experiment_id: int, equipment_id: int) -> None: ...

    def unlink_from_experiment(self, experiment_id: int, equipment_id: int) -> None: ...

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]: ...


class SqliteReagentRepository:
    """Adapter that backs ReagentRepository with the SQLite reagent functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

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
        return reagent_repository.create(
            self._connection,
            name,
            cas_number,
            smiles,
            in_stock,
            lot_number,
            supplier,
            expiry_date,
            state,
            purity,
            is_explosive,
            is_flammable,
            is_oxidizer,
            is_gas_under_pressure,
            is_corrosive,
            is_acute_toxic,
            is_harmful_irritant,
            is_health_hazard,
            is_environmental_hazard,
        )

    def get_by_id(self, reagent_id: int) -> dict[str, Any] | None:
        return _row_to_dict(reagent_repository.get_by_id(self._connection, reagent_id))

    def get_all(self) -> Sequence[dict[str, Any]]:
        rows = reagent_repository.get_all(self._connection)
        return [_row_to_dict(row) for row in rows]

    def link_to_experiment(
        self,
        experiment_id: int,
        reagent_id: int,
        amount: float,
        unit: str,
    ) -> None:
        reagent_repository.link_to_experiment(
            self._connection, experiment_id, reagent_id, amount, unit
        )

    def unlink_from_experiment(
        self,
        experiment_id: int,
        reagent_id: int,
    ) -> None:
        reagent_repository.unlink_from_experiment(
            self._connection, experiment_id, reagent_id
        )

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        rows = reagent_repository.get_by_experiment(self._connection, experiment_id)
        return [_row_to_dict(row) for row in rows]

    def get_experiment_history(self, reagent_id: int) -> Sequence[dict[str, Any]]:
        rows = reagent_repository.get_experiment_history(self._connection, reagent_id)
        return [_row_to_dict(row) for row in rows]


class SqliteEquipmentRepository:
    """Adapter that backs EquipmentRepository with the SQLite equipment functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, name: str, description: str = "") -> int:
        return equipment_repository.create(self._connection, name, description)

    def get_by_id(self, equipment_id: int) -> dict[str, Any] | None:
        return _row_to_dict(
            equipment_repository.get_by_id(self._connection, equipment_id)
        )

    def get_all(self) -> Sequence[dict[str, Any]]:
        rows = equipment_repository.get_all(self._connection)
        return [_row_to_dict(row) for row in rows]

    def link_to_experiment(self, experiment_id: int, equipment_id: int) -> None:
        equipment_repository.link_to_experiment(
            self._connection, experiment_id, equipment_id
        )

    def unlink_from_experiment(self, experiment_id: int, equipment_id: int) -> None:
        equipment_repository.unlink_from_experiment(
            self._connection, experiment_id, equipment_id
        )

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        rows = equipment_repository.get_by_experiment(self._connection, experiment_id)
        return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return dict(row)


class InventoryService:
    """Business logic for managing reagents and equipment."""

    def __init__(
        self,
        reagent_repo: ReagentRepository,
        equipment_repo: EquipmentRepository,
    ) -> None:
        self._reagent_repo = reagent_repo
        self._equipment_repo = equipment_repo

    def add_reagent(
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
    ) -> dict[str, Any]:
        _require_valid_name(name, "Reagent")
        reagent_id = self._reagent_repo.create(
            name,
            cas_number,
            smiles,
            in_stock,
            lot_number,
            supplier,
            expiry_date,
            state,
            purity,
            is_explosive,
            is_flammable,
            is_oxidizer,
            is_gas_under_pressure,
            is_corrosive,
            is_acute_toxic,
            is_harmful_irritant,
            is_health_hazard,
            is_environmental_hazard,
        )
        reagent = self._reagent_repo.get_by_id(reagent_id)
        if reagent is None:
            raise ReagentNotFoundError(f"Reagent with id {reagent_id} was not created")

        logger.info("Reagent created reagent_id=%s", reagent_id)
        return reagent

    def add_equipment(self, name: str, description: str = "") -> dict[str, Any]:
        _require_valid_name(name, "Equipment")
        equipment_id = self._equipment_repo.create(name, description)
        equipment = self._equipment_repo.get_by_id(equipment_id)
        if equipment is None:
            raise EquipmentNotFoundError(
                f"Equipment with id {equipment_id} was not created"
            )

        logger.info("Equipment created equipment_id=%s", equipment_id)
        return equipment

    def link_reagent_to_experiment(
        self,
        experiment_id: int,
        reagent_id: int,
        amount: float,
        unit: str,
    ) -> None:
        if self._reagent_repo.get_by_id(reagent_id) is None:
            raise ReagentNotFoundError(f"Reagent with id {reagent_id} does not exist")

        self._reagent_repo.link_to_experiment(experiment_id, reagent_id, amount, unit)
        logger.info(
            "Reagent linked to experiment reagent_id=%s experiment_id=%s",
            reagent_id,
            experiment_id,
        )

    def unlink_reagent_from_experiment(
        self,
        experiment_id: int,
        reagent_id: int,
    ) -> None:
        self._reagent_repo.unlink_from_experiment(experiment_id, reagent_id)
        logger.info(
            "Reagent unlinked from experiment reagent_id=%s experiment_id=%s",
            reagent_id,
            experiment_id,
        )

    def link_equipment_to_experiment(
        self,
        experiment_id: int,
        equipment_id: int,
    ) -> None:
        if self._equipment_repo.get_by_id(equipment_id) is None:
            raise EquipmentNotFoundError(
                f"Equipment with id {equipment_id} does not exist"
            )

        self._equipment_repo.link_to_experiment(experiment_id, equipment_id)
        logger.info(
            "Equipment linked to experiment equipment_id=%s experiment_id=%s",
            equipment_id,
            experiment_id,
        )

    def unlink_equipment_from_experiment(
        self,
        experiment_id: int,
        equipment_id: int,
    ) -> None:
        self._equipment_repo.unlink_from_experiment(experiment_id, equipment_id)
        logger.info(
            "Equipment unlinked from experiment equipment_id=%s experiment_id=%s",
            equipment_id,
            experiment_id,
        )

    def get_reagent_history(self, reagent_id: int) -> Sequence[dict[str, Any]]:
        if self._reagent_repo.get_by_id(reagent_id) is None:
            raise ReagentNotFoundError(f"Reagent with id {reagent_id} does not exist")

        history = self._reagent_repo.get_experiment_history(reagent_id)
        logger.debug(
            "Reagent history fetched reagent_id=%s count=%s", reagent_id, len(history)
        )
        return history

    def get_experiment_resources(
        self, experiment_id: int
    ) -> dict[str, Sequence[dict[str, Any]]]:
        reagents = self._reagent_repo.get_by_experiment(experiment_id)
        equipment = self._equipment_repo.get_by_experiment(experiment_id)
        logger.debug(
            "Experiment resources fetched experiment_id=%s reagents=%s equipment=%s",
            experiment_id,
            len(reagents),
            len(equipment),
        )
        return {"reagents": reagents, "equipment": equipment}

    def list_reagents(self) -> Sequence[dict[str, Any]]:
        return list(self._reagent_repo.get_all())

    def list_equipment(self) -> Sequence[dict[str, Any]]:
        return list(self._equipment_repo.get_all())


def _require_valid_name(name: str, entity_name: str) -> None:
    if not name or not name.strip():
        raise InventoryNameError(f"{entity_name} name cannot be blank")
