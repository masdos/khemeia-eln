from __future__ import annotations

import logging
import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from app.repositories import protocol_repository
from app.repositories.protocol_repository import ProtocolHasExperimentsError

logger = logging.getLogger(__name__)


class ProtocolNotFoundError(ValueError):
    """Raised when operating on a protocol that does not exist."""


class ProtocolDeletionError(ValueError):
    """Raised when a protocol with associated experiments cannot be deleted."""


class ProtocolValidationError(ValueError):
    """Raised when a protocol is created or updated with blank required fields."""


@runtime_checkable
class ProtocolRepository(Protocol):
    """Data access contract required by ProtocolService."""

    def create(self, name: str, content_markdown: str) -> int: ...

    def get_by_id(self, protocol_id: int) -> dict[str, Any] | None: ...

    def get_all(self, search_text: str | None = None) -> Sequence[dict[str, Any]]: ...

    def update(self, protocol_id: int, **fields: object) -> dict[str, Any] | None: ...

    def delete(self, protocol_id: int) -> None: ...


class SqliteProtocolRepository:
    """Adapter that backs ProtocolRepository with the SQLite protocol functions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, name: str, content_markdown: str) -> int:
        return protocol_repository.create(self._connection, name, content_markdown)

    def get_by_id(self, protocol_id: int) -> dict[str, Any] | None:
        return _row_to_dict(
            protocol_repository.get_by_id(self._connection, protocol_id)
        )

    def get_all(self, search_text: str | None = None) -> Sequence[dict[str, Any]]:
        rows = protocol_repository.get_all(self._connection, search_text=search_text)
        return [_row_to_dict(row) for row in rows]

    def update(self, protocol_id: int, **fields: object) -> dict[str, Any] | None:
        row = protocol_repository.update(self._connection, protocol_id, **fields)
        return _row_to_dict(row)

    def delete(self, protocol_id: int) -> None:
        protocol_repository.delete(self._connection, protocol_id)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return dict(row)


class ProtocolService:
    """Business logic for managing protocols. Never executes SQL directly."""

    def __init__(self, repository: ProtocolRepository) -> None:
        self._repository = repository

    def create_protocol(self, name: str, content_markdown: str) -> dict[str, Any]:
        _require_valid_name(name)
        _require_valid_content(content_markdown)
        protocol_id = self._repository.create(name, content_markdown)
        protocol = self._repository.get_by_id(protocol_id)
        if protocol is None:
            raise ProtocolNotFoundError(
                f"Protocol with id {protocol_id} was not created"
            )

        logger.info("Protocol created protocol_id=%s", protocol_id)
        return protocol

    def update_protocol(
        self,
        protocol_id: int,
        name: str | None = None,
        content_markdown: str | None = None,
    ) -> dict[str, Any]:
        if self._repository.get_by_id(protocol_id) is None:
            raise ProtocolNotFoundError(
                f"Protocol with id {protocol_id} does not exist"
            )

        fields: dict[str, object] = {}
        if name is not None:
            _require_valid_name(name)
            fields["name"] = name
        if content_markdown is not None:
            _require_valid_content(content_markdown)
            fields["content_markdown"] = content_markdown

        updated = self._repository.update(protocol_id, **fields)
        if updated is None:
            raise ProtocolNotFoundError(
                f"Protocol with id {protocol_id} does not exist"
            )

        logger.info("Protocol updated protocol_id=%s", protocol_id)
        return updated

    def delete_protocol(self, protocol_id: int) -> None:
        if self._repository.get_by_id(protocol_id) is None:
            raise ProtocolNotFoundError(
                f"Protocol with id {protocol_id} does not exist"
            )

        try:
            self._repository.delete(protocol_id)
        except ProtocolHasExperimentsError as error:
            raise ProtocolDeletionError(
                f"Protocol with id {protocol_id} cannot be deleted because "
                "it has associated experiments"
            ) from error

        logger.info("Protocol deleted protocol_id=%s", protocol_id)

    def get_protocol(self, protocol_id: int) -> dict[str, Any]:
        protocol = self._repository.get_by_id(protocol_id)
        if protocol is None:
            raise ProtocolNotFoundError(
                f"Protocol with id {protocol_id} does not exist"
            )

        return protocol

    def list_protocols(
        self,
        filters: Mapping[str, Any] | None = None,
    ) -> Sequence[dict[str, Any]]:
        search_text = None
        if filters:
            search_text = filters.get("search_text")

        protocols = self._repository.get_all(search_text=search_text)
        logger.debug("Protocols listed count=%s", len(protocols))
        return protocols


def _require_valid_name(name: str) -> None:
    if not name or not name.strip():
        raise ProtocolValidationError("Protocol name cannot be blank")


def _require_valid_content(content_markdown: str) -> None:
    if not content_markdown or not content_markdown.strip():
        raise ProtocolValidationError("Protocol content cannot be blank")
