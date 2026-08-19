from collections.abc import Sequence
from typing import Any

import pytest

from app.repositories.protocol_repository import ProtocolHasExperimentsError
from app.services.protocol_service import (
    ProtocolDeletionError,
    ProtocolNotFoundError,
    ProtocolService,
    ProtocolValidationError,
)


class InMemoryProtocolRepository:
    """Test double implementing ProtocolRepository without SQLite."""

    def __init__(self) -> None:
        self._protocols: dict[int, dict[str, Any]] = {}
        self._experiment_count_by_protocol: dict[int, int] = {}
        self._next_id = 1

    def create(self, name: str, content_markdown: str) -> int:
        protocol_id = self._next_id
        self._next_id += 1
        self._protocols[protocol_id] = {
            "id": protocol_id,
            "name": name,
            "content_markdown": content_markdown,
            "created_at": "2026-01-01 00:00:00",
            "modified_at": "2026-01-01 00:00:00",
        }
        return protocol_id

    def get_by_id(self, protocol_id: int) -> dict[str, Any] | None:
        return self._protocols.get(protocol_id)

    def get_all(self, search_text: str | None = None) -> Sequence[dict[str, Any]]:
        protocols = list(self._protocols.values())
        if search_text is not None and search_text.strip():
            term = search_text.strip().lower()
            protocols = [
                p
                for p in protocols
                if term in p["name"].lower() or term in p["content_markdown"].lower()
            ]
        return sorted(protocols, key=lambda p: p["id"], reverse=True)

    def update(self, protocol_id: int, **fields: object) -> dict[str, Any] | None:
        protocol = self._protocols.get(protocol_id)
        if protocol is None:
            return None

        for key in ("name", "content_markdown"):
            if key in fields:
                protocol[key] = fields[key]
        return protocol

    def delete(self, protocol_id: int) -> None:
        if self._experiment_count_by_protocol.get(protocol_id, 0) > 0:
            raise ProtocolHasExperimentsError(
                "Protocol cannot be deleted while experiments reference it"
            )

        del self._protocols[protocol_id]

    def add_experiment(self, protocol_id: int) -> None:
        self._experiment_count_by_protocol[protocol_id] = (
            self._experiment_count_by_protocol.get(protocol_id, 0) + 1
        )


@pytest.fixture(name="repository")
def repository_fixture() -> InMemoryProtocolRepository:
    return InMemoryProtocolRepository()


@pytest.fixture(name="service")
def service_fixture(repository: InMemoryProtocolRepository) -> ProtocolService:
    return ProtocolService(repository)


class TestCreateProtocol:
    def test_creates_protocol_and_returns_its_data(
        self, service: ProtocolService
    ) -> None:
        # when
        protocol = service.create_protocol(
            name="Standard Workup", content_markdown="# Workup"
        )

        # then
        assert protocol["name"] == "Standard Workup"
        assert protocol["content_markdown"] == "# Workup"
        assert protocol["id"] > 0

    def test_creates_protocol_with_long_markdown(
        self, service: ProtocolService
    ) -> None:
        # given
        content = "## Step 1\n\nMix reagents and stir for 30 minutes."

        # when
        protocol = service.create_protocol(
            name="Multi-step Synthesis", content_markdown=content
        )

        # then
        assert protocol["content_markdown"] == content

    def test_rejects_blank_name(self, service: ProtocolService) -> None:
        # when / then
        with pytest.raises(ProtocolValidationError, match="name cannot be blank"):
            service.create_protocol(name="   ", content_markdown="# Content")

    def test_rejects_blank_content(self, service: ProtocolService) -> None:
        # when / then
        with pytest.raises(ProtocolValidationError, match="content cannot be blank"):
            service.create_protocol(name="Protocol", content_markdown="   ")

    def test_does_not_create_protocol_when_validation_fails(
        self, service: ProtocolService, repository: InMemoryProtocolRepository
    ) -> None:
        # given
        initial_count = len(repository.get_all())

        # when / then
        with pytest.raises(ProtocolValidationError):
            service.create_protocol(name="", content_markdown="# Content")

        assert len(repository.get_all()) == initial_count


class TestGetProtocol:
    def test_returns_protocol_for_existing_id(
        self, service: ProtocolService, repository: InMemoryProtocolRepository
    ) -> None:
        # given
        protocol_id = repository.create(name="Find me", content_markdown="# Find")

        # when
        protocol = service.get_protocol(protocol_id)

        # then
        assert protocol["name"] == "Find me"

    def test_raises_not_found_for_missing_id(self, service: ProtocolService) -> None:
        # when / then
        with pytest.raises(ProtocolNotFoundError, match="does not exist"):
            service.get_protocol(999)


class TestUpdateProtocol:
    def test_updates_name_and_content(
        self, service: ProtocolService, repository: InMemoryProtocolRepository
    ) -> None:
        # given
        protocol_id = repository.create(name="Original", content_markdown="# Old")

        # when
        protocol = service.update_protocol(
            protocol_id, name="Updated", content_markdown="# New"
        )

        # then
        assert protocol["name"] == "Updated"
        assert protocol["content_markdown"] == "# New"

    def test_rejects_blank_name(
        self, service: ProtocolService, repository: InMemoryProtocolRepository
    ) -> None:
        # given
        protocol_id = repository.create(name="Stable", content_markdown="# Stable")

        # when / then
        with pytest.raises(ProtocolValidationError, match="name cannot be blank"):
            service.update_protocol(protocol_id, name="")

    def test_rejects_blank_content(
        self, service: ProtocolService, repository: InMemoryProtocolRepository
    ) -> None:
        # given
        protocol_id = repository.create(name="Stable", content_markdown="# Stable")

        # when / then
        with pytest.raises(ProtocolValidationError, match="content cannot be blank"):
            service.update_protocol(protocol_id, content_markdown="")

    def test_raises_not_found_for_missing_id(self, service: ProtocolService) -> None:
        # when / then
        with pytest.raises(ProtocolNotFoundError, match="does not exist"):
            service.update_protocol(999, name="Anything")


class TestDeleteProtocol:
    def test_deletes_protocol_without_experiments(
        self, service: ProtocolService, repository: InMemoryProtocolRepository
    ) -> None:
        # given
        protocol_id = repository.create(name="Disposable", content_markdown="# Discard")

        # when
        service.delete_protocol(protocol_id)

        # then
        assert repository.get_by_id(protocol_id) is None

    def test_rejects_deletion_when_experiments_reference_protocol(
        self, service: ProtocolService, repository: InMemoryProtocolRepository
    ) -> None:
        # given
        protocol_id = repository.create(
            name="Protected", content_markdown="# Protected"
        )
        repository.add_experiment(protocol_id)

        # when / then
        with pytest.raises(ProtocolDeletionError, match="associated experiments"):
            service.delete_protocol(protocol_id)

    def test_does_not_delete_protocol_when_deletion_is_rejected(
        self, service: ProtocolService, repository: InMemoryProtocolRepository
    ) -> None:
        # given
        protocol_id = repository.create(name="Still Here", content_markdown="# Here")
        repository.add_experiment(protocol_id)

        # when / then
        with pytest.raises(ProtocolDeletionError):
            service.delete_protocol(protocol_id)

        assert repository.get_by_id(protocol_id) is not None

    def test_raises_not_found_for_missing_id(self, service: ProtocolService) -> None:
        # when / then
        with pytest.raises(ProtocolNotFoundError, match="does not exist"):
            service.delete_protocol(999)


class TestListProtocols:
    def test_returns_all_protocols(self, service: ProtocolService) -> None:
        # given
        service.create_protocol(name="Alpha", content_markdown="# Alpha")
        service.create_protocol(name="Beta", content_markdown="# Beta")

        # when
        protocols = service.list_protocols()

        # then
        assert len(protocols) == 2

    def test_returns_empty_list_when_no_protocols(
        self, service: ProtocolService
    ) -> None:
        # when
        protocols = service.list_protocols()

        # then
        assert protocols == []

    def test_filters_by_search_text_in_name(self, service: ProtocolService) -> None:
        # given
        service.create_protocol(
            name="Crystallisation", content_markdown="# Crystallisation"
        )
        service.create_protocol(name="Distillation", content_markdown="# Distillation")

        # when
        protocols = service.list_protocols({"search_text": "crystallisation"})

        # then
        assert len(protocols) == 1
        assert protocols[0]["name"] == "Crystallisation"

    def test_filters_by_search_text_in_content(self, service: ProtocolService) -> None:
        # given
        service.create_protocol(
            name="General",
            content_markdown="# Extraction\nUse diethyl ether.",
        )
        service.create_protocol(name="Other", content_markdown="# No match here")

        # when
        protocols = service.list_protocols({"search_text": "diethyl ether"})

        # then
        assert len(protocols) == 1
        assert protocols[0]["name"] == "General"

    def test_returns_all_protocols_when_filters_are_empty(
        self, service: ProtocolService
    ) -> None:
        # given
        service.create_protocol(name="Only Protocol", content_markdown="# Only")

        # when
        protocols = service.list_protocols({})

        # then
        assert len(protocols) == 1

    def test_returns_no_protocols_when_no_content_matches(
        self, service: ProtocolService
    ) -> None:
        # given
        service.create_protocol(name="Something", content_markdown="# Something")

        # when
        protocols = service.list_protocols({"search_text": "Nonexistent"})

        # then
        assert protocols == []
