from typing import Any
from urllib.error import URLError

from app.services.ai_service import (
    AIService,
    _build_system_prompt,
    _sanitize_report,
)
from app.services.ollama_client import (
    IncompleteGenerationError,
    OllamaClient,
    OllamaStatus,
)


class FakeOllamaClient:
    """Test double for OllamaClient without HTTP or SQLite."""

    def __init__(
        self,
        status: OllamaStatus,
        response: str = "# Draft",
        status_error: Exception | None = None,
        generate_error: Exception | None = None,
    ) -> None:
        self._status = status
        self._response = response
        self._status_error = status_error
        self._generate_error = generate_error
        self.seen_models: list[str] = []
        self.seen_system: list[str] = []
        self.seen_prompts: list[str] = []

    def get_status(self) -> OllamaStatus:
        if self._status_error is not None:
            raise self._status_error
        return self._status

    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        self.seen_models.append(model)
        self.seen_system.append(system_prompt)
        self.seen_prompts.append(user_prompt)
        if self._generate_error is not None:
            raise self._generate_error
        return self._response


def _ready_status(*models: str) -> OllamaStatus:
    return OllamaStatus(is_available=True, installed_models=models)


def _experiment(title: str = "Synthesis of Aspirin") -> dict[str, Any]:
    return {
        "title": title,
        "state": "Success",
        "question": "Can yield exceed 80%?",
        "experimental_procedure_markdown": "Mix and heat.",
        "result_markdown": "Yield 85%.",
        "conclusions": "Route is viable.",
    }


def test_returns_markdown_draft_for_given_model() -> None:
    # given
    client: OllamaClient = FakeOllamaClient(
        status=_ready_status("qwen3:4b"), response="# Report\n\nContent."
    )  # type: ignore[assignment]
    service = AIService(client)

    # when
    report = service.generate_report(_experiment(), "qwen3:4b", "English")

    # then
    assert report == "# Report\n\nContent."
    assert client.seen_models == ["qwen3:4b"]


def test_sends_experiment_content_in_prompt() -> None:
    # given
    client = FakeOllamaClient(status=_ready_status("gemma3:4b"), response="# Draft")
    service = AIService(client)  # type: ignore[arg-type]

    # when
    service.generate_report(_experiment(title="Aspirin"), "gemma3:4b", "English")

    # then
    assert client.seen_models == ["gemma3:4b"]
    assert "Aspirin" in client.seen_prompts[0]


def test_combines_several_experiments_into_one_prompt() -> None:
    # given
    client = FakeOllamaClient(status=_ready_status("qwen3:4b"), response="# Combined")
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(
        [_experiment("Alpha"), _experiment("Beta")], "qwen3:4b", "English"
    )

    # then
    assert report == "# Combined"
    assert "Alpha" in client.seen_prompts[0]
    assert "Beta" in client.seen_prompts[0]


def test_returns_none_when_ollama_is_unavailable() -> None:
    # given
    client = FakeOllamaClient(
        status=OllamaStatus(is_available=False, installed_models=())
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment(), "qwen3:4b", "English")

    # then
    assert report is None
    assert client.seen_prompts == []


def test_returns_none_when_given_model_is_not_installed() -> None:
    # given
    client = FakeOllamaClient(status=_ready_status("gemma3:4b"), response="# Draft")
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment(), "qwen3:4b", "English")

    # then
    assert report is None
    assert client.seen_prompts == []


def test_returns_none_when_no_model_is_given() -> None:
    # given
    client = FakeOllamaClient(status=_ready_status("qwen3:4b"), response="# Draft")
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment(), "  ", "English")

    # then
    assert report is None
    assert client.seen_prompts == []


def test_returns_none_when_generation_raises() -> None:
    # given
    client = FakeOllamaClient(
        status=_ready_status("qwen3:4b"),
        generate_error=URLError("Connection refused"),
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment(), "qwen3:4b", "English")

    # then
    assert report is None


def test_returns_none_when_status_check_raises() -> None:
    # given
    client = FakeOllamaClient(
        status=_ready_status("qwen3:4b"),
        status_error=URLError("Connection refused"),
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment(), "qwen3:4b", "English")

    # then
    assert report is None


def test_requests_report_in_given_language() -> None:
    # given
    client = FakeOllamaClient(status=_ready_status("qwen3:4b"), response="# Draft")
    service = AIService(client)  # type: ignore[arg-type]

    # when
    service.generate_report(_experiment(), "qwen3:4b", "Spanish")

    # then
    assert "Spanish" in client.seen_system[0]


def test_requests_report_in_english_when_chosen() -> None:
    # given
    client = FakeOllamaClient(status=_ready_status("qwen3:4b"), response="# Draft")
    service = AIService(client)  # type: ignore[arg-type]

    # when
    service.generate_report(_experiment(), "qwen3:4b", "English")

    # then
    assert "English" in client.seen_system[0]


def test_returns_none_when_language_is_missing() -> None:
    # given
    client = FakeOllamaClient(status=_ready_status("qwen3:4b"), response="# Draft")
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment(), "qwen3:4b", "  ")

    # then
    assert report is None
    assert client.seen_prompts == []


def test_returns_none_when_generation_is_incomplete() -> None:
    # given
    client = FakeOllamaClient(
        status=_ready_status("qwen3:4b"),
        generate_error=IncompleteGenerationError("truncated"),
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment(), "qwen3:4b", "English")

    # then
    assert report is None


def test_builds_system_prompt_with_requested_language() -> None:
    # given
    language = "Spanish"

    # when
    prompt = _build_system_prompt(language)

    # then
    assert language in prompt
    assert "translate" in prompt.lower()
    assert "quantities" in prompt.lower()


def test_requires_standard_markdown_with_plain_formulas() -> None:
    # given
    language = "English"

    # when
    prompt = _build_system_prompt(language)

    # then
    assert "standard Markdown" in prompt
    assert "H2SO4" in prompt
    assert "LaTeX" in prompt
    assert "<sub>" in prompt


def test_flattens_latex_formula_to_plain_text() -> None:
    # given
    raw = r"$\text{H}_2\text{SO}_4$"

    # when
    cleaned = _sanitize_report(raw)

    # then
    assert cleaned == "H2SO4"


def test_flattens_html_subscript_to_plain_text() -> None:
    # given
    raw = "H<sub>2</sub>SO<sub>4</sub>"

    # when
    cleaned = _sanitize_report(raw)

    # then
    assert cleaned == "H2SO4"


def test_flattens_unicode_subscripts_to_plain_text() -> None:
    # given
    raw = "H₂SO₄"

    # when
    cleaned = _sanitize_report(raw)

    # then
    assert cleaned == "H2SO4"


def test_flattens_braced_subscripts_to_plain_text() -> None:
    # given
    raw = "CO_{2} and H_{2}O"

    # when
    cleaned = _sanitize_report(raw)

    # then
    assert cleaned == "CO2 and H2O"


def test_sanitizes_generated_draft_before_returning() -> None:
    # given
    client = FakeOllamaClient(
        status=_ready_status("qwen3:4b"),
        response=r"# Report with $\text{H}_2\text{SO}_4$",
    )
    service = AIService(client)  # type: ignore[arg-type]

    # when
    report = service.generate_report(_experiment(), "qwen3:4b", "English")

    # then
    assert report == "# Report with H2SO4"


def test_preserves_italic_markup_when_sanitizing() -> None:
    # given
    raw = "_No result recorded._ with H2SO4"

    # when
    cleaned = _sanitize_report(raw)

    # then
    assert cleaned == raw
