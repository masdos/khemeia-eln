from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


def _build_system_prompt(language: str) -> str:
    """Return the system prompt requesting a full report in one language."""
    return (
        "You are a chemistry laboratory assistant. "
        f"Write the complete report in {language}. "
        "Write a structured technical scientific report in Markdown based only "
        "on the supplied experiments. "
        "Use exactly these sections: # Title, ## Summary, ## Objective, "
        "## Methods, ## Results, ## Discussion, ## Conclusions. "
        "Be concise, factual and neutral. "
        "Do not invent data that is not present in the experiments. "
        "When the source data uses another language, translate it faithfully "
        "without altering quantities, units or chemical names."
    )


class AIService:
    """Generates scientific report drafts with an explicit Ollama model."""

    def __init__(self, ollama_client: OllamaClient) -> None:
        self._ollama_client = ollama_client

    def generate_report(
        self,
        experiments_data: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        model: str,
        language: str,
    ) -> str | None:
        """Return a Markdown report draft, or None when AI is not ready.

        The model and the language are always chosen by the caller; the
        model must be installed at call time or no report is generated.
        """
        experiments = _normalize_experiments(experiments_data)
        if not experiments:
            logger.warning("Report generation skipped count=%s", 0)
            return None
        if not model or not model.strip():
            logger.warning("Report generation skipped without model")
            return None
        if not language or not language.strip():
            logger.warning("Report generation skipped without language")
            return None

        try:
            status = self._ollama_client.get_status()
        except Exception as error:
            logger.warning("AI provider unavailable error=%s", str(error))
            return None

        if not status.is_available:
            logger.warning("AI provider unavailable")
            return None
        if model not in status.installed_models:
            logger.warning(
                "AI model not installed model=%s installed=%s",
                model,
                status.installed_models,
            )
            return None

        prompt = _build_user_prompt(experiments)
        system_prompt = _build_system_prompt(language.strip())
        logger.info(
            "Generating report count=%s model=%s language=%s",
            len(experiments),
            model,
            language.strip(),
        )
        try:
            report = self._ollama_client.generate(model, system_prompt, prompt)
        except Exception as error:
            logger.warning("Report generation failed error=%s", str(error))
            return None

        if not report or not report.strip():
            logger.warning("Empty report received count=%s", len(experiments))
            return None

        logger.info(
            "Report generated count=%s model=%s language=%s",
            len(experiments),
            model,
            language.strip(),
        )
        return report.strip()


def _normalize_experiments(
    experiments_data: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    if isinstance(experiments_data, Mapping):
        return [experiments_data]
    return list(experiments_data)


def _build_user_prompt(experiments: Sequence[Mapping[str, Any]]) -> str:
    blocks = [
        _format_experiment(index, experiment)
        for index, experiment in enumerate(experiments, start=1)
    ]
    return "Experiments:\n\n" + "\n\n".join(blocks)


def _format_experiment(index: int, experiment: Mapping[str, Any]) -> str:
    title = experiment.get("title") or f"Experiment {index}"
    state = experiment.get("state") or "Unknown"
    question = experiment.get("question") or "Not recorded"
    procedure = experiment.get("experimental_procedure_markdown") or "Not recorded"
    result = experiment.get("result_markdown") or "Not recorded"
    conclusions = experiment.get("conclusions") or "Not recorded"
    return (
        f"Experiment {index}: {title}\n"
        f"State: {state}\n"
        f"Question: {question}\n"
        f"Procedure: {procedure}\n"
        f"Result: {result}\n"
        f"Conclusions: {conclusions}"
    )
