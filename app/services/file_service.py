from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import BinaryIO, Protocol

logger = logging.getLogger(__name__)


class StoredFile(Protocol):
    """File-like object with a name and readable content."""

    name: str
    content: BinaryIO


class NiceGUIFile(Protocol):
    """Protocol matching NiceGUI's UploadEventArguments.file."""

    name: str

    async def read(self) -> bytes: ...


class FileService:
    """Only component aware of the filesystem for attachments."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def save_attachment(
        self, experiment_id: int, uploaded_file: StoredFile | NiceGUIFile
    ) -> str:
        """Store an uploaded file under BASE_DIR/attachments/{experiment_id}/.

        Returns the unique stored name (UUID plus original extension).
        """
        extension = Path(uploaded_file.name).suffix
        stored_name = f"{uuid.uuid4().hex}{extension}"

        destination_dir = self._attachments_dir(experiment_id)
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination = destination_dir / stored_name
        with destination.open("wb") as output:
            if hasattr(uploaded_file, "content"):
                output.write(uploaded_file.content.read())
            else:
                output.write(uploaded_file.read())

        logger.info(
            "Attachment saved experiment_id=%s stored_name=%s",
            experiment_id,
            stored_name,
        )
        return stored_name

    def save_attachment_bytes(
        self, experiment_id: int, file_name: str, content: bytes
    ) -> str:
        """Store raw bytes as an attachment under BASE_DIR/attachments/{experiment_id}/.

        Returns the unique stored name (UUID plus original extension).
        """
        extension = Path(file_name).suffix
        stored_name = f"{uuid.uuid4().hex}{extension}"

        destination_dir = self._attachments_dir(experiment_id)
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination = destination_dir / stored_name
        with destination.open("wb") as output:
            output.write(content)

        logger.info(
            "Attachment saved experiment_id=%s stored_name=%s",
            experiment_id,
            stored_name,
        )
        return stored_name

    def resolve_path(self, experiment_id: int, stored_name: str) -> Path:
        """Build the absolute path for an attachment stored name."""
        return self._attachments_dir(experiment_id) / stored_name

    def delete_attachment(self, experiment_id: int, stored_name: str) -> None:
        """Remove an attachment file from disk, ignoring missing files."""
        file_path = self.resolve_path(experiment_id, stored_name)
        try:
            file_path.unlink(missing_ok=True)
        except OSError as error:
            logger.error(
                "Attachment deletion failed experiment_id=%s stored_name=%s error=%s",
                experiment_id,
                stored_name,
                str(error),
            )
            raise

        logger.info(
            "Attachment deleted experiment_id=%s stored_name=%s",
            experiment_id,
            stored_name,
        )

    def _attachments_dir(self, experiment_id: int) -> Path:
        return self._base_dir / "attachments" / str(experiment_id)
