from __future__ import annotations

import logging
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.repositories import (
    attachment_repository,
    equipment_repository,
    experiment_repository,
    project_repository,
    protocol_repository,
    reagent_repository,
)

logger = logging.getLogger(__name__)


class ExperimentNotFoundError(ValueError):
    """Raised when exporting an experiment that does not exist."""


class ExperimentRepository(Protocol):
    """Data access contract for experiment reads required by ExportService."""

    def get_by_id(self, experiment_id: int) -> dict[str, Any] | None: ...


class ReagentRepository(Protocol):
    """Data access contract for reagent reads required by ExportService."""

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]: ...


class EquipmentRepository(Protocol):
    """Data access contract for equipment reads required by ExportService."""

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]: ...


class ProjectRepository(Protocol):
    """Data access contract for project reads required by ExportService."""

    def get_by_id(self, project_id: int) -> dict[str, Any] | None: ...


class ProtocolRepository(Protocol):
    """Data access contract for protocol reads required by ExportService."""

    def get_by_id(self, protocol_id: int) -> dict[str, Any] | None: ...


class AttachmentRepository(Protocol):
    """Data access contract for attachment reads required by ExportService."""

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]: ...


class SqliteExperimentRepository:
    """Adapter that backs the experiment read contract with SQLite functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_id(self, experiment_id: int) -> dict[str, Any] | None:
        return _row_to_dict(
            experiment_repository.get_by_id(self._connection, experiment_id)
        )


class SqliteReagentRepository:
    """Adapter that backs the reagent read contract with SQLite functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        rows = reagent_repository.get_by_experiment(self._connection, experiment_id)
        return [_row_to_dict(row) for row in rows]


class SqliteEquipmentRepository:
    """Adapter that backs the equipment read contract with SQLite functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        rows = equipment_repository.get_by_experiment(self._connection, experiment_id)
        return [_row_to_dict(row) for row in rows]


class SqliteProjectRepository:
    """Adapter that backs the project read contract with SQLite functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_id(self, project_id: int) -> dict[str, Any] | None:
        return _row_to_dict(project_repository.get_by_id(self._connection, project_id))


class SqliteProtocolRepository:
    """Adapter that backs the protocol read contract with SQLite functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_id(self, protocol_id: int) -> dict[str, Any] | None:
        return _row_to_dict(
            protocol_repository.get_by_id(self._connection, protocol_id)
        )


class SqliteAttachmentRepository:
    """Adapter that backs the attachment read contract with SQLite functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_experiment(self, experiment_id: int) -> Sequence[dict[str, Any]]:
        rows = attachment_repository.get_by_experiment(self._connection, experiment_id)
        return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return dict(row)


class ExportService:
    """Generates Markdown and PDF exports of experiments."""

    def __init__(
        self,
        base_dir: Path,
        experiment_repo: ExperimentRepository,
        reagent_repo: ReagentRepository,
        equipment_repo: EquipmentRepository,
        project_repo: ProjectRepository,
        protocol_repo: ProtocolRepository,
        attachment_repo: AttachmentRepository,
        user_name: str = "",
        user_email: str = "",
    ) -> None:
        self._base_dir = base_dir
        self._experiment_repo = experiment_repo
        self._reagent_repo = reagent_repo
        self._equipment_repo = equipment_repo
        self._project_repo = project_repo
        self._protocol_repo = protocol_repo
        self._attachment_repo = attachment_repo
        self._user_name = user_name
        self._user_email = user_email

    def export_experiment_markdown(self, experiment_id: int) -> Path:
        """Export an experiment to Markdown under BASE_DIR/exports/."""
        experiment = self._experiment_repo.get_by_id(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(
                f"Experiment with id {experiment_id} does not exist"
            )

        reagents = self._reagent_repo.get_by_experiment(experiment_id)
        equipment = self._equipment_repo.get_by_experiment(experiment_id)
        project = self._project_repo.get_by_id(experiment.get("project_id"))
        protocol = self._protocol_repo.get_by_id(experiment.get("protocol_id"))
        attachments = self._attachment_repo.get_by_experiment(experiment_id)
        content = self._build_markdown(
            experiment, reagents, equipment, project, protocol, attachments
        )

        file_path = self._exports_dir() / f"experiment_{experiment_id}.md"
        file_path.write_text(content, encoding="utf-8")

        logger.info("Experiment exported to markdown experiment_id=%s", experiment_id)
        return file_path

    def export_experiment_pdf(self, experiment_id: int) -> Path:
        """Export an experiment to PDF under BASE_DIR/exports/."""
        experiment = self._experiment_repo.get_by_id(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(
                f"Experiment with id {experiment_id} does not exist"
            )

        reagents = self._reagent_repo.get_by_experiment(experiment_id)
        equipment = self._equipment_repo.get_by_experiment(experiment_id)
        project = self._project_repo.get_by_id(experiment.get("project_id"))
        protocol = self._protocol_repo.get_by_id(experiment.get("protocol_id"))
        attachments = self._attachment_repo.get_by_experiment(experiment_id)
        markdown = self._build_markdown(
            experiment, reagents, equipment, project, protocol, attachments
        )

        file_path = self._exports_dir() / f"experiment_{experiment_id}.pdf"
        _write_markdown_pdf(file_path, markdown)

        logger.info("Experiment exported to pdf experiment_id=%s", experiment_id)
        return file_path

    def _build_markdown(
        self,
        experiment: dict[str, Any],
        reagents: Sequence[dict[str, Any]],
        equipment: Sequence[dict[str, Any]],
        project: dict[str, Any] | None,
        protocol: dict[str, Any] | None,
        attachments: Sequence[dict[str, Any]],
    ) -> str:
        from datetime import date

        today = date.today().strftime("%Y-%m-%d")
        project_name = project["name"] if project else "_None_"
        protocol_name = protocol["name"] if protocol else "_None_"

        lines = [
            today,
            self._user_name,
            self._user_email,
            "",
            f"# {experiment['title']}",
            "",
            f"**Project:** {project_name}",
            f"**Protocol:** {protocol_name}",
            f"**State:** {experiment['state']}",
            "",
            "## Reaction Onset",
            "",
            experiment.get("reaction_onset") or "_No reaction onset recorded._",
            "",
            "## Workup",
            "",
            experiment.get("workup") or "_No workup recorded._",
            "",
            "## Purification",
            "",
            experiment.get("purification") or "_No purification recorded._",
            "",
            "## Notes",
            "",
            experiment.get("notes") or "_No notes recorded._",
            "",
            "## Reagents",
            "",
        ]
        if reagents:
            lines.extend(
                f"- {row['name']}"
                + (
                    f" ({row['amount_used']} {row['unit']})"
                    if row.get("amount_used") is not None
                    else ""
                )
                for row in reagents
            )
        else:
            lines.append("_No reagents recorded._")

        lines.extend(["", "## Equipment", ""])
        if equipment:
            lines.extend(f"- {row['name']}" for row in equipment)
        else:
            lines.append("_No equipment recorded._")

        lines.extend(["", "## Attachments", ""])
        if attachments:
            lines.extend(f"- {att['file_name']}" for att in attachments)
        else:
            lines.append("_No attachments._")

        return "\n".join(lines) + "\n"

    def _exports_dir(self) -> Path:
        exports_dir = self._base_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        return exports_dir


def _write_markdown_pdf(file_path: Path, markdown: str) -> None:
    """Render simple Markdown content into a PDF file."""
    styles = getSampleStyleSheet()
    heading_styles = {
        1: ParagraphStyle(
            "Heading1", parent=styles["Heading1"], textColor=colors.HexColor("#1F2937")
        ),
        2: ParagraphStyle(
            "Heading2", parent=styles["Heading2"], textColor=colors.HexColor("#374151")
        ),
        3: ParagraphStyle(
            "Heading3", parent=styles["Heading3"], textColor=colors.HexColor("#4B5563")
        ),
    }
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    document = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=file_path.stem,
    )

    flowables: list = []
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            flowables.append(Spacer(1, 6))
            continue

        if line.startswith("### "):
            flowables.append(
                Paragraph(
                    _convert_inline_markdown(_escape_html(line[4:])), heading_styles[3]
                )
            )
        elif line.startswith("## "):
            flowables.append(
                Paragraph(
                    _convert_inline_markdown(_escape_html(line[3:])), heading_styles[2]
                )
            )
        elif line.startswith("# "):
            flowables.append(
                Paragraph(
                    _convert_inline_markdown(_escape_html(line[2:])), heading_styles[1]
                )
            )
        elif line.startswith("- "):
            flowables.append(
                ListFlowable(
                    [
                        ListItem(
                            Paragraph(
                                _convert_inline_markdown(_escape_html(line[2:])),
                                body_style,
                            ),
                            leftIndent=18,
                        )
                    ],
                    bulletType="bullet",
                    start="•",
                )
            )
        else:
            flowables.append(
                Paragraph(_convert_inline_markdown(_escape_html(line)), body_style)
            )

    document.build(flowables)


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _convert_inline_markdown(text: str) -> str:
    """Convert **bold** and _italic_ markdown to ReportLab HTML tags."""
    import re

    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)
    return text
