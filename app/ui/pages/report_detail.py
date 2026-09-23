from __future__ import annotations

import logging
from pathlib import Path

from nicegui import ui

from app.config import get_current_config
from app.database.connection import get_connection
from app.services.export_service import ExportService, SqliteReportRepository
from app.services.export_service import (
    SqliteAttachmentRepository as ExportSqliteAttachmentRepository,
)
from app.services.export_service import (
    SqliteEquipmentRepository as ExportSqliteEquipmentRepository,
)
from app.services.export_service import (
    SqliteExperimentRepository as ExportSqliteExperimentRepository,
)
from app.services.export_service import (
    SqliteProjectRepository as ExportSqliteProjectRepository,
)
from app.services.export_service import (
    SqliteProtocolRepository as ExportSqliteProtocolRepository,
)
from app.services.export_service import (
    SqliteReagentRepository as ExportSqliteReagentRepository,
)
from app.services.report_service import (
    ReportNotFoundError,
    ReportService,
    ReportTitleError,
)
from app.services.report_service import (
    SqliteReportRepository as DetailSqliteReportRepository,
)
from app.ui.components.export_location import export_location_label
from app.ui.components.forms import (
    back_button,
    detail_save_row,
    form_message,
)
from app.ui.components.markdown_editor import markdown_editor
from app.ui.components.meta import entity_meta

logger = logging.getLogger(__name__)


def _get_service() -> ReportService:
    repo = DetailSqliteReportRepository(get_connection())
    return ReportService(repo)


def _get_export_service(base_dir: Path) -> ExportService:
    conn = get_connection()
    config = get_current_config()
    return ExportService(
        base_dir=base_dir,
        experiment_repo=ExportSqliteExperimentRepository(conn),
        reagent_repo=ExportSqliteReagentRepository(conn),
        equipment_repo=ExportSqliteEquipmentRepository(conn),
        project_repo=ExportSqliteProjectRepository(conn),
        protocol_repo=ExportSqliteProtocolRepository(conn),
        attachment_repo=ExportSqliteAttachmentRepository(conn),
        user_name=config.user_name,
        user_email=config.user_email,
        user_institution=config.institution or "",
        report_repo=SqliteReportRepository(conn),
    )


def build_report_detail_page(
    report_id: int,
    base_dir: Path | None = None,
    *,
    export_service: ExportService | None = None,
) -> None:
    """Build the report detail/edit page."""
    service = _get_service()

    try:
        report = service.get_report(report_id)
    except ReportNotFoundError:
        ui.notify("Report not found", type="negative")
        return

    if base_dir is None:
        from app.bootstrap import run_bootstrap

        base_dir = run_bootstrap().base_dir

    with ui.column().classes("w-full max-w-6xl mt-8 px-4"):
        title_label = ui.label(report["title"]).classes("text-2xl font-semibold")

        entity_meta(report.get("created_at"), report.get("modified_at"))

        ui.label(f"Project: {report.get('project_name') or ''}").classes(
            "text-sm text-slate-500"
        )

        title_input = (
            ui.input("Title *", value=report["title"])
            .props("outlined")
            .classes("w-full")
        )
        content_input = markdown_editor("Content", report.get("content_markdown") or "")

        message = form_message()

        def save_report() -> None:
            try:
                updated = service.update_report(
                    report_id=report_id,
                    title=title_input.value,
                    content_markdown=content_input.value,
                )
                title_label.text = updated["title"]
                message.text = ""
                ui.notify("Report updated", type="positive")
            except (ReportTitleError, ReportNotFoundError) as error:
                message.text = str(error)

        detail_save_row(save_report)

        ui.separator().classes("mt-6")
        ui.label("Export").classes("text-xl font-semibold mt-4")

        def on_export(file_format: str) -> None:
            svc = export_service or _get_export_service(base_dir)
            try:
                if file_format == "pdf":
                    file_path = svc.export_report_pdf(report_id)
                elif file_format == "docx":
                    file_path = svc.export_report_docx(report_id)
                else:
                    file_path = svc.export_report_markdown(report_id)
            except (ValueError, RuntimeError) as error:
                ui.notify(str(error), type="negative")
                return
            ui.notify(f"Exported to {file_path.name}", type="positive")

        with ui.row().classes("gap-2"):
            ui.button("Markdown", on_click=lambda: on_export("md")).props(
                "color=primary"
            )
            ui.button("DOCX", on_click=lambda: on_export("docx")).props("color=primary")
            ui.button("PDF", on_click=lambda: on_export("pdf")).props("color=primary")

        export_location_label(base_dir / "exports")

        back_button("reports")
