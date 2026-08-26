from app.ai.contracts import ModelCallResult, ModelRequest
from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase, ConceptSystemLink
from app.models.image import Image
from app.models.tag import Tag
from app.models.user import User
from app.schemas.asset_agent import AssetAgentChatRequest
from app.services.asset_agent_service import AssetAgentService
from tests.conftest import login


def test_asset_agent_uses_confirmed_asset_context(db_factory):
    with db_factory() as db:
        system = Tag(name="AI 个性化学习", code="ai_personalized_learning")
        concept = BusinessConcept(
            code="ai_learning_plan",
            name="AI定制班",
            definition="根据孩子水平生成专属学习方案。",
            recommendation_text="不是所有孩子学一套，而是因材施教。",
        )
        concept.system_links.append(ConceptSystemLink(system_tag=system))
        concept.search_phrases.append(
            ConceptSearchPhrase(phrase="因材施教", review_status="accepted")
        )
        group = AssetGroup(title="AI定制班主图", created_by="admin")
        image = Image(
            title="定制规划图",
            file_name="plan.png",
            storage_key="plan.png",
            thumbnail_storage_key="plan-thumb.png",
            media_type="image/png",
            size_bytes=100,
            image_summary="页面展示根据水平安排课程。",
            asset_group=group,
        )
        group.primary_image_id = image.id
        group.concept_links.append(
            AssetConceptLink(
                concept=concept,
                relation_role="expresses",
                origin="manual",
                review_status="accepted",
                evidence_reason="画面展示定制学习规划。",
            )
        )
        group.search_phrases.append(
            AssetSearchPhrase(
                phrase="每个孩子都有自己的学习方案",
                origin="manual",
                review_status="accepted",
            )
        )
        user = User(username="agent-user", password_hash="x", role="business")
        db.add_all([system, concept, group, image, user])
        db.commit()

        provider = _RecordingProvider()
        response = AssetAgentService(db, provider).chat(
            user,
            AssetAgentChatRequest(message="这张图怎么跟家长解释？", image_ids=[image.id]),
        )

    assert response.used_model is True
    assert response.session is not None
    assert response.session.title == "定制规划图"
    assert [message.role for message in response.session.messages] == [
        "assistant",
        "system",
        "user",
        "assistant",
    ]
    assert "AI定制班" in provider.last_request.input_text
    assert "每个孩子都有自己的学习方案" in provider.last_request.input_text
    assert response.context_cards[0].title == "定制规划图"
    assert response.answer == "这张图可以用来解释 AI 定制班。"


def test_asset_agent_sessions_are_user_private_even_for_admin(client):
    business_csrf = login(client, "business", "business-password")
    business_headers = {"X-CSRF-Token": business_csrf, "Origin": "http://localhost:5173"}
    created = client.post("/api/asset-agent/sessions", json={}, headers=business_headers)
    assert created.status_code == 200
    session_id = created.json()["id"]

    sent = client.post(
        f"/api/asset-agent/sessions/{session_id}/messages",
        json={"message": "这是业务用户自己的聊天"},
        headers=business_headers,
    )
    assert sent.status_code == 200
    assert sent.json()["conversationId"] == session_id
    assert len(sent.json()["session"]["messages"]) == 3

    listed = client.get("/api/asset-agent/sessions")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["sessions"]] == [session_id]

    admin_csrf = login(client, "admin", "admin-password")
    admin_headers = {"X-CSRF-Token": admin_csrf, "Origin": "http://localhost:5173"}
    admin_listed = client.get("/api/asset-agent/sessions")
    assert admin_listed.status_code == 200
    assert admin_listed.json()["sessions"] == []

    admin_send = client.post(
        f"/api/asset-agent/sessions/{session_id}/messages",
        json={"message": "管理员不能接着别人的会话聊"},
        headers=admin_headers,
    )
    assert admin_send.status_code == 404

    admin_context = client.patch(
        f"/api/asset-agent/sessions/{session_id}/context",
        json={"contextImages": []},
        headers=admin_headers,
    )
    assert admin_context.status_code == 404

    admin_delete = client.delete(
        f"/api/asset-agent/sessions/{session_id}",
        headers=admin_headers,
    )
    assert admin_delete.status_code == 404

    business_csrf = login(client, "business", "business-password")
    business_headers = {"X-CSRF-Token": business_csrf, "Origin": "http://localhost:5173"}
    still_owned = client.get("/api/asset-agent/sessions", headers=business_headers)
    assert [item["id"] for item in still_owned.json()["sessions"]] == [session_id]


class _RecordingProvider:
    name = "recording"

    @property
    def configured(self):
        return True

    def generate_json(self, request: ModelRequest):
        self.last_request = request
        attempts = (
            {
                "provider": "recording",
                "model": "test",
                "status": "ok",
                "duration_ms": 1,
                "error": "",
            }
        )
        return ModelCallResult(
            {
                "answer": "这张图可以用来解释 AI 定制班。",
                "suggestedQuestions": ["它和真人督学有什么区别？"],
            },
            attempts,
        )
