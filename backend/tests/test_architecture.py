import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "app"


def python_files(path: Path) -> list[Path]:
    return sorted(item for item in path.rglob("*.py") if item.name != "__init__.py")


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_service_layer_does_not_depend_on_fastapi():
    violations = []
    for path in python_files(ROOT / "services"):
        imports = imported_modules(path)
        if any(module == "fastapi" or module.startswith("fastapi.") for module in imports):
            violations.append(path.name)
    assert violations == []


def test_repository_layer_does_not_depend_on_api_or_services():
    violations = []
    for path in python_files(ROOT / "repositories"):
        imports = imported_modules(path)
        if any(module.startswith(("app.api", "app.services")) for module in imports):
            violations.append(path.name)
    assert violations == []


def test_repository_layer_does_not_commit_transactions():
    violations = []
    for path in python_files(ROOT / "repositories"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"commit", "rollback"}
            ):
                violations.append(f"{path.name}:{node.lineno}:{node.func.attr}")
    assert violations == []


def test_route_layer_does_not_depend_on_repositories_or_sqlalchemy():
    violations = []
    for path in python_files(ROOT / "api" / "v1"):
        imports = imported_modules(path)
        if any(module.startswith(("app.repositories", "sqlalchemy")) for module in imports):
            violations.append(path.name)
    assert violations == []


def test_app_code_does_not_mutate_schema_outside_migrations():
    violations = []
    for path in python_files(ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"create_all", "drop_all"}
            ):
                violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.func.attr}")
    assert violations == []


def test_external_search_does_not_leak_into_repositories():
    violations = []
    for path in python_files(ROOT / "repositories"):
        imports = imported_modules(path)
        if any("meilisearch" in module for module in imports):
            violations.append(path.name)
    assert violations == []


def test_ai_service_normalizes_model_payload_before_schema_validation():
    path = ROOT / "services" / "ai_service.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = imported_modules(path)
    calls_normalizer = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "normalize_model_payload"
        for node in ast.walk(tree)
    )

    assert "app.ai.normalizer" in imports
    assert calls_normalizer


def test_image_service_does_not_own_ai_analysis_persistence():
    source = (ROOT / "services" / "image_service.py").read_text(encoding="utf-8")

    assert "ImageAnalysisResult" not in source
    assert "AnalysisRun" not in source
    assert "ContentTag" not in source
    assert "ImageLevel2Category" not in source
    assert "create_analysis_run" not in source
    assert "save_ai_analysis" not in source
