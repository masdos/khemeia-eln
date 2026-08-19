import io
from pathlib import Path

import pytest

from app.services.file_service import FileService


@pytest.fixture(name="service")
def service_fixture(tmp_path: Path) -> FileService:
    return FileService(tmp_path)


class FakeUploadedFile:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self.content = io.BytesIO(content)


class TestSaveAttachment:
    def test_saves_file_under_experiment_directory(
        self, service: FileService, tmp_path: Path
    ) -> None:
        # given
        uploaded = FakeUploadedFile("chromatogram.png", b"png-bytes")

        # when
        stored_name = service.save_attachment(42, uploaded)

        # then
        saved_path = tmp_path / "attachments" / "42" / stored_name
        assert saved_path.exists()
        assert saved_path.read_bytes() == b"png-bytes"

    def test_returns_stored_name_with_uuid_and_original_extension(
        self, service: FileService
    ) -> None:
        # given
        uploaded = FakeUploadedFile("report.pdf", b"pdf-bytes")

        # when
        stored_name = service.save_attachment(1, uploaded)

        # then
        assert stored_name.endswith(".pdf")
        base_name = stored_name[: -len(".pdf")]
        assert len(base_name) == 32
        assert int(base_name, 16) >= 0

    def test_creates_experiment_directory_if_missing(
        self, service: FileService, tmp_path: Path
    ) -> None:
        # given
        uploaded = FakeUploadedFile("data.csv", b"a,b,c")
        experiment_dir = tmp_path / "attachments" / "7"
        assert not experiment_dir.exists()

        # when
        service.save_attachment(7, uploaded)

        # then
        assert experiment_dir.exists()
        assert any(experiment_dir.iterdir())

    def test_preserves_original_extension_without_suffix(
        self, service: FileService
    ) -> None:
        # given
        uploaded = FakeUploadedFile("notes", b"content")

        # when
        stored_name = service.save_attachment(1, uploaded)

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
        stored_name = service.save_attachment(
            5, FakeUploadedFile("image.png", b"bytes")
        )

        # when
        path = service.resolve_path(5, stored_name)

        # then
        assert path.exists()
        assert path.name == stored_name


class TestDeleteAttachment:
    def test_deletes_attachment_file(self, service: FileService) -> None:
        # given
        stored_name = service.save_attachment(2, FakeUploadedFile("data.dat", b"data"))
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
        first_name = service.save_attachment(2, FakeUploadedFile("keep.txt", b"keep"))
        second_name = service.save_attachment(
            2, FakeUploadedFile("remove.txt", b"remove")
        )

        # when
        service.delete_attachment(2, second_name)

        # then
        assert service.resolve_path(2, first_name).exists()
        assert not service.resolve_path(2, second_name).exists()
