from app.domain.taxonomy_catalog import load_taxonomy_catalog

_catalog = load_taxonomy_catalog()

SYSTEMS = [(node.name, node.color) for node in _catalog.system_nodes]

CHILDREN = {
    system.name: [node.name for node in _catalog.children_of(system.code)]
    for system in _catalog.system_nodes
}

CHILD_COLORS = {
    system.name: (
        _catalog.children_of(system.code)[0].color
        if _catalog.children_of(system.code)
        else system.color
    )
    for system in _catalog.system_nodes
}
