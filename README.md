# Khemeia ELN

Khemeia ELN is a local-first laboratory notebook for chemistry researchers.
It uses Python, NiceGUI, SQLite, RDKit, and local AI providers.

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
uv run python main.py
```
