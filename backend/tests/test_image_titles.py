from app.domain.image_titles import (
    MAX_IMAGE_TITLE_LENGTH,
    allocate_unique_image_title,
    clean_image_title,
    title_namespace,
)


def test_keeps_a_free_user_defined_title_unchanged():
    assert allocate_unique_image_title("私教答疑", ["AI私教"]) == "私教答疑"


def test_duplicate_titles_continue_the_existing_three_digit_sequence():
    existing = ["AI私教", "AI私教001", "AI私教002"]
    assert allocate_unique_image_title("AI私教", existing) == "AI私教003"
    assert allocate_unique_image_title("AI私教001", existing) == "AI私教003"


def test_title_comparison_is_trimmed_and_case_insensitive():
    assert clean_image_title("  AI Tutor  ") == "AI Tutor"
    assert allocate_unique_image_title("ai tutor", ["AI TUTOR"]) == "ai tutor001"


def test_long_duplicate_titles_leave_room_for_the_suffix():
    requested = "名" * MAX_IMAGE_TITLE_LENGTH
    resolved = allocate_unique_image_title(requested, [requested])
    assert len(resolved) == MAX_IMAGE_TITLE_LENGTH
    assert resolved.endswith("001")
    assert title_namespace("AI私教001") == "AI私教"


def test_a_natural_year_suffix_is_not_mistaken_for_an_auto_number():
    assert allocate_unique_image_title("课程2026", ["课程2026"]) == "课程2026001"
