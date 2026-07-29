from pathlib import Path

import pytest

from app.core.errors import AppError
from app.models.business_concept import (
    BusinessConcept,
    ConceptSearchPhrase,
    ConceptSystemLink,
)
from app.models.tag import Tag
from app.services import analysis_tasks
from app.services.ai_knowledge_service import AiKnowledgeService
from app.services.ai_service import AiService
from app.services.image_analysis_service import ImageAnalysisService


class StaticProvider:
    name = "test"
    configured = True

    def __init__(self, payload):
        self.payload = payload

    def generate_json(self, _request):
        return self.payload


class SequenceProvider:
    name = "test"
    configured = True

    def __init__(self, payloads):
        self.payloads = iter(payloads)

    def generate_json(self, _request):
        return next(self.payloads)


def _analysis_payload(system_name: str, concept_name: str):
    return {
        "image_summary": "画面展示重命名后的卖点功能，不是普通课程页。",
        "semantic_profile": {
            "visual_facts": ["卖点功能页面"],
            "scenes": ["功能展示场景"],
            "asset_search_phrases": ["重命名卖点表达"],
        },
        "concept_suggestions": [
            {
                "system_name": system_name,
                "concept_name": concept_name,
                "confidence": 0.9,
                "evidence_level": "A",
                "relation_role": "expresses",
                "reason": "画面直接展示该功能，不是相邻卖点的界面。",
            }
        ],
    }


def _seed_school_system(db) -> Tag:
    system = Tag(
        code="sync_school",
        name="同步校内体系",
        color="#6366F1",
        node_type="system",
        assignable=False,
        status="active",
    )
    db.add(system)
    return system


def test_knowledge_catalog_uses_database_names_and_manual_phrases(db_factory):
    with db_factory() as db:
        system = _seed_school_system(db)
        db.add(
            BusinessConcept(
                code="animation_explanation",
                name="动画讲解精学",
                definition="用动画讲透课堂知识点的功能。",
                system_links=[ConceptSystemLink(system_tag=system)],
                search_phrases=[
                    ConceptSearchPhrase(
                        phrase="孩子看动画就能听懂",
                        phrase_type="pain",
                        origin="manual",
                        review_status="accepted",
                    ),
                    ConceptSearchPhrase(
                        phrase="数据库已采纳的种子长句",
                        phrase_type="official",
                        origin="source_document",
                        review_status="accepted",
                    ),
                    ConceptSearchPhrase(
                        phrase="动画讲解",
                        phrase_type="alias",
                        origin="source_document",
                        review_status="rejected",
                    ),
                ],
            )
        )
        db.commit()
        knowledge = AiKnowledgeService(db).knowledge()

    assert knowledge is not None
    assert "动画讲解精学" in knowledge.catalog_text
    assert "孩子看动画就能听懂" in knowledge.catalog_text
    assert "数据库已采纳的种子长句" in knowledge.catalog_text
    assert not any(
        "动画讲解" in line
        for line in knowledge.catalog_text.splitlines()
        if "常见表达" in line
    )
    assert ("同步校内体系", "动画讲解精学") in knowledge.concept_pairs
    assert "animation_explanation" in knowledge.concept_codes
    assert dict(knowledge.concept_display_names)["animation_explanation"] == (
        "同步校内体系 > 动画讲解精学"
    )
    prompt_context = dict(knowledge.concept_prompt_contexts)[
        "animation_explanation"
    ]
    assert "用动画讲透课堂知识点的功能" in prompt_context
    assert "孩子看动画就能听懂" in prompt_context
    common_line = next(
        line for line in prompt_context.splitlines() if "常见表达" in line
    )
    common_phrases = common_line.split("：", 1)[1].split("、")
    assert "动画讲解" not in common_phrases


def test_knowledge_catalog_drops_deprecated_concepts(db_factory):
    with db_factory() as db:
        _seed_school_system(db)
        db.add(
            BusinessConcept(
                code="animation_explanation",
                name="动画精讲",
                status="deprecated",
            )
        )
        db.commit()
        knowledge = AiKnowledgeService(db).knowledge()

    assert knowledge is not None
    assert "animation_explanation" not in knowledge.concept_codes
    assert "`animation_explanation`" not in knowledge.catalog_text


def test_image_analysis_validation_follows_database_knowledge(db_factory):
    with db_factory() as db:
        system = _seed_school_system(db)
        db.add(
            BusinessConcept(
                code="animation_explanation",
                name="动画讲解精学",
                system_links=[ConceptSystemLink(system_tag=system)],
            )
        )
        db.commit()
        knowledge = AiKnowledgeService(db).knowledge()

    assert knowledge is not None
    renamed = AiService(
        StaticProvider(_analysis_payload("同步校内体系", "动画讲解精学")),
        knowledge=knowledge,
    ).analyze_image(Path("unused.png"))
    assert renamed.concept_suggestions[0].concept_name == "动画讲解精学"

    with pytest.raises(AppError) as exc_info:
        AiService(
            StaticProvider(_analysis_payload("同步校内体系", "模型临时发明的概念")),
            knowledge=knowledge,
        ).analyze_image(Path("unused.png"))
    assert exc_info.value.code == "unknown_concept_suggestions"


def test_image_analysis_persistence_accepts_database_only_concept_codes(db_factory):
    with db_factory() as db:
        db.add(
            BusinessConcept(
                code="database_only_selling_point",
                name="数据库新增卖点",
                status="active",
            )
        )
        db.commit()
        payload = _analysis_payload("", "数据库新增卖点")
        payload["concept_suggestions"] = [
            {
                "concept_code": "database_only_selling_point",
                "confidence": 0.9,
                "evidence_level": "A",
                "relation_role": "expresses",
                "reason": "画面直接展示数据库新增卖点，不是相邻卖点页面。",
            }
        ]
        result = AiService(
            StaticProvider(payload),
            knowledge=AiKnowledgeService(db).knowledge(),
        ).analyze_image(Path("unused.png"))
        assert result.concept_suggestions[0].concept_code == (
            "database_only_selling_point"
        )
        assert result.concept_suggestions[0].concept_name == "数据库新增卖点"

        service = ImageAnalysisService(db)

        assert service._concept_suggestion_codes(result) == [  # noqa: SLF001
            "database_only_selling_point"
        ]


def test_search_understanding_converts_database_only_codes_to_current_names(db_factory):
    with db_factory() as db:
        system = _seed_school_system(db)
        db.add(
            BusinessConcept(
                code="database_only_search_concept",
                name="数据库查询卖点",
                status="active",
                system_links=[ConceptSystemLink(system_tag=system)],
            )
        )
        db.commit()
        knowledge = AiKnowledgeService(db).knowledge()

    payload = {
        "original_query": "数据库独有查询",
        "normalized_query": "数据库查询卖点",
        "search_intent": "识别数据库新增卖点",
        "query_type": "business_intent_search",
        "expanded_terms": [],
        "matched_business_concepts": [
            {
                "concept": "database_only_search_concept",
                "relation": "direct",
                "reason": "数据库目录命中",
                "weight": 0.95,
            }
        ],
        "excluded_concepts": [],
        "search_strategy": "按当前数据库卖点召回",
    }
    route = {
        "original_query": "数据库独有查询",
        "route_type": "single_system",
        "candidate_systems": [
            {
                "code": "sync_school",
                "relation": "primary",
                "reason": "数据库测试体系",
                "weight": 0.9,
            }
        ],
        "excluded_systems": [],
    }
    understanding = AiService(
        SequenceProvider([route, payload]),
        knowledge=knowledge,
    ).understand_search("数据库独有查询")

    assert understanding.matched_business_concepts[0].concept == (
        "同步校内体系 > 数据库查询卖点"
    )


def test_background_analysis_uses_database_knowledge(
    db_factory,
    monkeypatch,
    tmp_path,
):
    with db_factory() as db:
        db.add(
            BusinessConcept(
                code="background_database_concept",
                name="后台数据库卖点",
                status="active",
            )
        )
        db.commit()

    captured = {}
    expected_result = object()

    class FakeImageService:
        def __init__(self, *_args, **_kwargs):
            pass

        def content(self, _image_id):
            return tmp_path / "unused.png", object()

    class FakeStorageProvider:
        def __init__(self, *_args, **_kwargs):
            pass

    class FakeUnitOfWork:
        def rollback(self):
            raise AssertionError("成功链路不应回滚")

    class FakeImageAnalysisService:
        def __init__(self, *_args, **_kwargs):
            self.uow = FakeUnitOfWork()

        def mark_running(self, image_id, analysis_run_id):
            captured["running"] = (image_id, analysis_run_id)

        def save_ai_analysis(self, image_id, result, *, analysis_run_id):
            captured["saved"] = (image_id, result, analysis_run_id)

        def mark_failed(self, _image_id, _analysis_run_id):
            raise AssertionError("成功链路不应标记失败")

    class RecordingAiService:
        def __init__(self, _provider, knowledge=None):
            captured["knowledge"] = knowledge

        def analyze_image(self, _path):
            return expected_result

    monkeypatch.setattr(analysis_tasks, "ImageService", FakeImageService)
    monkeypatch.setattr(
        analysis_tasks,
        "LocalStorageProvider",
        FakeStorageProvider,
    )
    monkeypatch.setattr(
        analysis_tasks,
        "ImageAnalysisService",
        FakeImageAnalysisService,
    )
    monkeypatch.setattr(analysis_tasks, "AiService", RecordingAiService)
    monkeypatch.setattr(
        analysis_tasks.EmbeddingIndexSync,
        "from_settings",
        lambda: object(),
    )

    analysis_tasks.run_image_analysis_task(
        "image-id",
        "run-id",
        object(),
        db_factory,
    )

    assert captured["knowledge"] is not None
    assert "background_database_concept" in captured["knowledge"].concept_codes
    assert captured["saved"] == ("image-id", expected_result, "run-id")
