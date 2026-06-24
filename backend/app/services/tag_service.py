import uuid

from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.tag import Tag
from app.repositories.image_repository import ImageRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.tag import TagCreate, TagDeleteImpact, TagRead, TagUpdate
from app.services.unit_of_work import UnitOfWork


class TagService:
    def __init__(self, db):
        self.repo = TagRepository(db)
        self.images = ImageRepository(db)
        self.uow = UnitOfWork(db)

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

    def create(self, payload: TagCreate) -> TagRead:
        if payload.parent_id and not self.repo.get(payload.parent_id):
            raise AppError("parent_tag_not_found", "父标签不存在")
        try:
            values = payload.model_dump()
            values["code"] = f"custom_{uuid.uuid4().hex}"
            values["node_type"] = "custom"
            values["status"] = "active"
            values["is_secondary"] = bool(payload.parent_id)
            tag = self.repo.add(Tag(**values))
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise ConflictError("tag_name_exists", "同级标签名称已存在") from exc
        return TagRead.model_validate(tag)

    def update(self, tag_id: str, payload: TagUpdate) -> TagRead:
        tag = self._get(tag_id)
        values = payload.model_dump(exclude_unset=True)
        if tag.node_type != "custom" and {"name", "parent_id", "is_secondary"} & values.keys():
            raise AppError(
                "managed_taxonomy_node",
                "标准体系标签由权威目录管理，不能在界面中改名或移动",
                status_code=409,
            )
        parent_id = values.get("parent_id")
        if parent_id is not None:
            self._validate_parent(tag_id, parent_id)
        for key, value in values.items():
            setattr(tag, key, value)
        try:
            self.repo.save(tag)
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise ConflictError("tag_name_exists", "同级标签名称已存在") from exc
        return TagRead.model_validate(tag)

    def delete(self, tag_id: str) -> None:
        tag = self._get(tag_id)
        if tag.node_type != "custom":
            raise AppError(
                "managed_taxonomy_node",
                "标准体系标签不能直接删除，可在目录版本中停用或替代",
                status_code=409,
            )
        subtree_ids, image_ids = self._delete_scope(tag.id)
        if image_ids:
            raise ConflictError(
                "tag_in_use",
                "标签仍被图片使用，请先重新分配这些图片的标签",
            )
        for child_id in reversed(subtree_ids):
            child = self.repo.get(child_id)
            if child:
                self.repo.delete(child)
        self.uow.commit()

    def delete_impact(self, tag_id: str) -> TagDeleteImpact:
        tag = self._get(tag_id)
        subtree_ids, image_ids = self._delete_scope(tag.id)
        return TagDeleteImpact(
            tag_id=tag.id,
            tag_name=tag.name,
            subtree_tag_count=len(subtree_ids),
            direct_child_count=len(tag.children),
            affected_image_count=len(image_ids),
        )

    def _delete_scope(self, tag_id: str) -> tuple[list[str], list[str]]:
        subtree_ids = self.repo.descendant_ids(tag_id)
        image_ids = self.repo.image_ids_for_tags(subtree_ids)
        return subtree_ids, image_ids

    def _validate_parent(self, tag_id: str, parent_id: str) -> None:
        if parent_id == tag_id:
            raise AppError("tag_cycle", "标签不能成为自己的父标签")
        current = self.repo.get(parent_id)
        if not current:
            raise AppError("parent_tag_not_found", "父标签不存在")
        visited = {tag_id}
        while current:
            if current.id in visited:
                raise AppError("tag_cycle", "标签层级不能形成循环")
            visited.add(current.id)
            current = self.repo.get(current.parent_id) if current.parent_id else None

    def _get(self, tag_id: str) -> Tag:
        tag = self.repo.get(tag_id)
        if not tag:
            raise NotFoundError("tag_not_found", "标签不存在")
        return tag
