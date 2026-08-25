from app.domain.query_negation import is_term_negated
from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import (
    BusinessConcept,
    ConceptSearchPhrase,
    ConceptSystemLink,
)
from app.models.image import Image
from app.models.tag import Tag
from app.repositories.business_concept_repository import BusinessConceptRepository
from app.services.intent_catalog_service import IntentCatalogService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_concept_routing_service import SearchConceptRoutingService
from app.services.search_models import SearchHit
from app.services.search_service import SearchService


def test_query_negation_only_flips_explicitly_rejected_terms():
    assert is_term_negated("不需要真人老师督学", "真人老师督学")
    assert is_term_negated("不需要真人老师督学", "真人老师")
    assert is_term_negated("无需整理错题", "整理错题")
    assert not is_term_negated("拍题后不要直接给答案", "拍题")
    assert not is_term_negated("AI拍照后即可为你点拨思路，不会立即出答案", "不会立即出答案")
    assert not is_term_negated("不需要错题本，要拍题讲解", "拍题讲解")
    assert not is_term_negated("不需要家长的真人老师督学", "真人老师督学")
    assert not is_term_negated("需要真人老师帮忙监督", "真人老师")


def test_shared_entry_word_is_exploratory_not_confirmed_multi():
    understanding = QueryUnderstandingService().understand_locally("AI拍照")

    assert understanding is not None
    assert understanding.query_type == "exploratory_business_intent_search"
    assert "你可能在找" in understanding.search_intent
    assert {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    } == {"AI错题本", "AI拍题精学", "极速预习复习", "AI私教答疑"}
    assert all(
        item.relation == "direct"
        for item in understanding.matched_business_concepts
    )


def test_shared_photo_entry_is_narrowed_by_context_specific_evidence():
    understanding = QueryUnderstandingService().understand_locally(
        "AI拍照后即可为你点拨思路，不会立即出答案"
    )

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI拍题精学"]


def test_textbook_version_alignment_composition_keeps_neighbor_boundaries():
    service = QueryUnderstandingService()

    textbook = service.understand_locally("销售想讲不同地区都能用")
    edition = service.understand_locally("北师大版")
    reform = service.understand_locally("新课标教材版本变化")
    rapid = service.understand_locally("拍课本课前快速预习")
    plan = service.understand_locally("按教材版本和成绩目标排每日任务")

    assert textbook is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in textbook.matched_business_concepts
    ] == ["同步校内"]
    assert [
        item.code for item in textbook.matched_proof_points
    ] == ["pp_textbook_version_coverage"]
    assert edition is not None
    assert [
        item.code for item in edition.matched_proof_points
    ] == ["pp_textbook_version_coverage"]
    assert reform is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in reform.matched_business_concepts
    ] == ["新课标新考法预测"]
    assert rapid is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in rapid.matched_business_concepts
    ] == ["极速预习复习"]
    assert plan is not None
    assert {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in plan.matched_business_concepts
    } == {"同步校内", "AI定制学习方案"}


def test_ai_personalized_learning_plan_composition_keeps_neighbor_boundaries():
    service = QueryUnderstandingService()

    plan = service.understand_locally("根据薄弱点推荐内容")
    tailored = service.understand_locally("哪个卖点能讲不是所有孩子学一套")
    course = service.understand_locally("有没有专属课程方案")
    focused = service.understand_locally("精准补弱")
    textbook = service.understand_locally("教材版本同步")
    human = service.understand_locally("真人老师根据学习情况持续督促")
    report = service.understand_locally("学习周报反馈薄弱点")

    for understanding in (plan, tailored, course):
        assert understanding is not None
        assert [
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        ] == ["AI定制学习方案"]
        assert [
            item.code for item in understanding.matched_proof_points
        ] == ["pp_planning_generated_schedule"]

    assert focused is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in focused.matched_business_concepts
    ] == ["专项培优"]
    assert textbook is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in textbook.matched_business_concepts
    ] == ["同步校内"]
    assert human is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in human.matched_business_concepts
    ] == ["真人老师督学"]
    assert report is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in report.matched_business_concepts
    ] == ["学情报告反馈"]


def test_photo_question_learning_composition_keeps_neighbor_boundaries():
    service = QueryUnderstandingService()

    entry = service.understand_locally("拍照讲题")
    value = service.understand_locally("有没有从搜答案到学会的卖点")
    proof = service.understand_locally("我想找拍题相关的证明点")
    rapid = service.understand_locally("拍课本课前快速预习")
    error_book = service.understand_locally("把练习册错题拍下来以后复习")
    transfer = service.understand_locally("拍题后再做同类题")

    assert entry is not None
    assert [
        item.code for item in entry.matched_proof_points
    ] == ["pp_selfstudy_photo_question_recognition"]
    assert value is not None
    assert [
        item.code for item in value.matched_proof_points
    ] == ["pp_selfstudy_photo_socratic_guidance"]
    assert proof is not None
    assert [
        item.code for item in proof.matched_proof_points
    ] == ["pp_selfstudy_photo_question_recognition"]
    assert rapid is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in rapid.matched_business_concepts
    ] == ["极速预习复习"]
    assert error_book is not None
    assert "AI错题本" in {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in error_book.matched_business_concepts
    }
    assert transfer is not None
    assert "举一反三" in {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in transfer.matched_business_concepts
    }


def test_socratic_thinking_coach_composition_targets_guidance_proof_point():
    service = QueryUnderstandingService()

    samples = (
        "AI思维教练",
        "苏格拉底式教学",
        "AI追问",
        "让孩子自己想出答案",
        "有没有体现“启发而不是灌输”的图",
        "想找“会提问的AI老师”",
        "有没有关于连续追问的证明点",
    )

    for query in samples:
        understanding = service.understand_locally(query)

        assert understanding is not None, query
        assert understanding.query_type == "business_intent_search"
        assert [
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        ] == ["AI拍题精学"]
        assert [
            item.code for item in understanding.matched_proof_points
        ] == ["pp_selfstudy_photo_socratic_guidance"]

    tutor = service.understand_locally("随时问AI老师一道知识点")

    assert tutor is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in tutor.matched_business_concepts
    ] == ["AI私教答疑"]


def test_remaining_business_compositions_keep_neighbor_boundaries():
    service = QueryUnderstandingService()

    animation = service.understand_locally("老师讲太快孩子听不懂想用动画讲明白")
    visual = service.understand_locally("把看不见的知识变成动画")
    quiz = service.understand_locally("孩子说听懂了想马上看看会不会")
    tutor = service.understand_locally("孩子晚上写作业卡住了家里没人会讲")
    error_archive = service.understand_locally("练习册错题拍照上传")
    error_variant = service.understand_locally("错题后再练同类题")

    assert animation is not None
    assert [
        item.code for item in animation.matched_proof_points
    ] == ["pp_animation_pedagogy_design"]
    assert visual is not None
    assert [
        item.code for item in visual.matched_proof_points
    ] == ["pp_subject_animation_visualization"]
    scale = service.understand_locally("孩子班上，大概率就有同学在用")

    assert scale is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in scale.matched_business_concepts
    ] == ["动画精讲"]
    assert [
        item.code for item in scale.matched_proof_points
    ] == ["pp_animation_scale_data"]
    assert [
        item.code for item in scale.matched_evidence_points
    ] == ["ep_school_animation_scale_numbers"]

    assert quiz is not None
    assert [
        item.code for item in quiz.matched_proof_points
    ] == ["pp_learn_practice_loop"]
    assert tutor is not None
    assert [
        item.code for item in tutor.matched_proof_points
    ] == ["pp_selfstudy_tutor_interactive_qa"]
    assert error_archive is not None
    assert [
        item.code for item in error_archive.matched_proof_points
    ] == ["pp_selfstudy_error_photo_capture"]
    assert error_variant is not None
    assert [
        item.code for item in error_variant.matched_proof_points
    ] == ["pp_selfstudy_error_variant_recommendation"]

    exam_review = service.understand_locally("短时间高效复习")
    socratic = service.understand_locally("想找会提问的AI老师")
    report = service.understand_locally("每周学习报告汇总时长和正确率给家长")
    frequent_errors = service.understand_locally("大家容易错的高频错题集中练")
    transfer = service.understand_locally("讲完当前题再做同类题训练")

    assert exam_review is not None
    assert [
        item.code for item in exam_review.matched_proof_points
    ] == ["pp_exam_focus_stage_review"]
    assert socratic is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in socratic.matched_business_concepts
    ] == ["AI拍题精学"]
    assert report is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in report.matched_business_concepts
    ] == ["学情报告反馈"]
    assert frequent_errors is not None
    assert [
        item.code for item in frequent_errors.matched_proof_points
    ] == ["pp_exam_focus_high_frequency_errors"]
    assert transfer is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in transfer.matched_business_concepts
    ] == ["举一反三"]


def test_second_remaining_business_compositions_keep_neighbor_boundaries():
    service = QueryUnderstandingService()

    expected_proofs = {
        "新中考会怎么考": ("新课标新考法预测", "pp_exam_reform_trend_alignment"),
        "跨学科题怎么练": ("新课标新考法预测", "pp_exam_new_format_course_practice"),
        "理解原理换题也会": ("举一反三", "pp_exam_transfer_principle_first"),
        "讲完题再做同类题": ("举一反三", "pp_exam_transfer_variant_practice"),
        "命题专家设计课程": ("专家规划", "pp_cultivation_expert_team_credentials"),
        "长期学习路径设计": ("专家规划", "pp_cultivation_expert_path_design"),
        "小升初衔接课": ("学段衔接", "pp_cultivation_stage_bridge_courses"),
        "小初高一体化": ("学段衔接", "pp_cultivation_stage_full_cycle_coverage"),
        "一题多解": ("万能解法", "pp_cultivation_method_multiple_paths"),
        "建立理科思维": ("万能解法", "pp_cultivation_method_transfer_foundation"),
        "真人老师分析问题": ("真人老师督学", "pp_companion_teacher_diagnosis_plan"),
        "真人老师每天提醒": ("真人老师督学", "pp_companion_teacher_follow_up"),
        "学习周报看学了什么学了多久": ("学情报告反馈", "pp_companion_report_core_metrics"),
        "快进倍速记录": ("学情报告反馈", "pp_companion_report_behavior_signals"),
        "微信里看学习周报": ("学情报告反馈", "pp_companion_report_parent_delivery"),
    }

    for query, (concept, proof_point) in expected_proofs.items():
        understanding = service.understand_locally(query)

        assert understanding is not None, query
        assert understanding.query_type == "business_intent_search"
        assert [
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        ] == [concept]
        assert [
            item.code for item in understanding.matched_proof_points
        ] == [proof_point]

    boundaries = {
        "教材版本同步": "同步校内",
        "学习路径自动规划": "AI定制学习方案",
        "讲完当前题再做同类题训练": "举一反三",
        "同一道题不同方法": "万能解法",
        "高频错题薄弱知识点周报": "学情报告反馈",
        "个人错题练会一类题": "AI错题本",
    }
    for query, concept in boundaries.items():
        understanding = service.understand_locally(query)

        assert understanding is not None, query
        assert [
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        ] == [concept]

    ai_only = service.understand_locally("不要真人老师，只要 AI 随时回答问题")

    assert ai_only is not None
    assert "同步伴学体系 > 真人老师督学" in ai_only.excluded_concepts
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in ai_only.matched_business_concepts
    ] == ["AI私教答疑"]


def test_rapid_preview_before_class_composition_keeps_neighbor_boundaries():
    service = QueryUnderstandingService()

    samples = (
        "课前快速过知识点",
        "带着问题进课堂",
        "有什么功能适合每天晚上用",
        "想突出上课之前先建立认知",
        "哪个卖点适合讲“提前知道课堂重点”",
        "想讲短时间完成预习",
    )

    for query in samples:
        understanding = service.understand_locally(query)

        assert understanding is not None, query
        assert understanding.query_type == "business_intent_search"
        assert [
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        ] == ["极速预习复习"]
        assert [
            item.code for item in understanding.matched_proof_points
        ] == ["pp_selfstudy_preview_dual_entry"]

    exam_stage = service.understand_locally("月考复习")
    textbook = service.understand_locally("教材版本同步")
    plan = service.understand_locally("学习计划自动生成")
    photo = service.understand_locally("拍题讲解")
    error_book = service.understand_locally("练习册错题以后复习")

    assert exam_stage is not None
    assert [
        item.code for item in exam_stage.matched_proof_points
    ] == ["pp_exam_focus_stage_review"]
    assert textbook is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in textbook.matched_business_concepts
    ] == ["同步校内"]
    assert plan is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in plan.matched_business_concepts
    ] == ["AI定制学习方案"]
    assert photo is not None
    assert [
        item.code for item in photo.matched_proof_points
    ] == ["pp_selfstudy_photo_question_recognition"]
    assert error_book is not None
    assert "AI错题本" in {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in error_book.matched_business_concepts
    }


def test_rapid_review_after_class_composition_keeps_neighbor_boundaries():
    service = QueryUnderstandingService()

    samples = (
        "课后复习",
        "当天知识当天复习",
        "快速查漏补缺",
        "知识点快速回忆",
        "学过内容重新过一遍",
        "日常快速复习",
        "当天学当天复习",
        "有没有体现碎片时间学习的图",
        "哪个功能可以讲“花很少时间复习”",
        "有没有“快速回顾重点”的卖点",
    )

    for query in samples:
        understanding = service.understand_locally(query)

        assert understanding is not None, query
        assert understanding.query_type == "business_intent_search"
        assert [
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        ] == ["极速预习复习"]
        assert [
            item.code for item in understanding.matched_proof_points
        ] == ["pp_selfstudy_preview_dual_entry"]
        assert [
            item.code for item in understanding.matched_evidence_points
        ] == ["ep_selfstudy_fast_review"]

    exam_stage = service.understand_locally("月考复习")
    tomorrow_exam = service.understand_locally("明天月考快速复习")
    final_sprint = service.understand_locally("期末前三天冲刺")
    textbook = service.understand_locally("教材版本同步")
    plan = service.understand_locally("学习计划自动生成")
    photo = service.understand_locally("拍题讲解")
    error_book = service.understand_locally("练习册错题以后复习")

    assert exam_stage is not None
    assert [
        item.code for item in exam_stage.matched_proof_points
    ] == ["pp_exam_focus_stage_review"]
    for understanding in (tomorrow_exam, final_sprint):
        assert understanding is not None
        assert [
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        ] == ["专项培优"]
        assert [
            item.code for item in understanding.matched_proof_points
        ] == ["pp_exam_focus_stage_review"]
    assert textbook is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in textbook.matched_business_concepts
    ] == ["同步校内"]
    assert plan is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in plan.matched_business_concepts
    ] == ["AI定制学习方案"]
    assert photo is not None
    assert [
        item.code for item in photo.matched_proof_points
    ] == ["pp_selfstudy_photo_question_recognition"]
    assert error_book is not None
    assert "AI错题本" in {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in error_book.matched_business_concepts
    }


def test_objectless_photo_explain_combination_stays_exploratory():
    # D079：拍照入口没有拍摄对象、只有讲解目的时，保持拍题精学/极速预习复习
    # 探索型组合，不硬选唯一卖点，也不落入全库兜底。
    for query in (
        "拍一下，AI马上给你讲解",
        "一键拍照，AI 即刻为你提供思路点拨与详细解析，拒绝直接给答案",
    ):
        understanding = QueryUnderstandingService().understand_locally(query)

        assert understanding is not None, query
        assert understanding.query_type == "exploratory_business_intent_search"
        assert "你可能在找" in understanding.search_intent
        assert {
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        } == {"AI拍题精学", "极速预习复习"}
        assert all(
            item.relation == "direct" and item.weight >= 0.85
            for item in understanding.matched_business_concepts
        )


def test_animation_course_quality_phrase_is_a_trusted_animation_intent():
    understanding = QueryUnderstandingService().understand_locally("体现动画课很好")

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "动画精讲"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["动画精讲"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.85


def test_photo_guided_flow_keeps_fallback_animation_subordinate():
    query = "孩子拍一拍不会的题，AI先问步骤、讲思路，不懂再推对应知识点动画课，学会为止"
    understanding = QueryUnderstandingService().understand_locally(query)

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "AI拍题精学"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI拍题精学"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.85


def test_learning_outcome_visibility_keeps_report_and_quiz_as_shared_candidates():
    understanding = QueryUnderstandingService().understand_locally(
        "随时能看到学习成果"
    )

    assert understanding is not None
    assert understanding.query_type == "exploratory_business_intent_search"
    assert {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    } == {"课后小测", "学情报告反馈"}
    assert all(
        item.relation == "direct" and item.weight >= 0.85
        for item in understanding.matched_business_concepts
    )


def test_level_matched_virtual_class_is_trusted_ai_learning_plan():
    query = "动态组建一个与你水平相匹配的虚拟班级，安排个性化的学习节奏与内容"
    understanding = QueryUnderstandingService().understand_locally(query)

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "AI定制学习方案"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI定制学习方案"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.85


def test_heuristic_questioning_phrase_is_a_trusted_photo_guided_intent():
    # D078：该话术是拍题精学“苏格拉底式提问”的方法论表达，覆盖 D072 的旧归属。
    understanding = QueryUnderstandingService().understand_locally(
        "通过启发式提问，还原思考过程，帮你从‘解一题’到‘通一类’"
    )

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "AI拍题精学"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI拍题精学"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.85


def test_explicit_ai_tutor_outweighs_generic_weakness_neighbor_terms():
    understanding = QueryUnderstandingService().understand_locally(
        "量身打造一对一AI私教，24小时答疑解惑，精准定位知识薄弱点"
    )

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "AI私教答疑"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI私教答疑"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.95


def test_weak_ambiguous_entry_keeps_equal_neighboring_candidates():
    understanding = QueryUnderstandingService().understand_locally("复习")

    assert understanding is not None
    assert understanding.query_type == "ambiguous_business_intent_search"
    assert {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    } == {"极速预习复习", "AI错题本"}
    assert all(
        item.relation == "related"
        for item in understanding.matched_business_concepts
    )


def test_exam_stage_composition_does_not_capture_daily_or_reform_review():
    service = QueryUnderstandingService()

    daily = service.understand_locally("课后短时间高效复习今天的笔记")
    reform = service.understand_locally("新中考考试前快速练新题型")

    assert daily is not None
    assert all(
        not item.concept.endswith("> 专项培优")
        for item in daily.matched_business_concepts
    )
    assert reform is not None
    assert all(
        not item.concept.endswith("> 专项培优")
        for item in reform.matched_business_concepts
    )


def test_targeted_module_composition_keeps_neighbor_boundaries():
    service = QueryUnderstandingService()

    targeted = service.understand_locally("薄弱题型")
    frequent_errors = service.understand_locally("大家容易错的高频错题集中练")
    transfer = service.understand_locally("讲完当前题再做同类题训练")
    personal_errors = service.understand_locally("个人错题针对性训练")

    assert targeted is not None
    assert [
        item.code for item in targeted.matched_proof_points
    ] == ["pp_exam_focus_targeted_modules"]
    assert frequent_errors is not None
    assert [
        item.code for item in frequent_errors.matched_proof_points
    ] == ["pp_exam_focus_high_frequency_errors"]
    assert transfer is not None
    assert all(
        not item.concept.endswith("> 专项培优")
        for item in transfer.matched_business_concepts
    )
    assert personal_errors is not None
    assert all(
        not item.concept.endswith("> 专项培优")
        for item in personal_errors.matched_business_concepts
    )


def test_difficulty_upgrade_composition_keeps_neighbor_boundaries():
    service = QueryUnderstandingService()

    difficulty = service.understand_locally("从90分往满分冲")
    high_order = service.understand_locally("哪个卖点能体现不是只教基础")
    exam_stage = service.understand_locally("期末冲刺高分")
    targeted = service.understand_locally("精准补弱")
    transfer = service.understand_locally("讲完当前题再做同类题训练")

    assert difficulty is not None
    assert [
        item.code for item in difficulty.matched_proof_points
    ] == ["pp_exam_focus_targeted_modules"]
    assert high_order is not None
    assert [
        item.code for item in high_order.matched_proof_points
    ] == ["pp_exam_focus_targeted_modules"]
    assert exam_stage is not None
    assert [
        item.code for item in exam_stage.matched_proof_points
    ] == ["pp_exam_focus_stage_review"]
    assert targeted is not None
    assert [
        item.code for item in targeted.matched_proof_points
    ] == ["pp_exam_focus_targeted_modules"]
    assert transfer is not None
    assert all(
        not item.concept.endswith("> 专项培优")
        for item in transfer.matched_business_concepts
    )


def test_pure_negative_query_produces_excluded_concepts_only():
    understanding = QueryUnderstandingService().understand_locally("不需要真人老师督学")

    assert understanding is not None
    assert understanding.query_type == "no_reliable_intent_search"
    assert understanding.matched_business_concepts == []
    assert "同步伴学体系 > 真人老师督学" in understanding.excluded_concepts


def test_negated_concept_is_excluded_while_positive_concept_stays():
    understanding = QueryUnderstandingService().understand_locally(
        "不需要真人老师督学，想看学情报告"
    )

    assert understanding is not None
    assert understanding.normalized_query == "学情报告反馈"
    assert "同步伴学体系 > 真人老师督学" in understanding.excluded_concepts
    matched_names = [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ]
    assert "真人老师督学" not in matched_names


def test_negation_phrase_in_seed_vocabulary_still_matches_positively():
    understanding = QueryUnderstandingService().understand_locally("拍题后不要直接给答案")

    assert understanding is not None
    assert understanding.normalized_query == "AI拍题精学"
    assert understanding.query_type in {
        "business_intent_search",
        "multi_business_intent_search",
        "exploratory_business_intent_search",
    }


def _concept_hit(code: str, name: str, relation_role: str = "expresses") -> SearchHit:
    concept = BusinessConcept(code=code, name=name)
    image = Image(
        title=f"{name}素材",
        file_name=f"{code}.png",
        storage_key=f"{code}.png",
        thumbnail_storage_key=f"{code}-thumb.png",
        media_type="image/png",
        size_bytes=100,
        uploader="designer",
        asset_group=AssetGroup(
            title=f"{name}素材组",
            created_by="designer",
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role=relation_role,
                    origin="manual",
                    review_status="accepted",
                )
            ],
        ),
    )
    return SearchHit(image=image, score=0.9, reasons=("测试",))


def test_routing_drops_assets_expressing_query_excluded_concepts():
    excluded_hit = _concept_hit("human_teacher_supervision", "真人老师督学")
    kept_hit = _concept_hit("learning_report", "学情报告反馈")
    understanding = QueryUnderstandingService().understand_locally(
        "不需要真人老师督学，想看学情报告"
    )
    assert understanding is not None

    outcome = SearchConceptRoutingService().route(
        [excluded_hit, kept_hit],
        [],
        keyword="不需要真人老师督学，想看学情报告",
        understanding=understanding,
    )

    titles = [hit.image.title for hit in outcome.hits]
    assert "真人老师督学素材" not in titles
    assert "学情报告反馈素材" in titles


def test_runtime_catalog_prefers_database_names_and_reviewed_phrases(db_factory):
    with db_factory() as db:
        system = Tag(
            code="sync_school",
            name="同步校内体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        concept = BusinessConcept(
            code="animation_explanation",
            name="动画讲解精学",
            system_links=[ConceptSystemLink(system_tag=system)],
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="孩子看动画就能听懂",
                    phrase_type="pain",
                    origin="manual",
                    review_status="accepted",
                ),
                ConceptSearchPhrase(
                    phrase="动画精讲",
                    phrase_type="official",
                    origin="source_document",
                    review_status="rejected",
                ),
            ],
        )
        new_concept = BusinessConcept(
            code="parent_worry_free",
            name="家长省心陪学",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="家长不用天天盯着孩子",
                    phrase_type="pain",
                    origin="manual",
                    review_status="accepted",
                ),
                ConceptSearchPhrase(
                    phrase="星图",
                    phrase_type="alias",
                    origin="manual",
                    review_status="accepted",
                ),
            ],
        )
        db.add_all([system, concept, new_concept])
        db.commit()

        catalog = IntentCatalogService(BusinessConceptRepository(db)).runtime_catalog()

    by_code = {intent.code: intent for intent in catalog.intents}
    merged = by_code["animation_explanation"]
    assert merged.name == "动画讲解精学"
    assert merged.display_name == "同步校内体系 > 动画讲解精学"
    assert "孩子看动画就能听懂" in merged.pain_points
    assert "动画精讲" not in merged.phrases

    added = by_code["parent_worry_free"]
    assert added.name == "家长省心陪学"
    assert "家长不用天天盯着孩子" in added.pain_points
    assert "星图" in added.exact_only_phrases

    service = QueryUnderstandingService(runtime_catalog=catalog)
    exact = service.understand_locally("星图")
    assert exact is not None
    assert exact.normalized_query == "家长省心陪学"
    assert exact.matched_business_concepts[0].relation == "direct"

    sentence = service.understand_locally("我想找星图风格的素材")
    assert sentence is None or all(
        "家长省心陪学" not in item.concept
        for item in sentence.matched_business_concepts
    )


def test_runtime_catalog_prefers_core_system_over_support_order(db_factory):
    with db_factory() as db:
        support_system = Tag(
            code="sync_exam",
            name="同步考点体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        core_system = Tag(
            code="sync_self_study",
            name="同步自学体系",
            color="#22C55E",
            node_type="system",
            assignable=False,
            status="active",
        )
        concept = BusinessConcept(
            code="ai_error_book",
            name="AI错题本",
            system_links=[
                ConceptSystemLink(
                    system_tag=support_system,
                    role="support",
                ),
                ConceptSystemLink(
                    system_tag=core_system,
                    role="core",
                ),
            ],
        )
        db.add_all([support_system, core_system, concept])
        db.commit()

        catalog = IntentCatalogService(BusinessConceptRepository(db)).runtime_catalog()

    merged = next(item for item in catalog.intents if item.code == "ai_error_book")
    assert merged.display_name == "同步自学体系 > AI错题本"


def test_static_exact_mode_is_not_upgraded_by_database_seed_phrase(db_factory):
    with db_factory() as db:
        system = Tag(
            code="sync_school",
            name="同步校内体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        concept = BusinessConcept(
            code="instant_quiz",
            name="课后小测",
            system_links=[
                ConceptSystemLink(system_tag=system, role="core"),
            ],
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="正确率",
                    phrase_type="official",
                    origin="source_document",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([system, concept])
        db.commit()

        catalog = IntentCatalogService(BusinessConceptRepository(db)).runtime_catalog()

    merged = next(item for item in catalog.intents if item.code == "instant_quiz")
    assert "正确率" in merged.exact_only_phrases
    assert "正确率" not in merged.phrases

    understanding = QueryUnderstandingService(runtime_catalog=catalog).understand_locally(
        "每周学习报告汇总时长、正确率和薄弱点给家长"
    )
    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["学情报告反馈"]


def test_rejected_old_method_phrase_does_not_override_transfer_intent(db_factory):
    with db_factory() as db:
        concept = BusinessConcept(
            code="universal_method",
            name="万能解法",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="一道题学会一类题",
                    phrase_type="official",
                    origin="source_document",
                    review_status="rejected",
                )
            ],
        )
        db.add(concept)
        db.commit()

        catalog = IntentCatalogService(BusinessConceptRepository(db)).runtime_catalog()

    understanding = QueryUnderstandingService(runtime_catalog=catalog).understand_locally(
        "一道题学会一类题"
    )
    assert understanding is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["举一反三"]


def test_search_service_understands_database_only_concepts(db_factory):
    with db_factory() as db:
        concept = BusinessConcept(
            code="parent_worry_free",
            name="家长省心陪学",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="家长不用天天盯着孩子",
                    phrase_type="pain",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add(concept)
        db.commit()

        service = SearchService(db)
        understanding = service.query_understanding.understand_locally(
            "家长不用天天盯着孩子"
        )

    assert understanding is not None
    assert understanding.normalized_query == "家长省心陪学"
    assert understanding.matched_business_concepts[0].relation == "direct"
