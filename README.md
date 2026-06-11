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
uv run python -m main
```

## First Launch

If `config.json` is missing or incomplete, Khemeia ELN shows a blocking
welcome form before loading the app. Use it to enter your profile and choose
the local data folder.

The `Data folder` field can be filled with the native folder picker or by
typing the path manually. This folder becomes the base location for local data,
attachments, and exports.
