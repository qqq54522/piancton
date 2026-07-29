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


def test_image_service_does_not_own_lifecycle_or_tagging_workflows():
    path = ROOT / "services" / "image_service.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    class_node = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ImageService"
    )
    method_names = {node.name for node in class_node.body if isinstance(node, ast.FunctionDef)}

    assert {
        "delete",
        "list_deleted",
        "restore",
        "purge",
        "update_tags",
        "review_business_label",
        "_promote_ai_label_to_manual",
        "_remove_rejected_ai_label_outputs",
    }.isdisjoint(method_names)

    imports = imported_modules(path)
    assert "app.repositories.tag_repository" not in imports
    assert "ImageBusinessLabel" not in path.read_text(encoding="utf-8")


def test_search_service_keeps_ranking_and_query_expansion_outside_orchestrator():
    path = ROOT / "services" / "search_service.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SearchService"
    )
    method_names = {node.name for node in class_node.body if isinstance(node, ast.FunctionDef)}

    assert {
        "_build_response",
        "_build_scored_image",
        "_rerank_hits",
        "_rerank_document",
        "_database_queries",
        "_queries_from_understanding",
        "_smart_keyword",
        "_match_level",
        "_business_label_name",
    }.isdisjoint(method_names)
    assert "ImageBusinessLabel" not in source
    assert "ScoredImage" not in source
    assert "image_to_read" not in source


def test_search_service_keeps_recall_backends_outside_orchestrator():
    path = ROOT / "services" / "search_service.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SearchService"
    )
    method_names = {node.name for node in class_node.body if isinstance(node, ast.FunctionDef)}

    assert {
        "_search_meilisearch",
        "_search_embeddings",
    }.isdisjoint(method_names)
    assert "httpx" not in source
    assert "cosine_similarity" not in source
    assert "load_vector" not in source
    assert "repo.search" not in source
    assert "repo.list_embeddings" not in source


def test_phase4_search_orchestration_stays_split_and_bounded():
    facade = ROOT / "services" / "search_service.py"
    components = ROOT / "services" / "search_service_components.py"
    orchestrator = ROOT / "services" / "search_orchestrator.py"
    facade_source = facade.read_text(encoding="utf-8")
    orchestrator_source = orchestrator.read_text(encoding="utf-8")
    tree = ast.parse(orchestrator_source)
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "AsyncSearchOrchestrator"
    )
    method_names = {
        node.name
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert len(facade_source.splitlines()) <= 150
    assert len(orchestrator_source.splitlines()) <= 300
    assert "app.services.search_service_components" in imported_modules(facade)
    assert "app.services.search_external_branches" in imported_modules(components)
    assert "app.services.search_rerank_coordinator" in imported_modules(components)
    assert {
        "_start_meilisearch",
        "_start_embedding",
        "_start_understanding",
        "_hydrate_meilisearch",
        "_hydrate_embedding",
        "_rerank_with_deadline",
    }.isdisjoint(method_names)


def test_search_boundary_services_do_not_depend_on_repositories():
    boundary_files = [
        ROOT / "services" / "query_expansion_service.py",
        ROOT / "services" / "search_ranking_service.py",
        ROOT / "services" / "image_semantic_profile_service.py",
        ROOT / "services" / "query_understanding_service.py",
        ROOT / "services" / "search_concept_routing_service.py",
        ROOT / "services" / "search_scorer.py",
        ROOT / "services" / "search_response_builder.py",
        ROOT / "services" / "semantic_rerank_service.py",
    ]
    violations = []
    for path in boundary_files:
        imports = imported_modules(path)
        if any(module.startswith("app.repositories") for module in imports):
            violations.append(path.name)
    assert violations == []


def test_search_ranking_service_stays_as_orchestrator():
    path = ROOT / "services" / "search_ranking_service.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SearchRankingService"
    )
    method_names = {node.name for node in class_node.body if isinstance(node, ast.FunctionDef)}

    assert {
        "build_scored_image",
        "match_level",
        "_matching_names",
        "_strict_hit",
        "_matches_primary_category",
        "_matches_primary_label",
    }.isdisjoint(method_names)
    assert "image_to_read" not in source
    assert "NEGATION_MARKERS" not in source
    assert "_contains_unnegated_concept" not in source


def test_concept_routing_service_stays_focused_and_bounded():
    path = ROOT / "services" / "search_concept_routing_service.py"
    source = path.read_text(encoding="utf-8")

    assert len(source.splitlines()) <= 220
    assert "class SearchConceptRoutingService" in source
    assert "app.repositories" not in source
    assert "Meilisearch" not in source
    assert "Embedding" not in source
    assert "AssetSelectionPolicyService" in source
    assert "苏格拉底" not in source


def test_asset_selection_policy_stays_config_driven_and_bounded():
    path = ROOT / "services" / "asset_selection_policy_service.py"
    source = path.read_text(encoding="utf-8")

    assert len(source.splitlines()) <= 140
    assert "class AssetSelectionPolicyService" in source
    assert "苏格拉底" not in source
    assert "app.repositories" not in source
    assert "search_orchestrator" not in source


def test_search_service_calls_query_understanding_without_owning_intent_config():
    facade = ROOT / "services" / "search_service.py"
    components = ROOT / "services" / "search_service_components.py"
    component_imports = imported_modules(components)
    source = facade.read_text(encoding="utf-8") + components.read_text(encoding="utf-8")

    assert "app.services.query_understanding_service" in component_imports
    assert "app.domain.business_intents" not in component_imports
    assert "AI错题本" not in source
    assert "AI拍题精学" not in source
    assert "专家规划" not in source


def test_business_intents_domain_does_not_depend_on_services_or_repositories():
    imports = imported_modules(ROOT / "domain" / "business_intents.py")

    assert not any(module.startswith(("app.services", "app.repositories")) for module in imports)


def test_search_eval_domain_does_not_depend_on_services_or_repositories():
    imports = imported_modules(ROOT / "domain" / "search_eval.py")

    assert not any(module.startswith(("app.services", "app.repositories")) for module in imports)


def test_phase_1_to_3_workflows_keep_domain_boundaries_separate():
    concept_service = ROOT / "services" / "business_concept_service.py"
    asset_service = ROOT / "services" / "asset_service.py"
    relation_service = ROOT / "services" / "asset_relation_service.py"
    analysis_service = ROOT / "services" / "image_analysis_service.py"

    assert "app.models.image" not in imported_modules(concept_service)
    assert "app.models.business_concept" not in imported_modules(asset_service)
    assert "app.services.asset_relation_service" in imported_modules(analysis_service)
    assert "AssetConceptLink" not in analysis_service.read_text(encoding="utf-8")
    assert "ImageBusinessLabel" not in relation_service.read_text(encoding="utf-8")


def test_phase4_async_orchestrator_keeps_io_and_database_boundaries_separate():
    facade = ROOT / "services" / "search_service.py"
    components = ROOT / "services" / "search_service_components.py"
    orchestrator = ROOT / "services" / "search_orchestrator.py"
    api = ROOT / "api" / "v1" / "images.py"

    assert len(facade.read_text(encoding="utf-8").splitlines()) < 150
    assert "AsyncSearchOrchestrator" in components.read_text(encoding="utf-8")
    assert "ImageSummaryMatchService" not in facade.read_text(encoding="utf-8")
    assert not any(
        module.startswith(("app.repositories", "sqlalchemy", "httpx"))
        for module in imported_modules(orchestrator)
    )
    assert "async def search" in orchestrator.read_text(encoding="utf-8")
    assert "async def semantic_search" in api.read_text(encoding="utf-8")


def test_phase4_external_recall_returns_lightweight_candidates_before_hydration():
    meili = (ROOT / "services" / "meilisearch_recall_service.py").read_text(encoding="utf-8")
    embedding = (ROOT / "services" / "embedding_recall_service.py").read_text(encoding="utf-8")

    assert "def recall_candidates" in meili
    assert "ExternalSearchCandidate" in meili
    assert "def query_vector" in embedding
    assert "def score_candidates" in embedding
    assert "ExternalSearchCandidate" in embedding
