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


def test_load_config_returns_none_when_required_fields_are_missing(tmp_path) -> None:
    # given
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"user_name": "Ada"}), encoding="utf-8")

    # when
    config = load_config(base_dir=tmp_path, load_env_file=False)

    # then
    assert config is None


def test_load_config_uses_environment_overrides(tmp_path) -> None:
    # given
    clear_current_config()

    # when
    config = load_config(
        base_dir=tmp_path,
        env={
            "USER_NAME": "Grace",
            "USER_EMAIL": "grace@example.com",
        },
        load_env_file=False,
        pre_loaded_config={},
    )

    # then
    assert config is not None
    assert config.user_name == "Grace"
    assert config.user_email == "grace@example.com"
    clear_current_config()


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


def test_validate_config_defaults_institution_to_none_when_missing() -> None:
    # given
    config_data = {"user_name": "Ada", "user_email": "ada@example.com"}

    # when
    config = validate_config(config_data)

    # then
    assert config.institution is None
    clear_current_config()


def test_validate_config_keeps_provided_institution() -> None:
    # given
    config_data = {
        "user_name": "Ada",
        "user_email": "ada@example.com",
        "institution": "  University of Example  ",
    }

    # when
    config = validate_config(config_data)

    # then
    assert config.institution == "University of Example"
    clear_current_config()


def test_write_then_load_roundtrips_institution(tmp_path) -> None:
    # given
    clear_current_config()
    write_config(
        {
            "user_name": "Ada",
            "user_email": "ada@example.com",
            "institution": "Example Institute",
        },
        base_dir=tmp_path,
    )

    # when
    config = load_config(base_dir=tmp_path, load_env_file=False)

    # then
    assert config is not None
    assert config.institution == "Example Institute"
    clear_current_config()


def test_load_config_applies_institution_env_override(tmp_path) -> None:
    # given
    clear_current_config()

    # when
    config = load_config(
        base_dir=tmp_path,
        env={
            "USER_NAME": "Grace",
            "USER_EMAIL": "grace@example.com",
            "INSTITUTION": "Example University",
        },
        load_env_file=False,
        pre_loaded_config={},
    )

    # then
    assert config is not None
    assert config.institution == "Example University"
    clear_current_config()


def test_validate_config_defaults_last_used_model_to_none_when_missing() -> None:
    # given
    config_data = {"user_name": "Ada", "user_email": "ada@example.com"}

    # when
    config = validate_config(config_data)

    # then
    assert config.last_used_model is None
    clear_current_config()


def test_validate_config_keeps_provided_last_used_model_verbatim() -> None:
    # given
    config_data = {
        "user_name": "Ada",
        "user_email": "ada@example.com",
        "last_used_model": "  qwen3:4b  ",
    }

    # when
    config = validate_config(config_data)

    # then
    assert config.last_used_model == "qwen3:4b"
    clear_current_config()


def test_load_config_reads_existing_profile_file(tmp_path) -> None:
    # given
    clear_current_config()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "user_name": "Ada",
                "user_email": "ada@example.com",
                "last_used_model": "gemma3:4b",
            }
        ),
        encoding="utf-8",
    )

    # when
    config = load_config(base_dir=tmp_path, load_env_file=False)

    # then
    assert config is not None
    assert config.user_name == "Ada"
    assert config.user_email == "ada@example.com"
    assert config.last_used_model == "gemma3:4b"
    clear_current_config()


def test_load_config_returns_none_when_config_file_is_missing(tmp_path) -> None:
    # given
    clear_current_config()

    # when
    config = load_config(base_dir=tmp_path, load_env_file=False)

    # then
    assert config is None


def test_load_config_does_not_require_last_used_model_for_welcome(
    tmp_path,
) -> None:
    # given
    clear_current_config()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"user_name": "Ada", "user_email": "ada@example.com"}),
        encoding="utf-8",
    )

    # when
    config = load_config(base_dir=tmp_path, load_env_file=False)

    # then
    assert config is not None
    assert config.last_used_model is None
    clear_current_config()


def test_write_then_load_roundtrips_last_used_model(tmp_path) -> None:
    # given
    clear_current_config()
    write_config(
        {
            "user_name": "Ada",
            "user_email": "ada@example.com",
            "last_used_model": "qwen3:4b",
        },
        base_dir=tmp_path,
    )

    # when
    config = load_config(base_dir=tmp_path, load_env_file=False)

    # then
    assert config is not None
    assert config.last_used_model == "qwen3:4b"
    clear_current_config()


def test_load_config_applies_last_used_model_env_override(tmp_path) -> None:
    # given
    clear_current_config()

    # when
    config = load_config(
        base_dir=tmp_path,
        env={
            "USER_NAME": "Grace",
            "USER_EMAIL": "grace@example.com",
            "LAST_USED_MODEL": "gemma3:4b",
        },
        load_env_file=False,
        pre_loaded_config={},
    )

    # then
    assert config is not None
    assert config.last_used_model == "gemma3:4b"
    clear_current_config()
