from app.ai.skill_loader import build_task_prompt
from app.domain.taxonomy_catalog import load_taxonomy_catalog


def test_catalog_has_stable_expected_shape():
    catalog = load_taxonomy_catalog()

    assert catalog.version == "2026.06.1"
    assert len(catalog.system_nodes) == 6
    assert len(catalog.image_label_nodes) == 16
    assert len(catalog.copy_points) == 30
    assert all(not node.assignable for node in catalog.system_nodes)
    assert all(node.assignable for node in catalog.image_label_nodes)


def test_every_copy_point_maps_to_existing_image_labels():
    catalog = load_taxonomy_catalog()
    node_by_code = catalog.node_by_code

    for point in catalog.copy_points:
        assert point.target_label_codes
        assert all(
            node_by_code[target_code].node_type == "image_label"
            for target_code in point.target_label_codes
        )


def test_prompt_is_built_from_versioned_catalog():
    prompt = build_task_prompt("image_content_analysis")

    assert "权威标签目录（版本 2026.06.1）" in prompt
    assert "`photo_guided_learning` / AI拍题精学" in prompt
    assert "模型只能返回以上目录中存在的稳定 code" in prompt
