from unittest.mock import patch
from urllib.error import URLError

import pytest

from app.services.ollama_client import (
    GENERATE_TIMEOUT_SECONDS,
    RECOMMENDED_MODEL,
    OllamaClient,
)


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_reports_unavailable_when_ollama_endpoint_cannot_be_reached() -> None:
    # given
    client = OllamaClient()

    # when
    with patch(
        "app.services.ollama_client.urlopen",
        side_effect=URLError("Connection refused"),
    ):
        status = client.get_status()

    # then
    assert status.is_available is False
    assert status.installed_models == ()
    assert status.is_recommended_model_ready is False


def test_reports_missing_recommended_model_when_ollama_has_other_models() -> None:
    # given
    client = OllamaClient()
    response = _Response(b'{"models": [{"name": "llama3.2:3b"}]}')

    # when
    with patch("app.services.ollama_client.urlopen", return_value=response):
        status = client.get_status()

    # then
    assert status.is_available is True
    assert status.installed_models == ("llama3.2:3b",)
    assert status.is_recommended_model_ready is False


def test_reports_ready_when_recommended_model_is_installed() -> None:
    # given
    client = OllamaClient()
    response = _Response(b'{"models": [{"name": "llama3.2:3b"}, {"name": "qwen3:4b"}]}')

    # when
    with patch("app.services.ollama_client.urlopen", return_value=response):
        status = client.get_status()

    # then
    assert status.is_available is True
    assert RECOMMENDED_MODEL in status.installed_models
    assert status.is_recommended_model_ready is True


def test_returns_completion_text_when_generate_succeeds() -> None:
    # given
    client = OllamaClient()
    response = _Response(b'{"response": "# Report"}')

    # when
    with patch(
        "app.services.ollama_client.urlopen", return_value=response
    ) as open_mock:
        text = client.generate(RECOMMENDED_MODEL, "Summarize.")

    # then
    assert text == "# Report"
    assert open_mock.called


def test_raises_when_generate_response_has_no_text() -> None:
    # given
    client = OllamaClient()
    response = _Response(b'{"response": "  "}')

    # when / then
    with patch("app.services.ollama_client.urlopen", return_value=response):
        with pytest.raises(ValueError, match="did not contain text"):
            client.generate(RECOMMENDED_MODEL, "Summarize.")


def test_reports_ready_with_any_installed_model() -> None:
    # given
    client = OllamaClient()
    response = _Response(b'{"models": [{"name": "gemma3:4b"}]}')

    # when
    with patch("app.services.ollama_client.urlopen", return_value=response):
        status = client.get_status()

    # then
    assert status.is_ready is True
    assert status.has_models is True


def test_reports_not_ready_without_installed_models() -> None:
    # given
    client = OllamaClient()
    response = _Response(b'{"models": []}')

    # when
    with patch("app.services.ollama_client.urlopen", return_value=response):
        status = client.get_status()

    # then
    assert status.is_available is True
    assert status.has_models is False
    assert status.is_ready is False


def test_returns_installed_models_when_server_lists_several() -> None:
    # given
    client = OllamaClient()
    response = _Response(b'{"models": [{"name": "qwen3:4b"}, {"name": "gemma3:4b"}]}')

    # when
    with patch("app.services.ollama_client.urlopen", return_value=response):
        installed = client.get_installed_models()

    # then
    assert installed == ("qwen3:4b", "gemma3:4b")


def test_returns_empty_installed_models_when_server_unreachable() -> None:
    # given
    client = OllamaClient()

    # when
    with patch(
        "app.services.ollama_client.urlopen",
        side_effect=URLError("Connection refused"),
    ):
        installed = client.get_installed_models()

    # then
    assert installed == ()


def test_returns_empty_installed_models_when_no_model_installed() -> None:
    # given
    client = OllamaClient()
    response = _Response(b'{"models": []}')

    # when
    with patch("app.services.ollama_client.urlopen", return_value=response):
        installed = client.get_installed_models()

    # then
    assert installed == ()


def test_uses_long_timeout_for_generation_instead_of_status_timeout() -> None:
    # given
    client = OllamaClient()
    response = _Response(b'{"response": "# Report"}')

    # when
    with patch(
        "app.services.ollama_client.urlopen", return_value=response
    ) as open_mock:
        client.generate(RECOMMENDED_MODEL, "Summarize.")

    # then
    assert open_mock.call_args.kwargs["timeout"] == GENERATE_TIMEOUT_SECONDS
    assert open_mock.call_args.kwargs["timeout"] > 60


def test_honours_custom_generate_timeout() -> None:
    # given
    client = OllamaClient(generate_timeout_seconds=45.0)
    response = _Response(b'{"response": "# Report"}')

    # when
    with patch(
        "app.services.ollama_client.urlopen", return_value=response
    ) as open_mock:
        client.generate(RECOMMENDED_MODEL, "Summarize.")

    # then
    assert open_mock.call_args.kwargs["timeout"] == 45.0
