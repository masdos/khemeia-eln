from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

_SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")


def _build_system_prompt(language: str) -> str:
    """Return the system prompt requesting a full report in one language."""
    return (
        "You are a chemistry laboratory assistant. "
        f"Write the complete report in {language}. "
        "Write a structured technical scientific report in Markdown based only "
        "on the supplied experiments. "
        "Use exactly these sections: # Title, ## Summary, ## Objective, "
        "## Methods, ## Results, ## Conclusions. "
        "Use only standard Markdown (headings, bold, italic, lists, tables). "
        "Do not use LaTeX, math delimiters like $...$, backslash commands, "
        "HTML tags such as <sub> or <sup>, or Unicode sub/superscripts. "
        "Write chemical formulas in plain text with inline numbers, "
        "for example H2SO4, CO2 or H2O. "
        "Be concise, factual and neutral. "
        "Do not invent data that is not present in the experiments. "
        "When the source data uses another language, translate it faithfully "
        "without altering quantities, units or chemical names."
    )


def _sanitize_report(text: str) -> str:
    """Convert formulas to plain text with inline numbers.

    The Markdown preview and the PDF export only support standard
    Markdown, so LaTeX ($...$, \\text{...}), HTML (<sub>) and Unicode
    sub/superscripts are flattened, e.g. H2SO4 stays H2SO4.
    """
    cleaned = re.sub(r"</?(?:sub|sup|super)[^>]*>", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\\(?:text|mathrm|ce|ch)\{([^}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"[_^]\{([^}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"_([0-9]+)", r"\1", cleaned)
    cleaned = re.sub(r"\^([0-9+\-]+)", r"\1", cleaned)
    cleaned = cleaned.translate(_SUBSCRIPTS).translate(_SUPERSCRIPTS)
    cleaned = cleaned.replace("$", "")
    return cleaned


class AIService:
    """Generates scientific report drafts with an explicit Ollama model."""

    def __init__(self, ollama_client: OllamaClient) -> None:
        self._ollama_client = ollama_client

    def generate_report(
        self,
        experiments_data: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        model: str,
        language: str,
        on_progress: Callable[[str], None] | None = None,
    ) -> str | None:
        """Return a Markdown report draft, or None when AI is not ready.

        The model and the language are always chosen by the caller; the
        model must be installed at call time or no report is generated.
        When on_progress is given, generation streams and the callback
        receives the accumulated text after each chunk.
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
            if on_progress is None:
                report = self._ollama_client.generate(model, system_prompt, prompt)
            else:
                parts: list[str] = []
                for chunk in self._ollama_client.generate_stream(
                    model, system_prompt, prompt
                ):
                    parts.append(chunk)
                    on_progress("".join(parts))
                report = "".join(parts)
        except Exception as error:
            logger.warning("Report generation failed error=%s", str(error))
            return None

        if not report or not report.strip():
            logger.warning("Empty report received count=%s", len(experiments))
            return None

        cleaned = _sanitize_report(report.strip())
        if not cleaned.strip():
            logger.warning("Empty report received count=%s", len(experiments))
            return None

        logger.info(
            "Report generated count=%s model=%s language=%s",
            len(experiments),
            model,
            language.strip(),
        )
        return cleaned.strip()


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
