import json
import logging
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
RECOMMENDED_MODEL = "qwen3:4b"


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
    """Reads local Ollama state and generates completions without blocking the app."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        timeout_seconds: float = 2.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def get_status(self) -> OllamaStatus:
        """Return the local Ollama availability and installed model names."""
        request = Request(f"{self._base_url}/api/tags", method="GET")

        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (
            OSError,
            TimeoutError,
            URLError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return OllamaStatus(is_available=False, installed_models=())

        return OllamaStatus(
            is_available=True,
            installed_models=_model_names(payload),
        )

    def generate(self, model: str, prompt: str) -> str:
        """Generate a non-streaming completion with a local Ollama model."""
        body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(
            "utf-8"
        )
        request = Request(
            f"{self._base_url}/api/generate",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        with urlopen(request, timeout=self._timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        text = payload.get("response") if isinstance(payload, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Ollama response did not contain text")
        logger.debug("Ollama completion generated model=%s", model)
        return text

    def get_running_models(self) -> tuple[str, ...]:
        """Return names of models currently loaded, or empty when unknown."""
        request = Request(f"{self._base_url}/api/ps", method="GET")

        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (
            OSError,
            TimeoutError,
            URLError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return ()

        return _model_names(payload)


def _model_names(payload: object) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ()

    models = payload.get("models")
    if not isinstance(models, list):
        return ()

    return tuple(
        model["name"]
        for model in models
        if isinstance(model, dict) and isinstance(model.get("name"), str)
    )
