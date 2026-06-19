import json

import pytest

from app.config import (
    ConfigValidationError,
    clear_current_config,
    get_current_config,
    load_config,
    write_config,
)


def test_reads_existing_profile_from_config_file(tmp_path) -> None:
    # given
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "user_name": "Ada Lovelace",
                "user_email": "ada@lab.edu",
                "base_dir": str(tmp_path / "khemeia"),
                "ai_provider": "lmstudio",
            }
        ),
        encoding="utf-8",
    )

    # when
    config = load_config(config_path, load_env_file=False)

    # then
    assert config is not None
    assert config.user_name == "Ada Lovelace"


def test_returns_none_when_config_file_is_missing(tmp_path) -> None:
    # given
    config_path = tmp_path / "config.json"

    # when
    config = load_config(config_path, load_env_file=False)

    # then
    assert config is None


def test_returns_none_when_config_file_is_incomplete(tmp_path) -> None:
    # given
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "user_name": "Ada Lovelace",
                "user_email": "ada@lab.edu",
                "base_dir": str(tmp_path / "khemeia"),
            }
        ),
        encoding="utf-8",
    )

    # when
    config = load_config(config_path, load_env_file=False)

    # then
    assert config is None


def test_writes_profile_to_config_file(tmp_path) -> None:
    # given
    config_path = tmp_path / "config.json"
    profile = {
        "user_name": "Ada Lovelace",
        "user_email": "ada@lab.edu",
        "base_dir": tmp_path / "khemeia",
        "ai_provider": "lmstudio",
    }

    # when
    config = write_config(profile, config_path)

    # then
    stored_profile = json.loads(config_path.read_text(encoding="utf-8"))
    assert stored_profile == config.to_json_data()


def test_rejects_profile_when_required_field_is_missing(tmp_path) -> None:
    # given
    config_path = tmp_path / "config.json"
    profile = {
        "user_name": "Ada Lovelace",
        "user_email": "ada@lab.edu",
        "base_dir": tmp_path / "khemeia",
    }

    # when
    with pytest.raises(ConfigValidationError):
        write_config(profile, config_path)

    # then
    assert not config_path.exists()


def test_exposes_loaded_profile_globally(tmp_path) -> None:
    # given
    clear_current_config()
    config_path = tmp_path / "config.json"
    write_config(
        {
            "user_name": "Ada Lovelace",
            "user_email": "ada@lab.edu",
            "base_dir": tmp_path / "khemeia",
            "ai_provider": "lmstudio",
        },
        config_path,
    )

    # when
    current_config = get_current_config()

    # then
    assert current_config.user_email == "ada@lab.edu"


def test_environment_values_override_config_file(tmp_path) -> None:
    # given
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "user_name": "Ada Lovelace",
                "user_email": "ada@lab.edu",
                "base_dir": str(tmp_path / "khemeia"),
                "ai_provider": "lmstudio",
            }
        ),
        encoding="utf-8",
    )
    env = {
        "USER_NAME": "Grace Hopper",
        "USER_EMAIL": "grace@lab.edu",
        "BASE_DIR": str(tmp_path / "override"),
        "AI_PROVIDER": "ollama",
    }

    # when
    config = load_config(config_path, env=env, load_env_file=False)

    # then
    assert config is not None
    assert config.user_name == "Grace Hopper"
