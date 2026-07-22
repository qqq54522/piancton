from pathlib import Path

from app.domain.proof_points import (
    load_proof_point_catalog,
    query_proof_point_score,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCES = (
    PROJECT_ROOT / "skills" / "understand-image-search-intent" / "references"
)


def _reference(name: str) -> str:
    return (REFERENCES / name).read_text(encoding="utf-8")


def test_source_audit_keeps_original_high_information_details():
    school = _reference("sync-school.md")
    exam = _reference("sync-exam.md")
    cultivation = _reference("sync-cultivation.md")
    planning = _reference("sync-planning.md")
    self_study = _reference("sync-self-study.md")
    companion = _reference("sync-companion.md")

    assert "北京课改版等 13 个版本" in school
    assert "13 个版本\u201d清单来自本体系原图" in school
    assert "几分钟/短时间讲明白一个知识点" in school
    assert "课不长但一个点讲透" in school

    assert "小学\u201c思维培优\u201d" in exam
    assert "月考、期中、期末、中考、高考" in exam
    assert "拍题后不直接给最终答案" in exam
    assert "推送相关动画课" in exam

    assert "全国 31 套主流教材版本" in cultivation
    assert "同步跟进 + 拔高培优" in cultivation

    for input_name in (
        "学生学习周期",
        "在读年级",
        "具体提升学科",
        "主要学习目的",
        "针对的具体考试",
        "真实成绩水平",
        "教材版本",
        "计划学习时间",
    ):
        assert input_name in planning
    assert "5000 亿条学习互动" in planning
    assert "1340 亿条学习行为数据" in planning

    assert "3-5 道同考点变式练习" in self_study
    assert "手机、平板、电脑端查询复习" in self_study

    assert "本周观看课程名称/对应知识点" in companion
    assert "快进/倍速" in companion
    assert "答题正确率、高频错题和薄弱知识点" in companion


def test_every_system_records_green_branches_as_non_facts():
    for path in sorted(REFERENCES.glob("sync-*.md")):
        content = path.read_text(encoding="utf-8")
        assert "原图审计记录（2026-07-21）" in content
        assert "绿色" in content
        assert "不作为已有事实" in content


def test_source_details_are_available_to_runtime_proof_matching():
    points = load_proof_point_catalog().by_code

    assert query_proof_point_score(
        "月考期中期末一键划重点", points["pp_exam_focus_stage_review"]
    ) >= 0.93
    assert query_proof_point_score(
        "小学思维培优", points["pp_exam_focus_targeted_modules"]
    ) >= 0.93
    assert query_proof_point_score(
        "错题后再练几道", points["pp_selfstudy_error_variant_recommendation"]
    ) >= 0.93
    assert query_proof_point_score(
        "找那种几分钟就能讲明白一个知识点的图",
        points["pp_animation_pedagogy_design"],
    ) >= 0.86
    assert query_proof_point_score(
        "有没有一节课不长，但一个点能讲透的",
        points["pp_animation_pedagogy_design"],
    ) >= 0.86
