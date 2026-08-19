from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from app.services.export_service import ExperimentNotFoundError, ExportService


class InMemoryExperimentRepository:
    """Test double returning a single experiment without SQLite."""

    def __init__(self) -> None:
        self._experiments: dict[int, dict[str, Any]] = {}

    def add_experiment(self, experiment: dict[str, Any]) -> None:
        self._experiments[experiment["id"]] = experiment

    def get_by_id(self, experiment_id: int) -> dict[str, Any] | None:
        return self._experiments.get(experiment_id)


class InMemoryReagentRepository:
    """Test double returning linked reagents without SQLite."""

    def __init__(self) -> None:
        self._reagents_by_experiment: dict[int, list[dict[str, Any]]] = {}

    def add_to_experiment(self, experiment_id: int, reagent: dict[str, Any]) -> None:
        self._reagents_by_experiment.setdefault(experiment_id, []).append(reagent)

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        return self._reagents_by_experiment.get(experiment_id, [])


class InMemoryEquipmentRepository:
    """Test double returning linked equipment without SQLite."""

    def __init__(self) -> None:
        self._equipment_by_experiment: dict[int, list[dict[str, Any]]] = {}

    def add_to_experiment(self, experiment_id: int, equipment: dict[str, Any]) -> None:
        self._equipment_by_experiment.setdefault(experiment_id, []).append(equipment)

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        return self._equipment_by_experiment.get(experiment_id, [])


@pytest.fixture(name="experiment_repository")
def experiment_repository_fixture() -> InMemoryExperimentRepository:
    return InMemoryExperimentRepository()


@pytest.fixture(name="reagent_repository")
def reagent_repository_fixture() -> InMemoryReagentRepository:
    return InMemoryReagentRepository()


@pytest.fixture(name="equipment_repository")
def equipment_repository_fixture() -> InMemoryEquipmentRepository:
    return InMemoryEquipmentRepository()


@pytest.fixture(name="service")
def service_fixture(
    tmp_path: Path,
    experiment_repository: InMemoryExperimentRepository,
    reagent_repository: InMemoryReagentRepository,
    equipment_repository: InMemoryEquipmentRepository,
) -> ExportService:
    experiment_repository.add_experiment(
        {
            "id": 1,
            "title": "Synthesis of Aspirin",
            "state": "Success",
            "notes": "Acetylated salicylic acid at 90 C.",
            "created_at": "2026-01-01 00:00:00",
        }
    )
    reagent_repository.add_to_experiment(
        1,
        {
            "name": "Acetic anhydride",
            "amount_used": 5.0,
            "unit": "mL",
        },
    )
    reagent_repository.add_to_experiment(
        1,
        {"name": "Salicylic acid", "amount_used": 2.0, "unit": "g"},
    )
    equipment_repository.add_to_experiment(
        1, {"name": "Hotplate stirrer", "description": ""}
    )
    return ExportService(
        tmp_path,
        experiment_repository,
        reagent_repository,
        equipment_repository,
    )


class TestExportExperimentMarkdown:
    def test_writes_markdown_file_that_exists_and_is_not_empty(
        self, service: ExportService, tmp_path: Path
    ) -> None:
        # when
        file_path = service.export_experiment_markdown(1)

        # then
        assert file_path == tmp_path / "exports" / "experiment_1.md"
        assert file_path.exists()
        assert file_path.stat().st_size > 0

    def test_includes_title_state_notes_reagents_and_equipment(
        self, service: ExportService
    ) -> None:
        # when
        file_path = service.export_experiment_markdown(1)

        # then
        content = file_path.read_text(encoding="utf-8")
        assert "# Synthesis of Aspirin" in content
        assert "**State:** Success" in content
        assert "Acetylated salicylic acid" in content
        assert "Acetic anhydride (5.0 mL)" in content
        assert "Salicylic acid (2.0 g)" in content
        assert "Hotplate stirrer" in content

    def test_raises_not_found_for_missing_experiment(
        self, service: ExportService
    ) -> None:
        # when / then
        with pytest.raises(ExperimentNotFoundError, match="does not exist"):
            service.export_experiment_markdown(999)


class TestExportExperimentPdf:
    def test_writes_pdf_file_that_exists_and_is_not_empty(
        self, service: ExportService, tmp_path: Path
    ) -> None:
        # when
        file_path = service.export_experiment_pdf(1)

        # then
        assert file_path == tmp_path / "exports" / "experiment_1.pdf"
        assert file_path.exists()
        assert file_path.stat().st_size > 0

    def test_pdf_starts_with_pdf_header(self, service: ExportService) -> None:
        # when
        file_path = service.export_experiment_pdf(1)

        # then
        content = file_path.read_bytes()
        assert content.startswith(b"%PDF")

    def test_raises_not_found_for_missing_experiment(
        self, service: ExportService
    ) -> None:
        # when / then
        with pytest.raises(ExperimentNotFoundError, match="does not exist"):
            service.export_experiment_pdf(999)


class TestExportsDirectory:
    def test_creates_exports_directory_when_missing(
        self,
        tmp_path: Path,
        experiment_repository: InMemoryExperimentRepository,
        reagent_repository: InMemoryReagentRepository,
        equipment_repository: InMemoryEquipmentRepository,
    ) -> None:
        # given
        experiment_repository.add_experiment(
            {"id": 2, "title": "Lone", "state": "Running", "notes": None}
        )
        service = ExportService(
            tmp_path,
            experiment_repository,
            reagent_repository,
            equipment_repository,
        )
        exports_dir = tmp_path / "exports"
        assert not exports_dir.exists()

        # when
        service.export_experiment_markdown(2)

        # then
        assert exports_dir.exists()

    def test_writes_placeholder_when_no_notes_or_resources(
        self,
        tmp_path: Path,
        experiment_repository: InMemoryExperimentRepository,
        reagent_repository: InMemoryReagentRepository,
        equipment_repository: InMemoryEquipmentRepository,
    ) -> None:
        # given
        experiment_repository.add_experiment(
            {"id": 3, "title": "Bare", "state": "Running", "notes": None}
        )
        service = ExportService(
            tmp_path,
            experiment_repository,
            reagent_repository,
            equipment_repository,
        )

        # when
        file_path = service.export_experiment_markdown(3)

        # then
        content = file_path.read_text(encoding="utf-8")
        assert "_No notes recorded._" in content
        assert "_No reagents recorded._" in content
        assert "_No equipment recorded._" in content
