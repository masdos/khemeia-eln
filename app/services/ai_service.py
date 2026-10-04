from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

_SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")

_ROLE = (
    "You are a chemistry laboratory assistant inside an electronic lab "
    "notebook. Write a DRAFT technical scientific report in Markdown from "
    "the experiment records in the user message. A chemist will review and "
    "edit the draft, so accuracy matters more than polish."
)

_REPORT_RULES = """\
RECORDS FORMAT
Each experiment has these labeled fields: Title, State, Research question,
Protocol name, Experimental procedure, Results, Conclusions,
Reagents, Equipment, Attachments. Only the protocol name is sent, not its
content. An empty field is marked NOT RECORDED.

TRUTH RULES (highest priority)
1. Use only facts that appear in the records. Do not invent data.
2. If a value is missing, write "Not recorded" in the report language. Never
   estimate or invent numbers, dates, observations, yields, melting points,
   Rf values or literature values.
3. Do not calculate. Report only numbers that already appear in the records.
4. Do not cite literature and do not invent references. Never cite Wikipedia.
5. Describe what actually happened. The protocol name is context only: the
   experimental procedure is the correct account of the work. Include
   deviations and failures. Do not idealize.
6. Keep every quantity, unit and chemical name exactly as recorded. Do not
   round or convert. When the records use another language, translate them
   faithfully without altering quantities, units or chemical names.
7. Yields, melting points, Rf values and similar data exist only if they are
   written in the Results field. Copy each value with its unit and the
   compound it belongs to. If it is unclear which compound a value belongs
   to, reproduce the original sentence instead of assigning it.
8. The State decides the outcome:
   - Success: say the experiment worked only if Results or Conclusions
     support it.
   - Fail: say clearly that the experiment failed. Give causes only if the
     records mention them.
   - Running: the experiment is not finished. Write only the title, Summary,
     Objective and Methods. Under Results, Discussion and Conclusions write
     only "Pending: experiment still running." in the report language.

FORMAT RULES
- Use only standard Markdown (headings, bold, italic, lists, tables).
- Do not use LaTeX, math delimiters like $...$, backslash commands, HTML tags
  such as <sub> or <sup>, or Unicode sub/superscripts. If the records contain
  LaTeX, rewrite it in plain text.
- Write chemical formulas in plain text with inline numbers, for example
  H2SO4, CO2 or H2O.
- Be concise, factual and neutral.
- Use third person and passive voice for all actions. Do not use "I" or "we".
  Reagents and compounds are the only actors.
- Use short sentences and precise terms. Avoid vague verbs such as "reacts
  with" when a precise verb exists.
- State how reagents were added when the records say so (dropwise, in
  portions).
- Mention the hazards listed in the records as safety precautions in Methods.
- Every table and figure must be mentioned in the text by its number.
- Write the section headings in the report language.

STRUCTURE
Start with the report title as a level-1 heading: short, and naming the
experiment performed. Then write exactly these sections as level-2 headings,
in this order, and no others (no References section):
- Summary: one paragraph of 3 to 4 full sentences with the purpose, the
  method and the key recorded results.
- Objective: state the purpose using the Research question and explain why it
  matters. Use only background found in the records. Include chemical
  equations only if they appear in the records: copy them in plain text, do
  not create or balance them.
- Methods: built from the Experimental procedure, using the protocol only as
  context, and from the Reagents and Equipment lists. Give enough detail for
  another chemist to repeat the work, including reagent amounts. Record color,
  texture and physical state when present. Leave out trivial details.
- Results: present only the content of the Results field. No analysis and no
  opinion on quality. Build a table only if the field gives values for clearly
  labeled compounds: caption ABOVE the table, units in every column header.
  Otherwise describe the data in prose. Figure captions go BELOW the figure.
  Mention a figure only if it is in the Attachments list. Never invent
  figures.
- Discussion: continuous prose that tells a logical story. Never use bullet
  points or numbered lists here. Analyze the recorded results and the
  chemist's Conclusions. Compare with literature values only if they appear
  in the records. Discuss sources of error only if the records support them.
  Suggest concrete improvements. Do not add new calculations.
- Conclusions: one paragraph. Base it on the Conclusions field and do not
  contradict it. If it is NOT RECORDED, summarize only what the Results and
  the State support. Say whether the Research question was answered,
  according to the State.

SEVERAL EXPERIMENTS
Give each experiment its own subsection in Methods. Use one table in Results
with one row per experiment. Compare the experiments in the Discussion.

OUTPUT
Return only the report. No introduction, no closing remarks, no notes about
your reasoning.
"""


def _build_system_prompt(language: str) -> str:
    """Return the system prompt requesting a full report in one language."""
    return f"{_ROLE}\nWrite the complete report in {language}.\n\n{_REPORT_RULES}"


def _sanitize_report(text: str) -> str:
    """Convert formulas to plain text with inline numbers.

    The Markdown preview and the PDF export only support standard
    Markdown, so LaTeX ($...$, \\text{...}), HTML (<sub>) and Unicode
    sub/superscripts are flattened, e.g. H2SO4 stays H2SO4.
    """
    cleaned = re.sub(r"</?(?:sub|sup|super)[^>]*>", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\\(?:text|mathrm|ce|ch)\{([^}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"_\{([^}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"\^\{([^}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"(?<=[A-Za-z)])_(\d+)", r"\1", cleaned)
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
    protocol_name = experiment.get("protocol_name") or "Not recorded"
    procedure = experiment.get("experimental_procedure_markdown") or "Not recorded"
    result = experiment.get("result_markdown") or "Not recorded"
    conclusions = experiment.get("conclusions") or "Not recorded"
    return (
        f"Experiment {index}: {title}\n"
        f"State: {state}\n"
        f"Question: {question}\n"
        f"Protocol name: {protocol_name}\n"
        f"Procedure: {procedure}\n"
        f"Result: {result}\n"
        f"Conclusions: {conclusions}\n"
        f"Reagents: {_format_reagents(experiment.get('reagents'))}\n"
        f"Equipment: {_format_equipment(experiment.get('equipment'))}\n"
        f"Attachments: {_format_attachments(experiment.get('attachments'))}"
    )


def _format_reagents(reagents: Any) -> str:
    """Format linked reagents with amount, lot and hazards for the prompt."""
    if not reagents:
        return "Not recorded"
    parts = []
    for reagent in reagents:
        name = reagent.get("name") or "Unnamed reagent"
        details: list[str] = []
        if reagent.get("amount_used") is not None:
            amount = f"{reagent['amount_used']} {reagent.get('unit') or ''}".strip()
            details.append(amount)
        if reagent.get("lot_number"):
            details.append(f"Lot: {reagent['lot_number']}")
        hazards = reagent.get("hazards") or []
        if hazards:
            details.append(f"Hazards: {', '.join(hazards)}")
        parts.append(f"{name} ({', '.join(details)})" if details else name)
    return "; ".join(parts)


def _format_equipment(equipment: Any) -> str:
    """Format linked equipment with descriptions for the prompt."""
    if not equipment:
        return "Not recorded"
    parts = []
    for item in equipment:
        name = item.get("name") or "Unnamed equipment"
        description = (item.get("description") or "").strip()
        parts.append(f"{name} ({description})" if description else name)
    return "; ".join(parts)


def _format_attachments(attachments: Any) -> str:
    """Format attachment file name, extension and description for the prompt."""
    if not attachments:
        return "Not recorded"
    parts = []
    for attachment in attachments:
        if isinstance(attachment, Mapping):
            file_name = str(attachment.get("file_name") or "").strip()
            if not file_name:
                continue
            extension = str(attachment.get("extension") or "").strip()
            description = str(attachment.get("description") or "").strip()
            label = file_name
            if extension:
                label += f" [{extension}]"
            label += f" - {description}" if description else " - No description"
            parts.append(label)
        else:
            name = str(attachment).strip()
            if name:
                parts.append(name)
    return "; ".join(parts) if parts else "Not recorded"
