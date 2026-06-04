# Python Project Rules

## Project Context

This is **Khemeia ELN**, a local-first laboratory management system for chemistry researchers.
Stack: Python 3.12+, NiceGUI, SQLite, RDKit, LM Studio.

Key project dependencies (install with `uv add`):
- `nicegui` — desktop UI framework (requires `pywebview` for `native=True` mode)
- `rdkit` — cheminformatics; install via `uv add rdkit`. If unavailable on PyPI for the target platform, use the `rdkit-pypi` package or a conda-forge channel.
- `rocrate` — RO-Crate packaging for `.eln` export
- `python-dotenv` — `.env` loading for developer overrides

> **RDKit note:** On some platforms RDKit is not available on PyPI. If `uv add rdkit` fails, try `uv add rdkit-pypi`. All code that imports RDKit must degrade gracefully when the package is absent (return `None`, do not raise).

## Python Version

This project requires **Python 3.12 or higher**. Set this in `pyproject.toml`:

```toml
[project]
requires-python = ">=3.12"
```

## Package Management

This project uses `uv`. Do not use pip, pip-tools, poetry, or conda.

- Add runtime dependency: `uv add <package>` (writes to `[project.dependencies]`)
- Add dev dependency: `uv add --dev <package>` (writes to `[dependency-groups]` per PEP 735)
- Remove dependency: `uv remove <package>`
- Sync environment from lockfile: `uv sync`
- Regenerate lockfile from constraints: `uv lock`
- Upgrade locked versions: `uv lock --upgrade`
- Commit `uv.lock` to version control

## Running Code

Always use `uv run` to execute Python code and tools. Never call `python`, `pytest`, `ruff`, or other tools directly.

- Run a script: `uv run python script.py`
- Run a module: `uv run python -m module_name`
- Run a tool: `uv run pytest`, `uv run ruff check .`
- One-off tool (not a project dependency): `uvx <tool>`

## Creating New Projects

- Application or script: `uv init project-name`
- Always use `pyproject.toml` for metadata (PEP 621). Never create `setup.py`, `setup.cfg`, or `requirements.txt`.

## Testing

- Framework: pytest
- Run tests: `uv run pytest`
- Test files go in `tests/` at the project root
- Test file naming: `test_*.py`
- Test function naming: `test_*`
- No `__init__.py` needed in `tests/`
- Repository tests use SQLite `:memory:` with the real schema applied on setup
- Service tests use in-memory repository stubs — no SQLite, no filesystem

## Linting and Formatting

- Tool: ruff (handles both linting and formatting)
- Lint: `uv run ruff check .`
- Lint and auto-fix: `uv run ruff check --fix .`
- Format: `uv run ruff format .`
- Check formatting: `uv run ruff format --check .`
- Configuration lives in `pyproject.toml` under `[tool.ruff]`

## Type Checking

- Tool: **ty** (this project uses ty exclusively — do not use pyrefly or mypy)
- Run: `uv run ty check`
- Configuration lives in `pyproject.toml` under `[tool.ty]`

## Code Style

- Follow ruff's defaults for formatting (88 char line length, double quotes, spaces)
- Import sorting is handled by ruff (`isort` rules enabled via `select = ["I"]`)
- Do not add `# type: ignore` comments without an error code

## Pre-commit Hooks

- Tool: prek
- Install: `uvx prek install`
- Do not install prek with pip. Use `uvx`.

## What NOT to Do

- Do not create or activate virtual environments manually. uv manages `.venv/` automatically.
- Do not install packages globally or with `pip install`.
- Do not create `requirements.txt` for dependency management. Use `pyproject.toml` and `uv.lock`.
- Do not run `python setup.py` commands.
- Do not add dependencies to `pyproject.toml` by hand. Use `uv add`.
- If you must edit `pyproject.toml` directly, write dev dependencies under `[dependency-groups]` (PEP 735), not the legacy `[tool.uv.dev-dependencies]` table.

---

## Configuration: config.json vs .env

The application uses **two separate configuration mechanisms** with distinct responsibilities.

### config.json — User profile (primary configuration)

Written and managed by the application itself when the user fills in the welcome form.
Location: project root (`config.json`).

```json
{
  "user_name": "Ada Lovelace",
  "user_email": "ada@lab.edu",
  "base_dir": "/home/ada/khemeia",
  "ai_provider": "lmstudio"
}
```

- `base_dir` is the root for all local data (`data/database.db`, `data/attachments/`, `data/exports/`).
- `ai_provider` selects the active AI backend: `lmstudio`, `ollama`, or `remote`.
- `user_name` and `user_email` are available globally for auditing without being passed as parameters.
- If `config.json` is missing or has missing required fields, the UI shows a blocking welcome form before loading the rest of the app.
- `config.json` must **not** be committed to version control (add to `.gitignore`).

### .env — Developer overrides (optional)

Used only by developers to override specific values without modifying `config.json`.
Loaded via `python-dotenv`. Takes precedence over `config.json` when a key is present in both.

Typical uses: custom endpoint ports, alternative `base_dir` for local testing, log level.

```dotenv
# Example .env — never commit this file
AI_ENDPOINT=http://localhost:5000/v1
LOG_LEVEL=DEBUG
```

- `.env` must **never** be committed to version control.
- Do not store secrets (API keys, passwords) in `config.json`. Use `.env` for those.
- `src/config.py` is the single module responsible for reading both sources and exposing a unified config object to the rest of the application.

## Critical Operational Rules

1. **NEVER** use bare system commands like `pip install` or `python`. **ALWAYS** use the `uv run` or `uv add` prefix.
2. **NEVER** modify `pyproject.toml` or `uv.lock` manually. Use `uv add <package>` to update dependencies.
3. **NEVER** commit sensitive data, secrets, `config.json`, or `.env` files.
4. **ALWAYS** ensure that `uv run ruff check .` and `uv run pytest` pass with zero errors before considering a task complete.


# Python Unit Testing Standards

## Structure: AAA Pattern

Structure every test using the **Arrange / Act / Assert** triple block. Use comments `# given`, `# when`, `# then` to mark each section explicitly.

## Test Naming

- Write test names in **snake_case** (Python convention)
- The name must describe the **business rule** the system enforces — not restate the implementation
- Do **not** prefix with `test_` inside the name; the function name prefix is sufficient

**Good examples:**
- `test_returns_discounted_price_for_premium_customers`
- `test_rejects_order_when_stock_insufficient`
- `test_finds_patients_with_matching_surname`

**Bad examples:**
- `test_get_discount` — restates implementation
- `test_when_premium_customer_get_discount` — describes mechanics, not the rule

## Coverage

- Cover both the **happy path** and all relevant **error/edge cases** for every feature
- Write a separate test function for each distinct scenario

## Fast and Informative Failures

- Each test must fail for **exactly one reason**: the business rule it validates has stopped being met
- Do not assert unrelated fields or side effects within the same test

## Robustness and Flexibility

- Test **behavior**, not implementation details

---

# Python Logging Standards (stdlib logging)

When writing or editing Python code, all log statements **must** follow these rules.

## Message Format

```python
logger.info("Action/Result key1=%s key2=%s ...", value1, value2)
```

The message prefix is a short, static action or result phrase. All dynamic values follow as explicit positional arguments.

## Rules

| Rule | Forbidden | Correct |
|------|-----------|---------|
| No embedded data in the phrase | `logger.info(f"Processing file {file_name}")` | `logger.info("Processing file file_name=%s", file_name)` |
| Explicit key names on every placeholder | `logger.info("Processed: %s", file_name)` | `logger.info("Processed file_name=%s", file_name)` |
| No generic key names | `id=%s`, `data=%s`, `value=%s` | `experiment_id=%s`, `reagent_id=%s`, `stored_name=%s` |
| No string concatenation | `logger.error("Error: " + str(e))` | `logger.error("Operation failed error=%s", str(e))` |
| No colons or commas in template | `logger.info("Result: %s, count: %s", ...)` | `logger.info("Result completed result=%s count=%s", ...)` |
| Concise phrase, no narrative | `logger.info("We are now starting to process the incoming request")` | `logger.info("Request received request_id=%s", request_id)` |

## Key Ordering (left to right)

1. `experiment_id` / `reagent_id` / `equipment_id` / `attachment_id`
2. Main entity name (`experiment_title`, `file_name`, `stored_name`, ...)
3. Metrics / counters (`count`, `duration_ms`, `size_bytes`, ...)
4. Status / result (`status`, `error`, `result`, ...)

## Log Level Selection

| Level | Use for |
|-------|---------|
| `DEBUG` | Technical / internal state, function entry/exit, detailed variable values |
| `INFO` | Normal business flow milestones, successful operations |
| `WARNING` | Recoverable issues, unexpected but non-fatal conditions (e.g. AI provider unavailable) |
| `ERROR` | Failures requiring action, exceptions caught and handled |
| `CRITICAL` | System-wide failures, unrecoverable errors |

## Examples

### Bad ❌

```python
logger.info("Processing experiment " + str(experiment_id))
logger.error(f"Failed to process: {id}, error: {e}")
logger.debug("Result: %s count: %s", result, count)
```

### Good ✅

```python
logger.info("Experiment created experiment_id=%s", experiment_id)
logger.error("Hash generation failed experiment_id=%s error=%s", experiment_id, str(e))
logger.warning("AI provider unavailable provider=%s", provider_name)
logger.error("Database query failed query_name=%s error=%s", query_name, str(e), exc_info=True)
```

## Exception Logging

```python
try:
    perform_operation()
except Exception as e:
    logger.error("Operation failed experiment_id=%s error=%s", experiment_id, str(e), exc_info=True)
```

## Performance Notes

- %-formatting is evaluated lazily (arguments only processed if log level is enabled)
- Avoid expensive function calls in log arguments: `logger.info("Result=%s", expensive_fn())` may still call the function

---

# Clear English Guidelines

Write all generated text in clear English, including code comments, documentation, commit notes, and error messages.

- Prefer short, direct sentences and plain language
- Avoid unnecessary jargon; if a technical term is required, explain it briefly
- Keep comments focused on intent and behavior, not obvious line-by-line restatements
- Domain terms from the data model (e.g. `experiment`, `reagent`, `smiles`, `hash_sha256`) may be used as-is in code and comments without translation

---

<!--[1] Tim Hopper, "How to Set Up CLAUDE.md for a Python Project," pydevtools.com, 2024. [Online]. Available: https://pydevtools.com/handbook/how-to/how-to-use-the-pydevtools-claude-md-template/. Accessed: Jun. 6, 2026. -->
