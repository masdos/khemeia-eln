from pathlib import Path

import pytest

from app.services.file_service import FileService


@pytest.fixture(name="service")
def service_fixture(tmp_path: Path) -> FileService:
    return FileService(tmp_path)


class TestSaveAttachmentBytes:
    def test_saves_file_under_experiment_directory(
        self, service: FileService, tmp_path: Path
    ) -> None:
        # given — raw bytes as delivered by the async upload handler
        # when
        stored_name = service.save_attachment_bytes(
            42, "chromatogram.png", b"png-bytes"
        )

        # then
        saved_path = tmp_path / "attachments" / "42" / stored_name
        assert saved_path.exists()
        assert saved_path.read_bytes() == b"png-bytes"

    def test_returns_stored_name_with_uuid_and_original_extension(
        self, service: FileService
    ) -> None:
        # given
        # when
        stored_name = service.save_attachment_bytes(1, "report.pdf", b"pdf-bytes")

        # then
        assert stored_name.endswith(".pdf")
        base_name = stored_name[: -len(".pdf")]
        assert len(base_name) == 32
        assert int(base_name, 16) >= 0

    def test_creates_experiment_directory_if_missing(
        self, service: FileService, tmp_path: Path
    ) -> None:
        # given
        experiment_dir = tmp_path / "attachments" / "7"
        assert not experiment_dir.exists()

        # when
        service.save_attachment_bytes(7, "data.csv", b"a,b,c")

        # then
        assert experiment_dir.exists()
        assert any(experiment_dir.iterdir())

    def test_preserves_original_extension_without_suffix(
        self, service: FileService
    ) -> None:
        # given
        # when
        stored_name = service.save_attachment_bytes(1, "notes", b"content")

        # then
        assert stored_name == stored_name.rstrip(".txt")


class TestResolvePath:
    def test_builds_absolute_path_from_base_dir(
        self, service: FileService, tmp_path: Path
    ) -> None:
        # when
        path = service.resolve_path(3, "abc123.txt")

        # then
        assert path == tmp_path / "attachments" / "3" / "abc123.txt"
        assert path.is_absolute()

    def test_resolves_path_for_saved_attachment(self, service: FileService) -> None:
        # given
        stored_name = service.save_attachment_bytes(5, "image.png", b"bytes")

        # when
        path = service.resolve_path(5, stored_name)

        # then
        assert path.exists()
        assert path.name == stored_name


class TestDeleteAttachment:
    def test_deletes_attachment_file(self, service: FileService) -> None:
        # given
        stored_name = service.save_attachment_bytes(2, "data.dat", b"data")
        path = service.resolve_path(2, stored_name)
        assert path.exists()

        # when
        service.delete_attachment(2, stored_name)

        # then
        assert not path.exists()

    def test_is_idempotent_when_file_is_missing(self, service: FileService) -> None:
        # when / then
        service.delete_attachment(2, "missing.bin")

    def test_leaves_other_files_untouched(self, service: FileService) -> None:
        # given
        first_name = service.save_attachment_bytes(2, "keep.txt", b"keep")
        second_name = service.save_attachment_bytes(2, "remove.txt", b"remove")

        # when
        service.delete_attachment(2, second_name)

        # then
        assert service.resolve_path(2, first_name).exists()
        assert not service.resolve_path(2, second_name).exists()


class TestUiDeleteSequence:
    def test_removes_file_and_database_row_together(
        self, service: FileService, tmp_path: Path
    ) -> None:
        # given
        from app.database.connection import close_connection, get_connection
        from app.repositories import attachment_repository
        from app.repositories.experiment_repository import (
            create as create_experiment,
        )

        connection = get_connection(":memory:")
        try:
            project_id = connection.execute(
                "INSERT INTO projects (name) VALUES (?)", ("Project",)
            ).lastrowid
            connection.commit()
            protocol_id = connection.execute(
                "INSERT INTO protocols (name, content_markdown) VALUES (?, '# C')",
                ("Protocol",),
            ).lastrowid
            connection.commit()
            experiment_id = create_experiment(
                connection,
                project_id=project_id,
                protocol_id=protocol_id,
                title="Exp",
            )
            stored_name = service.save_attachment_bytes(
                experiment_id, "spectrum.png", b"png-bytes"
            )
            attachment_id = attachment_repository.create(
                connection, experiment_id, "spectrum.png", stored_name, ".png"
            )
            saved_path = tmp_path / "attachments" / str(experiment_id) / stored_name
            assert saved_path.exists()

            # when (same order as the experiment detail page delete handler)
            service.delete_attachment(experiment_id, stored_name)
            attachment_repository.delete(connection, attachment_id, experiment_id)

            # then
            assert not saved_path.exists()
            experiment_dir = tmp_path / "attachments" / str(experiment_id)
            assert list(experiment_dir.iterdir()) == []
            row = connection.execute(
                "SELECT * FROM attachments WHERE id = ?", (attachment_id,)
            ).fetchone()
            assert row is None
        finally:
            close_connection(connection)
