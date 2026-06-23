import json

import pytest

from app.config import (
    ConfigValidationError,
    clear_current_config,
    get_current_config,
    load_config,
    set_current_config,
    validate_config,
    write_config,
)


def test_validate_config_allows_missing_ai_provider_and_defaults_to_none() -> None:
    # given
    config_data = {"user_name": "Ada", "user_email": "ada@example.com"}

    # when
    config = validate_config(config_data)

    # then
    assert config.ai_provider is None


def test_write_config_persists_ai_provider_as_null(tmp_path) -> None:
    # given
    config_path = tmp_path / "config.json"

    # when
    write_config({"user_name": "Ada", "user_email": "ada@example.com"}, config_path)

    # then
    saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved_config["ai_provider"] is None


def test_validate_config_rejects_unsupported_ai_provider() -> None:
    # given
    config_data = {
        "user_name": "Ada",
        "user_email": "ada@example.com",
        "ai_provider": "unknown",
    }

    # when / then
    with pytest.raises(ConfigValidationError, match="unsupported AI provider"):
        validate_config(config_data)


def test_load_config_returns_none_when_required_fields_are_missing(tmp_path) -> None:
    # given
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"user_name": "Ada"}), encoding="utf-8")

    # when
    config = load_config(config_path=config_path, load_env_file=False)

    # then
    assert config is None


def test_load_config_uses_environment_overrides() -> None:
    # given
    clear_current_config()

    # when
    config = load_config(
        config_path="/tmp/nonexistent-config.json",
        env={"USER_NAME": "Grace",
         "USER_EMAIL": "grace@example.com",
          "AI_PROVIDER": "ollama"},
        load_env_file=False,
        pre_loaded_config={},
    )

    # then
    assert config is not None
    assert config.user_name == "Grace"
    assert config.user_email == "grace@example.com"
    assert config.ai_provider == "ollama"


def test_current_config_state_can_be_set_and_cleared() -> None:
    # given
    clear_current_config()
    config = validate_config({"user_name": "Ada", "user_email": "ada@example.com"})

    # when
    set_current_config(config)

    # then
    assert get_current_config() == config

    # when
    clear_current_config()

    # then
    with pytest.raises(ConfigValidationError, match="not been loaded"):
        get_current_config()
