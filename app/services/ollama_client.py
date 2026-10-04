import logging
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

from ollama import Client as OllamaSdkClient

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
RECOMMENDED_MODEL = "qwen3.5:4b"
STATUS_TIMEOUT_SECONDS = 2.0
GENERATE_TIMEOUT_SECONDS = 1800.0
GENERATE_MAX_TOKENS = 2000
GENERATE_NUM_CTX = 8192
GENERATE_TEMPERATURE = 0.3
_CONTEXT_WARNING_RATIO = 0.9


def _generate_options() -> dict[str, int | float]:
    return {
        "num_ctx": GENERATE_NUM_CTX,
        "num_predict": GENERATE_MAX_TOKENS,
        "temperature": GENERATE_TEMPERATURE,
    }


def _log_token_usage(model: str, metrics: object) -> None:
    prompt_tokens = getattr(metrics, "prompt_eval_count", None)
    completion_tokens = getattr(metrics, "eval_count", None)
    logger.info(
        "Ollama usage model=%s prompt_tokens=%s completion_tokens=%s num_ctx=%s",
        model,
        prompt_tokens,
        completion_tokens,
        GENERATE_NUM_CTX,
    )
    if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
        used_tokens = prompt_tokens + completion_tokens
        if used_tokens >= GENERATE_NUM_CTX * _CONTEXT_WARNING_RATIO:
            logger.warning(
                "Context window nearly full model=%s used_tokens=%s num_ctx=%s",
                model,
                used_tokens,
                GENERATE_NUM_CTX,
            )


class IncompleteGenerationError(RuntimeError):
    """Raised when Ollama stops without completing the response."""


@dataclass(frozen=True)
class OllamaStatus:
    """Availability and installed-model state reported by Ollama."""

    is_available: bool
    installed_models: tuple[str, ...]

    @property
    def has_models(self) -> bool:
        """Return whether any local model is installed."""
        return len(self.installed_models) > 0

    @property
    def is_ready(self) -> bool:
        """Return whether Ollama can generate with a local model."""
        return self.is_available and self.has_models

    @property
    def is_recommended_model_ready(self) -> bool:
        """Return whether the recommended model is installed locally."""
        return RECOMMENDED_MODEL in self.installed_models


class OllamaClient:
    """Reads local Ollama state and generates completions via the Ollama SDK.

    Uses two SDK clients: a short-timeout one for status probes and a
    long-timeout one for generation, which can take minutes on local
    hardware. An SDK client factory can be injected for testing without
    HTTP.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        timeout_seconds: float = STATUS_TIMEOUT_SECONDS,
        generate_timeout_seconds: float = GENERATE_TIMEOUT_SECONDS,
        sdk_client_factory: Callable[[str, float], OllamaSdkClient] | None = None,
    ) -> None:
        factory = sdk_client_factory or (
            lambda host, timeout: OllamaSdkClient(host=host, timeout=timeout)
        )
        host = base_url.rstrip("/")
        self._status_client = factory(host, timeout_seconds)
        self._generate_client = factory(host, generate_timeout_seconds)

    def get_status(self) -> OllamaStatus:
        """Return the local Ollama availability and installed model names.

        Never raises: any failure means Ollama is not available.
        """
        try:
            models = self._status_client.list().models
        except Exception as error:
            logger.debug("Ollama status probe failed error=%s", str(error))
            return OllamaStatus(is_available=False, installed_models=())
        return OllamaStatus(
            is_available=True,
            installed_models=_model_names(models),
        )

    def generate_stream(
        self, model: str, system_prompt: str, user_prompt: str
    ) -> Iterator[str]:
        """Yield response text chunks as Ollama streams them.

        Generation can take many minutes on CPU-only hardware, so it uses
        a much longer timeout than the quick status probes. Output length
        is capped to bound the worst-case generation time. Thinking output
        stays disabled so the model returns only the final report.
        Raises IncompleteGenerationError when Ollama stops without
        completing the response.
        """
        stream = self._generate_client.generate(
            model=model,
            prompt=user_prompt,
            system=system_prompt,
            stream=True,
            think=False,
            options=_generate_options(),
        )
        done_reason = None
        last_chunk = None
        for chunk in stream:
            last_chunk = chunk
            done_reason = getattr(chunk, "done_reason", done_reason)
            text = getattr(chunk, "response", None)
            if isinstance(text, str) and text:
                yield text
        if last_chunk is not None:
            _log_token_usage(model, last_chunk)
        if done_reason != "stop":
            logger.warning(
                "Incomplete Ollama stream model=%s done_reason=%s",
                model,
                done_reason,
            )
            raise IncompleteGenerationError(
                f"Ollama stopped without completing the response (model={model})"
            )

    def get_installed_models(self) -> tuple[str, ...]:
        """Return names of installed local models, or empty when unknown.

        Readiness depends only on the server responding and at least one
        model being installed; memory-loaded state is never consulted.
        """
        return self.get_status().installed_models


def _model_names(models: object) -> tuple[str, ...]:
    if not isinstance(models, Sequence) or isinstance(models, (str, bytes)):
        return ()
    names = []
    for model in models:
        name = getattr(model, "model", None)
        if isinstance(name, str) and name:
            names.append(name)
    return tuple(names)
