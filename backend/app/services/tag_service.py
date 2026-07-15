from app.repositories.tag_repository import TagRepository
from app.schemas.tag import TagRead


class TagService:
    """Read-only six-system taxonomy view used by filters and concept management."""

    def __init__(self, db):
        self.repo = TagRepository(db)

    def list_tags(self) -> list[TagRead]:
        return [
            TagRead(
                id=tag.id,
                code=tag.code,
                name=tag.name,
                color=tag.color,
                parent_id=tag.parent_id,
                parent_name=parent_name,
                is_secondary=tag.is_secondary,
                node_type=tag.node_type,
                assignable=tag.assignable,
                status=tag.status,
                taxonomy_version=tag.taxonomy_version,
                sort_order=tag.sort_order,
                image_count=image_count,
            )
            for tag, parent_name, image_count in self.repo.list_with_counts()
        ]
