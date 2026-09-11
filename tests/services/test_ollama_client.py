from unittest.mock import patch
from urllib.error import URLError

from app.services.ollama_client import RECOMMENDED_MODEL, OllamaClient


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
    response = _Response(
        b'{"models": [{"name": "llama3.2:3b"}, {"name": "qwen3:4b"}]}'
    )

    # when
    with patch("app.services.ollama_client.urlopen", return_value=response):
        status = client.get_status()

    # then
    assert status.is_available is True
    assert RECOMMENDED_MODEL in status.installed_models
    assert status.is_recommended_model_ready is True
