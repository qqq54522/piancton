from app.api.v1.business_facets import get_business_facets


def _proof_names(catalog, concept_code: str) -> list[str]:
    return [
        item.name
        for item in catalog.proof_points
        if item.concept_code == concept_code
    ]


def test_business_facets_return_green_evidence_points_and_hide_internal_proofs():
    catalog = get_business_facets(None)  # type: ignore[arg-type]

    assert any(
        item.code == "ep_cultivation_transition_course"
        for item in catalog.evidence_points
    )
    assert all(
        item.proof_point_code in {proof.code for proof in catalog.proof_points}
        for item in catalog.evidence_points
    )
    assert _proof_names(catalog, "ai_learning_plan") == [
        "多维个人条件输入",
        "专属路径与每日任务结果",
    ]
    assert _proof_names(catalog, "photo_guided_learning") == [
        "AI拍题精学",
        "苏格拉底式提问",
        "第三方测评",
    ]
    assert "学习数据与课程规模基础" not in {
        item.name for item in catalog.proof_points
    }
    assert "AI 规划的公开方法论说明" not in {
        item.name for item in catalog.proof_points
    }
