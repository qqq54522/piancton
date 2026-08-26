import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast

from app.ai.contracts import ModelCallResult
from app.models.image import Image
from app.schemas.ai import SearchResultRecommendationReasonResult
from app.schemas.image import SearchResultConceptMatch
from app.services.search_models import SearchHit
from app.services.search_result_recommendation_service import (
    SearchResultRecommendationService,
)
from app.services.search_scorer import SearchScorer


def test_result_recommendation_reason_uses_current_image_and_query_context():
    scorer = SearchScorer()
    image = cast(Image, SimpleNamespace(
        title="考前冲刺三天提分海报",
        channel="官网大图",
        asset_group=SimpleNamespace(style_label="数据图", is_scene_image=False),
    ))

    reason = scorer._result_recommendation_reason(
        image=image,
        asset_title="期末前三天冲刺",
        matched_query_concepts=[
            SearchResultConceptMatch(
                concept_code="exam_sprint",
                concept_name="考前突击",
                relation_role="expresses",
                recommendation_text="旧的人工固定推荐语",
            )
        ],
        proof_name="短时间高效复习",
        evidence_name="期末前三天冲刺",
        reasons=["卖点内素材独有话术命中：期末前三天冲刺（100%）"],
        matched_content=["冲刺", "提分"],
    )

    assert "推荐这张「期末前三天冲刺」" in reason
    assert "主要表达“考前突击”" in reason
    assert "期末前三天冲刺" in reason
    assert "官网大图" in reason
    assert "数据图" in reason
    assert "旧的人工固定推荐语" not in reason


def _image(title: str) -> Image:
    return Image(
        title=title,
        file_name=f"{title}.png",
        storage_key=f"{title}.png",
        thumbnail_storage_key=f"thumb-{title}.jpg",
        media_type="image/png",
        size_bytes=100,
        uploader="designer",
        asset_role="primary",
        version_no=1,
        is_current=True,
        download_count=0,
        created_at=datetime.now(timezone.utc),
    )


class _ConfiguredProvider:
    configured = True


class _RecommendationAi:
    provider = _ConfiguredProvider()

    def recommend_search_result_reasons(self, **_kwargs):
        return ModelCallResult(
            SearchResultRecommendationReasonResult(
                reasons=[
                    {
                        "image_id": "image-1",
                        "reason": "模型说明：这张图承接了当前查询中的考前冲刺需求。",
                    },
                ]
            ),
            (
                {
                    "provider": "test-provider",
                    "model": "test-model",
                    "status": "ok",
                    "duration_ms": 8,
                    "fallback_index": 0,
                },
            ),
        )


def test_dynamic_recommendation_overlays_only_final_candidate_ids():
    image = _image("考前冲刺")
    image.id = "image-1"
    scorer = SearchScorer()
    result = scorer.build_scored_image(
        image,
        "考前冲刺",
        1.0,
        ["标题匹配"],
    )
    service = SearchResultRecommendationService(
        _RecommendationAi(),
        timeout_seconds=1,
    )

    enriched = asyncio.run(
        service.enrich(
            keyword="考前冲刺",
            understanding=None,
            hits=[SearchHit(image=image, score=1.0, reasons=("标题匹配",))],
            results=[result],
        )
    )

    assert enriched.value is not None
    assert enriched.value[0].result_recommendation_reason.startswith("模型说明")
    assert enriched.diagnostic.source == "result_recommendation_reason"
    assert enriched.diagnostic.status == "ok"
    assert enriched.diagnostic.attempts[0].layer == "第五层：动态推荐理由"


class _InvalidRecommendationAi:
    provider = _ConfiguredProvider()

    def recommend_search_result_reasons(self, **_kwargs):
        return SearchResultRecommendationReasonResult(
            reasons=[
                {
                    "image_id": "not-a-candidate",
                    "reason": "这条不能覆盖真实结果。",
                }
            ]
        )


def test_invalid_dynamic_recommendation_falls_back_as_failed_branch():
    image = _image("考前冲刺")
    image.id = "image-3"
    scorer = SearchScorer()
    result = scorer.build_scored_image(image, "考前冲刺", 1.0, ["标题匹配"])
    local_reason = result.result_recommendation_reason
    service = SearchResultRecommendationService(
        _InvalidRecommendationAi(),
        timeout_seconds=1,
    )

    enriched = asyncio.run(
        service.enrich(
            keyword="考前冲刺",
            understanding=None,
            hits=[SearchHit(image=image, score=1.0, reasons=("标题匹配",))],
            results=[result],
        )
    )

    assert enriched.value is not None
    assert enriched.value[0].result_recommendation_reason == local_reason
    assert enriched.diagnostic.status == "failed"


class _FailingRecommendationAi:
    class _Provider:
        configured = True

    provider = _Provider()

    def recommend_search_result_reasons(self, **_kwargs):
        raise RuntimeError("provider down")


def test_dynamic_recommendation_failure_keeps_local_reason():
    image = _image("考前冲刺")
    image.id = "image-2"
    scorer = SearchScorer()
    result = scorer.build_scored_image(
        image,
        "考前冲刺",
        1.0,
        ["标题匹配"],
    )
    local_reason = result.result_recommendation_reason
    service = SearchResultRecommendationService(
        _FailingRecommendationAi(),
        timeout_seconds=1,
    )

    enriched = asyncio.run(
        service.enrich(
            keyword="考前冲刺",
            understanding=None,
            hits=[SearchHit(image=image, score=1.0, reasons=("标题匹配",))],
            results=[result],
        )
    )

    assert enriched.value is not None
    assert enriched.value[0].result_recommendation_reason == local_reason
    assert enriched.diagnostic.status == "failed"
