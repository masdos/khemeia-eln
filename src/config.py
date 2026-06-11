import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

CONFIG_PATH = Path("config.json")
REQUIRED_FIELDS = ("user_name", "user_email", "base_dir", "ai_provider")
AI_PROVIDERS = ("lmstudio", "ollama", "remote")
ENV_KEYS = {
    "user_name": ("USER_NAME", "KHEMEIA_USER_NAME"),
    "user_email": ("USER_EMAIL", "KHEMEIA_USER_EMAIL"),
    "base_dir": ("BASE_DIR", "KHEMEIA_BASE_DIR"),
    "ai_provider": ("AI_PROVIDER", "KHEMEIA_AI_PROVIDER"),
}

_current_config: "AppConfig | None" = None


class ConfigValidationError(ValueError):
    """Raised when the user profile is missing required values."""


@dataclass(frozen=True)
class AppConfig:
    user_name: str
    user_email: str
    base_dir: Path
    ai_provider: str

    def to_json_data(self) -> dict[str, str]:
        return {
            "user_name": self.user_name,
            "user_email": self.user_email,
            "base_dir": str(self.base_dir),
            "ai_provider": self.ai_provider,
        }


def load_config(
    config_path: str | Path = CONFIG_PATH,
    env: Mapping[str, str] | None = None,
    load_env_file: bool = True,
) -> AppConfig | None:
    """Load the user profile, applying developer environment overrides."""
    if load_env_file:
        load_dotenv()

    path = Path(config_path)
    if not path.exists():
        return None

    try:
        raw_config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    if not isinstance(raw_config, dict):
        return None

    raw_config.update(_env_overrides(env or os.environ))

    try:
        config = validate_config(raw_config)
    except ConfigValidationError:
        return None

    set_current_config(config)
    return config


def write_config(
    config_data: Mapping[str, object],
    config_path: str | Path = CONFIG_PATH,
) -> AppConfig:
    """Validate and persist the user profile as config.json."""
    config = validate_config(config_data)
    path = Path(config_path)
    path.write_text(
        json.dumps(config.to_json_data(), indent=2) + "\n",
        encoding="utf-8",
    )
    set_current_config(config)
    return config


def validate_config(config_data: Mapping[str, object]) -> AppConfig:
    values = {field: _clean_value(config_data.get(field)) for field in REQUIRED_FIELDS}
    missing_fields = [field for field, value in values.items() if not value]
    if missing_fields:
        raise ConfigValidationError("Profile is missing required fields")

    ai_provider = values["ai_provider"].lower()
    if ai_provider not in AI_PROVIDERS:
        raise ConfigValidationError("Profile has an unsupported AI provider")

    return AppConfig(
        user_name=values["user_name"],
        user_email=values["user_email"],
        base_dir=Path(values["base_dir"]),
        ai_provider=ai_provider,
    )


def get_current_config() -> AppConfig:
    if _current_config is None:
        raise ConfigValidationError("Profile has not been loaded")

    return _current_config


def set_current_config(config: AppConfig) -> None:
    global _current_config

    _current_config = config


def clear_current_config() -> None:
    global _current_config

    _current_config = None


def _env_overrides(env: Mapping[str, str]) -> dict[str, str]:
    overrides = {}
    for field, keys in ENV_KEYS.items():
        for key in keys:
            if key in env:
                overrides[field] = env[key]
                break

    return overrides


def _clean_value(value: object) -> str:
    if value is None:
        return ""

    if isinstance(value, Path):
        return str(value).strip()

    return str(value).strip()
