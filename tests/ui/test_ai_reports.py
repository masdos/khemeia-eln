from app.services.ollama_client import OllamaStatus
from app.ui.pages.ai_reports import describe_status, get_readiness


class FakeOllamaClient:
    """Test double for OllamaClient without HTTP."""

    def __init__(
        self,
        status: OllamaStatus,
        status_error: Exception | None = None,
    ) -> None:
        self._status = status
        self._status_error = status_error
        self.status_calls = 0

    def get_status(self) -> OllamaStatus:
        self.status_calls += 1
        if self._status_error is not None:
            raise self._status_error
        return self._status


def test_accepts_any_installed_model_as_ready() -> None:
    # given
    readiness = get_readiness(
        FakeOllamaClient(status=OllamaStatus(True, ("qwen2.5:7b",)))  # type: ignore[arg-type]
    )

    # when
    state, message = describe_status(readiness)

    # then
    assert state == "ready"
    assert "All requirements are ready" in message


def test_accepts_several_installed_models_as_ready() -> None:
    # given
    readiness = get_readiness(
        FakeOllamaClient(status=OllamaStatus(True, ("qwen3:4b", "gemma3:4b")))  # type: ignore[arg-type]
    )

    # when
    state, message = describe_status(readiness)

    # then
    assert state == "ready"
    assert "2 local model(s)" in message


def test_describes_missing_ollama_with_short_message() -> None:
    # given
    readiness = get_readiness(
        FakeOllamaClient(status=OllamaStatus(False, ()))  # type: ignore[arg-type]
    )

    # when
    state, message = describe_status(readiness)

    # then — resources live in the hub requirements list, not here
    assert state == "missing_ollama"
    assert message == "Ollama is not installed or has not been started."


def test_describes_missing_model_with_short_message() -> None:
    # given
    readiness = get_readiness(
        FakeOllamaClient(status=OllamaStatus(True, ()))  # type: ignore[arg-type]
    )

    # when
    state, message = describe_status(readiness)

    # then
    assert state == "missing_model"
    assert message == "No local model detected."


def test_returns_unavailable_when_status_check_raises() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(False, ()),
        status_error=ConnectionError("refused"),
    )

    # when
    readiness = get_readiness(client)  # type: ignore[arg-type]

    # then
    assert readiness.is_available is False
    assert readiness.state == "missing_ollama"
