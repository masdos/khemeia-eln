import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ollama import Client as OllamaSdkClient

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
RECOMMENDED_MODEL = "qwen3.5:4b"
STATUS_TIMEOUT_SECONDS = 2.0
GENERATE_TIMEOUT_SECONDS = 1800.0
GENERATE_MAX_TOKENS = 2000


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

    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        """Generate a non-streaming completion with a local Ollama model.

        Generation can take many minutes on CPU-only hardware, so it uses
        a much longer timeout than the quick status probes. Output length
        is capped to bound the worst-case generation time. Thinking output
        stays disabled so the model returns only the final report.
        """
        response = self._generate_client.generate(
            model=model,
            prompt=user_prompt,
            system=system_prompt,
            stream=False,
            think=False,
            options={"num_predict": GENERATE_MAX_TOKENS},
        )
        done_reason = getattr(response, "done_reason", None)
        if done_reason != "stop":
            logger.warning(
                "Incomplete Ollama generation model=%s done_reason=%s",
                model,
                done_reason,
            )
            raise IncompleteGenerationError(
                f"Ollama stopped without completing the response (model={model})"
            )
        text = getattr(response, "response", None)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Ollama response did not contain text")
        logger.debug("Ollama completion generated model=%s", model)
        return text

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
