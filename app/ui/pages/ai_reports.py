from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

OLLAMA_DOWNLOAD_URL = "https://ollama.com/download"
QWEN_PULL_COMMAND = "ollama pull qwen3"
SERVE_COMMAND = "ollama serve"

READY = "ready"
MISSING_OLLAMA = "missing_ollama"
MISSING_MODEL = "missing_model"


@dataclass(frozen=True)
class Readiness:
    """Ollama availability with installed local models."""

    is_available: bool
    installed_models: tuple[str, ...] = ()

    @property
    def state(self) -> str:
        """Return ready, missing_ollama or missing_model."""
        if not self.is_available:
            return MISSING_OLLAMA
        if not self.installed_models:
            return MISSING_MODEL
        return READY


def get_readiness(client: OllamaClient | None = None) -> Readiness:
    """Return Ollama readiness without raising when the endpoint fails."""
    ollama = client or OllamaClient()
    try:
        status = ollama.get_status()
    except Exception as error:
        logger.warning("AI readiness check failed error=%s", str(error))
        return Readiness(is_available=False)
    if not status.is_available:
        return Readiness(is_available=False)
    if not status.has_models:
        return Readiness(is_available=True)
    return Readiness(
        is_available=True,
        installed_models=status.installed_models,
    )


def describe_status(readiness: Readiness) -> tuple[str, str]:
    """Return state and user-facing message for a readiness.

    Messages stay short: download links and commands live in the
    AI Assistant requirements list, not in the status indicator.
    """
    if readiness.state == MISSING_OLLAMA:
        return MISSING_OLLAMA, "Ollama is not installed or has not been started."
    if readiness.state == MISSING_MODEL:
        return MISSING_MODEL, "No local model detected."
    count = len(readiness.installed_models)
    return READY, f"All requirements are ready ({count} local model(s))."
