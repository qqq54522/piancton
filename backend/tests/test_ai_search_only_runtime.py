from app.api import dependencies


def test_legacy_ai_and_api_center_routes_are_removed(client):
    assert client.get("/api/admin/api-center/summary").status_code == 404
    assert client.get("/api/ai/provider").status_code == 404
    assert client.post("/api/ai/search-intent", json={"keyword": "举一反三"}).status_code == 404


def test_search_runtime_has_no_extra_model_clients(db_factory):
    with db_factory() as db:
        service = dependencies.get_search_service(db)

    orchestrator = service.orchestrator
    assert orchestrator.query_understanding.ai_service is None
    assert orchestrator.external_branches.vikingdb_knowledge_router is None
    assert orchestrator.external_branches.embedding.configured is False
    assert orchestrator.ranking.reranker.configured is False
    assert service.ai_search is not None


def test_asset_agent_runtime_uses_only_viking_ai_search(db_factory):
    with db_factory() as db:
        service = dependencies.get_asset_agent_service(db)

    assert not hasattr(service, "provider")
    assert not hasattr(service, "knowledge_router")
    assert service.ai_search_chat is None or service.ai_search_chat.base_url.startswith(
        "https://aisearch."
    )
