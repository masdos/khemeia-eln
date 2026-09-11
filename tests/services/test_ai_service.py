from typing import Any
from urllib.error import URLError

from app.services.ai_service import AIService
from app.services.ollama_client import (
    RECOMMENDED_MODEL,
    OllamaClient,
    OllamaStatus,
)


class FakeOllamaClient:
    """Test double for OllamaClient without HTTP or SQLite."""

    def __init__(
        self,
        status: OllamaStatus,
        response: str = "# Draft",
        status_error: Exception | None = None,
        generate_error: Exception | None = None,
    ) -> None:
        self._status = status
        self._response = response
        self._status_error = status_error
        self._generate_error = generate_error
        self.seen_models: list[str] = []
        self.seen_prompts: list[str] = []

    def get_status(self) -> OllamaStatus:
        if self._status_error is not None:
            raise self._status_error
        return self._status

    def generate(self, model: str, prompt: str) -> str:
        self.seen_models.append(model)
        self.seen_prompts.append(prompt)
        if self._generate_error is not None:
            raise self._generate_error
        return self._response


def _ready_status() -> OllamaStatus:
    return OllamaStatus(is_available=True, installed_models=(RECOMMENDED_MODEL,))


def _experiment(title: str = "Synthesis of Aspirin") -> dict[str, Any]:
    return {
        "title": title,
        "state": "Success",
        "question": "Can yield exceed 80%?",
        "experimental_procedure_markdown": "Mix and heat.",
        "result_markdown": "Yield 85%.",
        "conclusions": "Route is viable.",
    }


def test_returns_markdown_draft_for_single_experiment() -> None:
    # given
    client: OllamaClient = FakeOllamaClient(
        status=_ready_status(), response="# Report\n\nContent."
    )  # type: ignore[assignment]
    service = AIService(client)

    # when
    report = service.generate_report(_experiment())

    # then
    assert report == "# Report\n\nContent."


def test_sends_recommended_model_and_experiment_content() -> None:
    # given
    client = FakeOllamaClient(status=_ready_status(), response="# Draft")
    service = AIService(client)  # type: ignore[arg-type]

    # when
    service.generate_report(_experiment(title="Aspirin"))

    # then
    assert client.seen_models == [RECOMMENDED_MODEL]
    assert "Aspirin" in client.seen_prompts[0]


def test_combines_several_experiments_into_one_prompt() -> None:
    # given
    client = FakeOllamaClient(status=_ready_status(), response="# Combined")
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report([_experiment("Alpha"), _experiment("Beta")])

    # then
    assert report == "# Combined"
    assert "Alpha" in client.seen_prompts[0]
    assert "Beta" in client.seen_prompts[0]


def test_returns_none_when_ollama_is_unavailable() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(is_available=False, installed_models=())
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment())

    # then
    assert report is None
    assert client.seen_prompts == []


def test_uses_any_installed_model_when_preferred_is_missing() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(is_available=True, installed_models=("gemma3:4b",)),
        response="# Draft",
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment())

    # then
    assert report == "# Draft"
    assert client.seen_models == ["gemma3:4b"]


def test_returns_none_when_no_model_is_installed() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(is_available=True, installed_models=())
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment())

    # then
    assert report is None
    assert client.seen_prompts == []


def test_returns_none_when_generation_raises() -> None:
    # given
    client = FakeOllamaClient(
        status=_ready_status(),
        generate_error=URLError("Connection refused"),
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment())

    # then
    assert report is None


def test_returns_none_when_status_check_raises() -> None:
    # given
    client = FakeOllamaClient(
        status=_ready_status(),
        status_error=URLError("Connection refused"),
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment())

    # then
    assert report is None
