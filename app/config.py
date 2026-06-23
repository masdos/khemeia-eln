import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

REQUIRED_FIELDS = ("user_name", "user_email")
AI_PROVIDERS = ("lmstudio", "ollama", "remote")
ENV_KEYS = {
    "user_name": ("USER_NAME", "KHEMEIA_USER_NAME"),
    "user_email": ("USER_EMAIL", "KHEMEIA_USER_EMAIL"),
    "ai_provider": ("AI_PROVIDER", "KHEMEIA_AI_PROVIDER"),
}

_current_config: "AppConfig | None" = None


class ConfigValidationError(ValueError):
    """Raised when the user profile is missing required values."""


@dataclass(frozen=True)
class AppConfig:
    user_name: str
    user_email: str
    ai_provider: str | None

    def to_json_data(self) -> dict[str, str | None]:
        return {
            "user_name": self.user_name,
            "user_email": self.user_email,
            "ai_provider": self.ai_provider,
        }


def load_config(
    base_dir: Path,
    env: Mapping[str, str] | None = None,
    load_env_file: bool = True,
    pre_loaded_config: dict | None = None,
) -> AppConfig | None:
    """Load user profile from BASE_DIR/config.json.

    Args:
        base_dir: Application data directory (typically from BootstrapResult.base_dir)
        env: Environment variables for overrides (defaults to os.environ)
        load_env_file: Whether to load .env file via python-dotenv
        pre_loaded_config: Pre-loaded config dict for testing (bypasses file I/O)

    Returns:
        AppConfig if config.json exists and is valid, None otherwise
    """
    if load_env_file:
        load_dotenv()

    # Use pre-loaded config if provided; otherwise load from disk
    if pre_loaded_config is not None:
        raw_config = pre_loaded_config
    else:
        config_path = base_dir / "config.json"
        if not config_path.exists():
            return None

        try:
            raw_config = json.loads(config_path.read_text(encoding="utf-8"))
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
    base_dir: Path,
) -> AppConfig:
    """Validate and persist the user profile to BASE_DIR/config.json.

    Args:
        config_data: Configuration dict with user_name, user_email, ai_provider
        base_dir: Application data directory (typically from BootstrapResult.base_dir)

    Returns:
        AppConfig if validation succeeds

    Raises:
        ConfigValidationError: If required fields are missing or invalid
    """
    config = validate_config(config_data)
    config_path = base_dir / "config.json"
    config_path.write_text(
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

    ai_provider_value = _clean_value(config_data.get("ai_provider"))
    ai_provider = None if not ai_provider_value else ai_provider_value.lower()
    if ai_provider is not None and ai_provider not in AI_PROVIDERS:
        raise ConfigValidationError("Profile has an unsupported AI provider")

    return AppConfig(
        user_name=values["user_name"],
        user_email=values["user_email"],
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
