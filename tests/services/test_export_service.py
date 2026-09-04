from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from app.services.export_service import (
    ExperimentNotFoundError,
    ExportService,
    _convert_inline_markdown,
)


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


class InMemoryProjectRepository:
    """Test double returning project data without SQLite."""

    def __init__(self) -> None:
        self._projects: dict[int, dict[str, Any]] = {}

    def add_project(self, project: dict[str, Any]) -> None:
        self._projects[project["id"]] = project

    def get_by_id(self, project_id: int) -> dict[str, Any] | None:
        return self._projects.get(project_id)


class InMemoryProtocolRepository:
    """Test double returning protocol data without SQLite."""

    def __init__(self) -> None:
        self._protocols: dict[int, dict[str, Any]] = {}

    def add_protocol(self, protocol: dict[str, Any]) -> None:
        self._protocols[protocol["id"]] = protocol

    def get_by_id(self, protocol_id: int) -> dict[str, Any] | None:
        return self._protocols.get(protocol_id)


class InMemoryAttachmentRepository:
    """Test double returning attachment data without SQLite."""

    def __init__(self) -> None:
        self._attachments_by_experiment: dict[int, list[dict[str, Any]]] = {}

    def add_to_experiment(self, experiment_id: int, attachment: dict[str, Any]) -> None:
        self._attachments_by_experiment.setdefault(experiment_id, []).append(attachment)

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        return self._attachments_by_experiment.get(experiment_id, [])


@pytest.fixture(name="experiment_repository")
def experiment_repository_fixture() -> InMemoryExperimentRepository:
    return InMemoryExperimentRepository()


@pytest.fixture(name="reagent_repository")
def reagent_repository_fixture() -> InMemoryReagentRepository:
    return InMemoryReagentRepository()


@pytest.fixture(name="equipment_repository")
def equipment_repository_fixture() -> InMemoryEquipmentRepository:
    return InMemoryEquipmentRepository()


@pytest.fixture(name="project_repository")
def project_repository_fixture() -> InMemoryProjectRepository:
    return InMemoryProjectRepository()


@pytest.fixture(name="protocol_repository")
def protocol_repository_fixture() -> InMemoryProtocolRepository:
    return InMemoryProtocolRepository()


@pytest.fixture(name="attachment_repository")
def attachment_repository_fixture() -> InMemoryAttachmentRepository:
    return InMemoryAttachmentRepository()


@pytest.fixture(name="service")
def service_fixture(
    tmp_path: Path,
    experiment_repository: InMemoryExperimentRepository,
    reagent_repository: InMemoryReagentRepository,
    equipment_repository: InMemoryEquipmentRepository,
    project_repository: InMemoryProjectRepository,
    protocol_repository: InMemoryProtocolRepository,
    attachment_repository: InMemoryAttachmentRepository,
) -> ExportService:
    experiment_repository.add_experiment(
        {
            "id": 1,
            "title": "Synthesis of Aspirin",
            "state": "Success",
            "notes": "Acetylated salicylic acid at 90 C.",
            "created_at": "2026-01-01 00:00:00",
            "project_id": 1,
            "protocol_id": 1,
        }
    )
    project_repository.add_project({"id": 1, "name": "Aspirin Synthesis"})
    protocol_repository.add_protocol({"id": 1, "name": "Standard Protocol"})
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
        project_repository,
        protocol_repository,
        attachment_repository,
        user_name="Test User",
        user_email="test@example.com",
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
        assert "**Project:** Aspirin Synthesis" in content
        assert "**Protocol:** Standard Protocol" in content
        assert "Acetylated salicylic acid" in content
        assert "Acetic anhydride (5.0 mL)" in content
        assert "Salicylic acid (2.0 g)" in content
        assert "Hotplate stirrer" in content
        assert "Test User" in content
        assert "test@example.com" in content

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
        project_repository: InMemoryProjectRepository,
        protocol_repository: InMemoryProtocolRepository,
        attachment_repository: InMemoryAttachmentRepository,
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
            project_repository,
            protocol_repository,
            attachment_repository,
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
        project_repository: InMemoryProjectRepository,
        protocol_repository: InMemoryProtocolRepository,
        attachment_repository: InMemoryAttachmentRepository,
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
            project_repository,
            protocol_repository,
            attachment_repository,
        )

        # when
        file_path = service.export_experiment_markdown(3)

        # then
        content = file_path.read_text(encoding="utf-8")
        assert "_No notes recorded._" in content
        assert "_No reagents recorded._" in content
        assert "_No equipment recorded._" in content
        assert "_No reaction onset recorded._" in content
        assert "_No workup recorded._" in content
        assert "_No purification recorded._" in content


class TestConvertInlineMarkdown:
    def test_converts_bold_markers_to_html_tags(self) -> None:
        # given
        text = "**Project:** Aspirin Synthesis"

        # when
        result = _convert_inline_markdown(text)

        # then
        assert result == "<b>Project:</b> Aspirin Synthesis"

    def test_converts_italic_markers_to_html_tags(self) -> None:
        # given
        text = "_No notes recorded._"

        # when
        result = _convert_inline_markdown(text)

        # then
        assert result == "<i>No notes recorded.</i>"

    def test_preserves_text_without_inline_formatting(self) -> None:
        # given
        text = "Plain text without formatting"

        # when
        result = _convert_inline_markdown(text)

        # then
        assert result == "Plain text without formatting"

    def test_converts_multiple_bold_sections(self) -> None:
        # given
        text = "**Bold1** and **Bold2**"

        # when
        result = _convert_inline_markdown(text)

        # then
        assert result == "<b>Bold1</b> and <b>Bold2</b>"
