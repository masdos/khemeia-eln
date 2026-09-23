from types import SimpleNamespace
from typing import Any

import pytest

from app.services.ollama_client import (
    GENERATE_MAX_TOKENS,
    GENERATE_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
    RECOMMENDED_MODEL,
    STATUS_TIMEOUT_SECONDS,
    IncompleteGenerationError,
    OllamaClient,
)


class FakeSdkModel:
    """Test double for an SDK list entry exposing the model name."""

    def __init__(self, name: Any) -> None:
        self.model = name


class FakeSdkClient:
    """Test double for ollama.Client without HTTP."""

    def __init__(
        self,
        models: Any = None,
        response: Any = "",
        done_reason: Any = "stop",
        stream_chunks: list[str] | None = None,
    ) -> None:
        self._models = models
        self._response = response
        self._done_reason = done_reason
        self._stream_chunks = stream_chunks
        self.generate_calls: list[tuple[str, Any, Any]] = []
        self.generate_kwargs: list[dict[str, Any]] = []

    def list(self) -> Any:
        if isinstance(self._models, Exception):
            raise self._models
        return SimpleNamespace(models=self._models)

    def generate(
        self,
        model: str = "",
        prompt: Any = None,
        system: Any = None,
        **kwargs: Any,
    ) -> Any:
        self.generate_calls.append((model, system, prompt))
        self.generate_kwargs.append(kwargs)
        if isinstance(self._response, Exception):
            raise self._response
        if kwargs.get("stream") and self._stream_chunks is not None:
            return iter(
                [
                    SimpleNamespace(response=text, done_reason=None)
                    for text in self._stream_chunks[:-1]
                ]
                + [
                    SimpleNamespace(
                        response=(
                            self._stream_chunks[-1] if self._stream_chunks else ""
                        ),
                        done_reason=self._done_reason,
                    )
                ]
            )
        return SimpleNamespace(response=self._response, done_reason=self._done_reason)


class FakeSdkFactory:
    """Test double recording (host, timeout) pairs for both SDK clients."""

    def __init__(
        self, status_client: FakeSdkClient, generate_client: FakeSdkClient
    ) -> None:
        self.calls: list[tuple[str, float]] = []
        self._clients = [status_client, generate_client]

    def __call__(self, host: str, timeout: float) -> FakeSdkClient:
        self.calls.append((host, timeout))
        return self._clients[len(self.calls) - 1]


def _make_client(
    models: Any = None,
    response: Any = "",
    done_reason: Any = "stop",
    stream_chunks: list[str] | None = None,
    **kwargs: Any,
) -> tuple[OllamaClient, FakeSdkFactory, FakeSdkClient, FakeSdkClient]:
    status_client = FakeSdkClient(models=models)
    generate_client = FakeSdkClient(
        response=response, done_reason=done_reason, stream_chunks=stream_chunks
    )
    factory = FakeSdkFactory(status_client, generate_client)
    return (
        OllamaClient(sdk_client_factory=factory, **kwargs),
        factory,
        status_client,
        generate_client,
    )


def test_reports_unavailable_when_ollama_endpoint_cannot_be_reached() -> None:
    # given
    client, _, _, _ = _make_client(models=ConnectionError("Connection refused"))

    # when
    status = client.get_status()

    # then
    assert status.is_available is False
    assert status.installed_models == ()
    assert status.is_recommended_model_ready is False


def test_reports_missing_recommended_model_when_ollama_has_other_models() -> None:
    # given
    client, _, _, _ = _make_client(models=[FakeSdkModel("llama3.2:3b")])

    # when
    status = client.get_status()

    # then
    assert status.is_available is True
    assert status.installed_models == ("llama3.2:3b",)
    assert status.is_recommended_model_ready is False


def test_reports_ready_when_recommended_model_is_installed() -> None:
    # given
    client, _, _, _ = _make_client(
        models=[FakeSdkModel("llama3.2:3b"), FakeSdkModel("qwen3.5:4b")]
    )

    # when
    status = client.get_status()

    # then
    assert status.is_available is True
    assert RECOMMENDED_MODEL in status.installed_models
    assert status.is_recommended_model_ready is True


def test_returns_completion_text_when_generate_succeeds() -> None:
    # given
    client, _, _, generate_client = _make_client(response="# Report")

    # when
    text = client.generate(RECOMMENDED_MODEL, "Write a report.", "Summarize.")

    # then
    assert text == "# Report"
    assert generate_client.generate_calls == [
        (RECOMMENDED_MODEL, "Write a report.", "Summarize.")
    ]


def test_raises_when_generate_response_has_no_text() -> None:
    # given
    client, _, _, _ = _make_client(response="  ")

    # when / then
    with pytest.raises(ValueError, match="did not contain text"):
        client.generate(RECOMMENDED_MODEL, "Write a report.", "Summarize.")


def test_reports_ready_with_any_installed_model() -> None:
    # given
    client, _, _, _ = _make_client(models=[FakeSdkModel("gemma3:4b")])

    # when
    status = client.get_status()

    # then
    assert status.is_ready is True
    assert status.has_models is True


def test_reports_not_ready_without_installed_models() -> None:
    # given
    client, _, _, _ = _make_client(models=[])

    # when
    status = client.get_status()

    # then
    assert status.is_available is True
    assert status.has_models is False
    assert status.is_ready is False


def test_returns_installed_models_when_server_lists_several() -> None:
    # given
    client, _, _, _ = _make_client(
        models=[FakeSdkModel("qwen3:4b"), FakeSdkModel("gemma3:4b")]
    )

    # when
    installed = client.get_installed_models()

    # then
    assert installed == ("qwen3:4b", "gemma3:4b")


def test_returns_empty_installed_models_when_server_unreachable() -> None:
    # given
    client, _, _, _ = _make_client(models=ConnectionError("Connection refused"))

    # when
    installed = client.get_installed_models()

    # then
    assert installed == ()


def test_returns_empty_installed_models_when_no_model_installed() -> None:
    # given
    client, _, _, _ = _make_client(models=[])

    # when
    installed = client.get_installed_models()

    # then
    assert installed == ()


def test_uses_long_timeout_for_generation_instead_of_status_timeout() -> None:
    # given
    _, factory, _, _ = _make_client(response="# Report")

    # when / then
    assert factory.calls == [
        (OLLAMA_BASE_URL, STATUS_TIMEOUT_SECONDS),
        (OLLAMA_BASE_URL, GENERATE_TIMEOUT_SECONDS),
    ]
    assert factory.calls[1][1] > 60


def test_honours_custom_generate_timeout() -> None:
    # given
    _, factory, _, _ = _make_client(response="# Report", generate_timeout_seconds=45.0)

    # when / then
    assert factory.calls[1] == (OLLAMA_BASE_URL, 45.0)


def test_caps_generation_length_to_bound_slow_hardware_time() -> None:
    # given
    client, _, _, generate_client = _make_client(response="# Report")

    # when
    client.generate(RECOMMENDED_MODEL, "Write a report.", "Summarize.")

    # then
    assert generate_client.generate_kwargs[0]["options"] == {
        "num_predict": GENERATE_MAX_TOKENS
    }


def test_strips_trailing_slash_from_base_url() -> None:
    # given
    _, factory, _, _ = _make_client(base_url="http://example:11434/")

    # when / then
    assert [host for host, _ in factory.calls] == [
        "http://example:11434",
        "http://example:11434",
    ]


def test_ignores_list_entries_without_valid_names() -> None:
    # given
    client, _, _, _ = _make_client(
        models=[FakeSdkModel("qwen3:4b"), FakeSdkModel(None), FakeSdkModel("")]
    )

    # when
    status = client.get_status()

    # then
    assert status.installed_models == ("qwen3:4b",)


def test_reports_no_models_when_sdk_payload_has_no_model_list() -> None:
    # given
    client, _, _, _ = _make_client(models=None)

    # when
    status = client.get_status()

    # then
    assert status.is_available is True
    assert status.installed_models == ()


def test_returns_text_when_generation_completes_with_stop_reason() -> None:
    # given
    client, _, _, _ = _make_client(response="# Full report", done_reason="stop")

    # when
    text = client.generate(RECOMMENDED_MODEL, "Write in English.", "Experiments.")

    # then
    assert text == "# Full report"


def test_raises_incomplete_error_when_generation_stops_early() -> None:
    # given
    client, _, _, _ = _make_client(response="# Partial", done_reason="length")

    # when / then
    with pytest.raises(IncompleteGenerationError):
        client.generate(RECOMMENDED_MODEL, "Write in English.", "Experiments.")


def test_sends_system_prompt_without_manual_concatenation() -> None:
    # given
    client, _, _, generate_client = _make_client(response="# Report")

    # when
    client.generate(RECOMMENDED_MODEL, "System instructions.", "User data.")

    # then
    assert generate_client.generate_calls == [
        (RECOMMENDED_MODEL, "System instructions.", "User data.")
    ]
    assert generate_client.generate_kwargs[0]["think"] is False
    assert generate_client.generate_kwargs[0]["stream"] is False


def test_uses_updated_recommended_model() -> None:
    # given / when / then
    assert RECOMMENDED_MODEL == "qwen3.5:4b"


def test_streams_response_chunks_in_order() -> None:
    # given
    client, _, _, generate_client = _make_client(stream_chunks=["# Re", "port"])

    # when
    chunks = list(client.generate_stream(RECOMMENDED_MODEL, "System.", "Data."))

    # then
    assert chunks == ["# Re", "port"]
    assert generate_client.generate_calls == [(RECOMMENDED_MODEL, "System.", "Data.")]
    assert generate_client.generate_kwargs[0]["stream"] is True
    assert generate_client.generate_kwargs[0]["think"] is False
    assert generate_client.generate_kwargs[0]["options"] == {
        "num_predict": GENERATE_MAX_TOKENS
    }


def test_raises_incomplete_error_when_stream_stops_early() -> None:
    # given
    client, _, _, _ = _make_client(stream_chunks=["# Partial"], done_reason="length")

    # when / then
    with pytest.raises(IncompleteGenerationError):
        list(client.generate_stream(RECOMMENDED_MODEL, "System.", "Data."))
