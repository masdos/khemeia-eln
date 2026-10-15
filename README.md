# Khemeia ELN

Khemeia ELN is a local-first electronic laboratory notebook for chemistry researchers.
It centralizes experiments, reagent/equipment traceability, and attachments, and
uses a local AI model to draft technical reports.

## Context and goals

This project was born in the [AI Expert](https://devexpert.io/cursos/expert/ai)
course. Two constraints shaped every technical decision:

* **No paid AI subscriptions.** All AI features must work without third-party
  accounts or paid APIs.
* **Data privacy.** Lab data never leaves the machine, so the app is a desktop
  application backed by a local SQLite database, and report generation runs
  against a local model through Ollama (`http://localhost:11434`).

## Features

* **Experiment workflow:** dashboard with text search and state filter, quick
  creation dialog, detail page with question, procedure, result, and conclusions.
* **Inventory traceability:** link reagents and equipment to experiments, usage
  history per resource, guarded deletion of resources in use, stock filter.
* **Attachments and export:** file attachments with editable descriptions,
  Markdown editor with live preview, SMILES structure rendering (RDKit),
  experiment export to Markdown, PDF, and DOCX.
* **Local AI assistant:** multi-experiment selector, installed-model dropdown
  with last-used memory, streaming draft generation with live preview,
  project-first flow that saves reports to the database before exporting.
* **User profile:** one-time welcome form (name, email, optional institution)
  used for authorship auditing and export headers.

## Tech stack

Python 3.12+, NiceGUI (desktop via `pywebview`), SQLite, RDKit, Ollama.
Dependency management with `uv`; linting and formatting with `ruff`;
testing with `pytest`.

## Installation

Install the project environment from the lockfile:

```powershell
uv sync
```

## Development Commands

Run the test suite:

```powershell
uv run pytest
```

Run lint checks:

```powershell
uv run ruff check .
```

Start the desktop app:

```powershell
uv run python -m main
```

## AI-assisted development

The project followed a spec-driven workflow. Research on electronic lab
notebooks (ELN) started with NotebookLM using [eLabFTW](https://www.elabftw.net/)
as reference. A Gemini Gem provided by the course then generated the
spec-driven development documents (`docs/spec.md`, `docs/plan.md`), which were
validated by Claude Sonnet 5 acting as judge for the plan and the spec. The
`docs/feature_list.json` backlog was generated with Claude following the
format from [harness-sdd](https://github.com/betta-tech/harness-sdd/blob/main/feature_list.json).
Implementation began with Codex for the first commits and continued with
opencode agents afterwards. Agent behavior is governed by `AGENTS.md`, based on
the [pydevtools Python template](https://pydevtools.com/handbook/how-to/how-to-use-the-pydevtools-claude-md-template/)
and customized for this project (uv workflow, pytest/ruff conventions, Ollama-only
AI backend, commit and logging rules). Planned work runs through the
`khemeia-next-feature` skill (`.agents/skills/khemeia-next-feature/SKILL.md`),
which picks the first `pending` feature from `feature_list.json`, loads the
architectural context, and drives it to `done`. Fixes and small additions
outside the backlog are done as vibecoding: describe the need by chat, adjust,
and refine iteratively (see `docs/vibe_codign_implementation.md`).

| Model | Commits | Share |
|---|---|---|
| `muse-spark-1.3-contributor-free` | 68 | 38.9% |
| `mimo-v2.5-free` | 45 | 25.7% |
| `deepseek-v4-flash-free` | 23 | 13.1% |
| `mimo-v2-free` | 10 | 5.7% |
| manual / unknown (28/05–08/06/2026) | 10 | 5.7% |
| uncertain `gemma4:e2b` or manual (11–23/06/2026) | 8 | 4.6% |
| `GPT-5.6 Terra` | 4 | 2.3% |
| `Claude Sonnet 5` | 3 | 1.7% |
| `gpt-3.5-turbo` | 2 | 1.1% |
| `big-pickle` | 1 | 0.6% |
| `Claude Sonnet 5 + muse-spark` (shared) | 1 | 0.6% |
| **Total (`5ffc3cd` → `HEAD`)** | **175** | **100%** |

Attribution: 106 commits carry an `AI-Model:` trailer in the commit message
(since `ead9e7`); the previous 69 commits are attributed by matching commit
dates with `opencode session export` model data. Reproduce with
`git log --grep="AI-Model:"` and `opencode session list` /
`opencode export <sessionID>`.

### Human review

No agent output reaches `main` unreviewed:

* **Pre-commit hooks** (`.pre-commit-config.yaml`): `uv run ruff check .` and
  `uv run pytest` run automatically before every commit and block it on failure.
* **Diff review:** each change is inspected (`git diff`, `git status`) before
  staging, and only the intended files are committed.
* **GPG-signed commits:** every commit is signed (`git commit -S`), so authorship
  and integrity are verifiable.

## Limitations

* Single-user desktop scope: no multi-user access control, no audit log beyond
  authorship fields, and no deployment packaging yet.
* Local AI depends on the user's hardware: draft quality and generation time
  vary with the installed Ollama model, and an empty model list disables
  generation by design.
* RDKit is optional at runtime: SMILES rendering returns `None` when the package
  is unavailable or the SMILES string is invalid.
* Commit authorship before the `AI-Model:` trailer era (69 commits) is
  reconstructed from session dates, so 18 of them remain manual or uncertain.

## Credits and Attributions

This project uses third-party graphical assets:
* **Logo design:** Based on the `alembic` emoji by **Marleen Heine** from the [OpenMoji](https://openmoji.org/library/emoji-2697/) project.
* **License:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
* **Modifications:** None.
