import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_imports_application_entry_point_without_starting_ui() -> None:
    # given
    module_path = PROJECT_ROOT / "main.py"
    spec = importlib.util.spec_from_file_location("khemeia_main", module_path)

    # when
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # then
    assert callable(module.main)


def test_contains_initial_project_directories() -> None:
    # given
    required_directories = [
        "src",
        "src/database",
        "src/repositories",
        "src/services",
        "src/services/ai",
        "src/ui/pages",
        "src/ui/components",
        "data/attachments",
        "tests/services",
        "tests/repositories",
    ]

    # when
    missing_directories = [
        directory
        for directory in required_directories
        if not (PROJECT_ROOT / directory).is_dir()
    ]

    # then
    assert missing_directories == []
