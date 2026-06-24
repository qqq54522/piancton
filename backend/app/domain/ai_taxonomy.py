from app.domain.taxonomy_catalog import load_taxonomy_catalog

_catalog = load_taxonomy_catalog()
_node_by_code = _catalog.node_by_code

SECONDARY_LABEL_CATALOG = {
    (_node_by_code[node.parent_code].name, node.name)
    for node in _catalog.image_label_nodes
    if node.parent_code
}

SECONDARY_LABEL_CODES = {node.code for node in _catalog.image_label_nodes}

CONTENT_TAG_DIMENSIONS = {
    "人物",
    "场景",
    "物体",
    "动作",
    "情绪",
    "文字",
    "视觉风格",
    "颜色",
    "构图",
    "产品功能",
    "业务卖点",
    "其他",
}
