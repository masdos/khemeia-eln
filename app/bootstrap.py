from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs

APP_NAME = "khemeia-eln"
REQUIRED_CONFIG_FIELDS = ("user_name", "user_email")


@dataclass
class BootstrapResult:
    base_dir: Path
    config_path: Path
    db_path: Path
    config: dict = field(default_factory=dict)
    config_complete: bool = False


def _resolve_base_dir() -> Path:
    return Path(platformdirs.user_data_dir(APP_NAME))


def _create_directories(base_dir: Path) -> None:
    (base_dir / "attachments").mkdir(parents=True, exist_ok=True)
    (base_dir / "exports").mkdir(parents=True, exist_ok=True)


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _is_config_complete(config: dict) -> bool:
    return all(
        isinstance(config.get(f), str) and config[f].strip()
        for f in REQUIRED_CONFIG_FIELDS
    )


def run_bootstrap() -> BootstrapResult:
    """Prepare application directories and load user profile.

    Database initialization is handled by database.connection.get_connection().
    """
    base_dir = _resolve_base_dir()
    _create_directories(base_dir)

    db_path = base_dir / "database.db"
    config_path = base_dir / "config.json"

    config = _load_config(config_path)
    complete = _is_config_complete(config)

    return BootstrapResult(
        base_dir=base_dir,
        config_path=config_path,
        db_path=db_path,
        config=config,
        config_complete=complete,
    )
