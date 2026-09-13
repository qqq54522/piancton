from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone

from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.asset import AssetGroup
from app.models.asset_collection import (
    AssetCollectionBoard,
    AssetCollectionBoardItem,
    UserAssetLike,
)
from app.models.image import Image
from app.models.usage import AiSearchBehaviorEvent, UserUsageEvent
from app.models.user import User
from app.repositories.ai_search_behavior_repository import AiSearchBehaviorRepository
from app.repositories.asset_collection_repository import AssetCollectionRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.image_repository import ImageRepository
from app.repositories.usage_repository import UsageEventRepository
from app.schemas.asset_collection import (
    AssetCollectionBoardListResponse,
    AssetCollectionBoardRead,
    AssetCollectionMembership,
    AssetCollectionSummary,
    AssetSaveContext,
    SavedAssetListResponse,
    SavedAssetRead,
)
from app.services.serializers import image_to_read
from app.services.unit_of_work import UnitOfWork


class AssetCollectionService:
    def __init__(self, db):
        self.collections = AssetCollectionRepository(db)
        self.assets = AssetRepository(db)
        self.images = ImageRepository(db)
        self.events = UsageEventRepository(db)
        self.behavior_events = AiSearchBehaviorRepository(db)
        self.uow = UnitOfWork(db)

    def summary(self, user: User) -> AssetCollectionSummary:
        boards = self.collections.list_boards(user.id)
        liked_ids = self.collections.list_like_ids(user.id)
        return AssetCollectionSummary(
            liked_asset_group_ids=liked_ids,
            liked_count=len(liked_ids),
            boards=[self._board_read(board) for board in boards],
        )

    def membership(self, user: User, asset_group_id: str) -> AssetCollectionMembership:
        return AssetCollectionMembership(
            asset_group_id=asset_group_id,
            liked=self.collections.get_like(user.id, asset_group_id) is not None,
            board_ids=self.collections.board_ids_for_asset(user.id, asset_group_id),
        )

    def list_likes(
        self,
        user: User,
        *,
        cursor: str | None,
        limit: int,
    ) -> SavedAssetListResponse:
        cursor_at, cursor_id = _decode_cursor(cursor)
        rows = self.collections.list_likes(
            user.id, cursor_at=cursor_at, cursor_id=cursor_id, limit=limit
        )
        return self._saved_list(rows, limit=limit)

    def like(
        self, user: User, asset_group_id: str, context: AssetSaveContext
    ) -> AssetCollectionMembership:
        group, image = self._resolve_asset(asset_group_id, context.image_id)
        if self.collections.get_like(user.id, asset_group_id) is not None:
            return self.membership(user, asset_group_id)
        was_saved = self.collections.is_saved_anywhere(user.id, asset_group_id)
        self.collections.add_like(
            UserAssetLike(
                user_id=user.id,
                asset_group_id=asset_group_id,
                preferred_image_id=image.id,
            )
        )
        self._record_change(
            user,
            group,
            image,
            action="like_image",
            behavior_type=None if was_saved else "favorite",
            context=context,
        )
        self.uow.commit()
        return self.membership(user, asset_group_id)

    def unlike(
        self, user: User, asset_group_id: str, context: AssetSaveContext
    ) -> AssetCollectionMembership:
        row = self.collections.get_like(user.id, asset_group_id)
        if row is None:
            return self.membership(user, asset_group_id)
        group, image = self._resolve_asset(
            asset_group_id,
            row.preferred_image_id,
            require_published=False,
            strict_preferred=False,
        )
        self.collections.delete_like(row)
        remains_saved = self.collections.is_saved_anywhere(user.id, asset_group_id)
        self._record_change(
            user,
            group,
            image,
            action="unlike_image",
            behavior_type=None if remains_saved else "unfavorite",
            context=context,
        )
        self.uow.commit()
        return self.membership(user, asset_group_id)

    def list_boards(self, user: User) -> AssetCollectionBoardListResponse:
        return AssetCollectionBoardListResponse(
            items=[self._board_read(board) for board in self.collections.list_boards(user.id)]
        )

    def create_board(self, user: User, name: str) -> AssetCollectionBoardRead:
        cleaned, normalized = _normalize_board_name(name)
        if self.collections.board_name_exists(user.id, normalized):
            raise ConflictError("board_name_exists", "已经有同名画板")
        board = self.collections.add_board(
            AssetCollectionBoard(user_id=user.id, name=cleaned, normalized_name=normalized)
        )
        self.uow.commit()
        return self._board_read(board)

    def rename_board(self, user: User, board_id: str, name: str) -> AssetCollectionBoardRead:
        board = self._get_board(user.id, board_id)
        cleaned, normalized = _normalize_board_name(name)
        if self.collections.board_name_exists(user.id, normalized, exclude_id=board.id):
            raise ConflictError("board_name_exists", "已经有同名画板")
        board.name = cleaned
        board.normalized_name = normalized
        board.updated_at = datetime.now(timezone.utc)
        self.collections.save_board(board)
        self.uow.commit()
        return self._board_read(board)

    def delete_board(self, user: User, board_id: str) -> None:
        board = self._get_board(user.id, board_id)
        removed = list(board.items)
        for item in removed:
            if self.collections.is_saved_anywhere(
                user.id, item.asset_group_id, exclude_board_id=board.id
            ):
                continue
            group, image = self._resolve_asset(
                item.asset_group_id,
                item.preferred_image_id,
                require_published=False,
                strict_preferred=False,
            )
            self._record_change(
                user,
                group,
                image,
                action="remove_from_board",
                behavior_type="unfavorite",
                context=AssetSaveContext(source="my_collections"),
                board_id=board.id,
            )
        self.collections.delete_board(board)
        self.uow.commit()

    def list_board_items(
        self,
        user: User,
        board_id: str,
        *,
        cursor: str | None,
        limit: int,
    ) -> SavedAssetListResponse:
        self._get_board(user.id, board_id)
        cursor_at, cursor_id = _decode_cursor(cursor)
        rows = self.collections.list_board_items(
            board_id, cursor_at=cursor_at, cursor_id=cursor_id, limit=limit
        )
        return self._saved_list(rows, limit=limit)

    def add_to_board(
        self,
        user: User,
        board_id: str,
        asset_group_id: str,
        context: AssetSaveContext,
    ) -> AssetCollectionMembership:
        board = self._get_board(user.id, board_id)
        group, image = self._resolve_asset(asset_group_id, context.image_id)
        if self.collections.get_board_item(board.id, asset_group_id) is not None:
            return self.membership(user, asset_group_id)
        was_saved = self.collections.is_saved_anywhere(user.id, asset_group_id)
        self.collections.add_board_item(
            AssetCollectionBoardItem(
                board_id=board.id,
                asset_group_id=asset_group_id,
                preferred_image_id=image.id,
            )
        )
        board.updated_at = datetime.now(timezone.utc)
        self.collections.save_board(board)
        self._record_change(
            user,
            group,
            image,
            action="add_to_board",
            behavior_type=None if was_saved else "favorite",
            context=context,
            board_id=board.id,
        )
        self.uow.commit()
        return self.membership(user, asset_group_id)

    def remove_from_board(
        self,
        user: User,
        board_id: str,
        asset_group_id: str,
        context: AssetSaveContext,
    ) -> AssetCollectionMembership:
        board = self._get_board(user.id, board_id)
        row = self.collections.get_board_item(board.id, asset_group_id)
        if row is None:
            return self.membership(user, asset_group_id)
        group, image = self._resolve_asset(
            asset_group_id,
            row.preferred_image_id,
            require_published=False,
            strict_preferred=False,
        )
        self.collections.delete_board_item(row)
        board.updated_at = datetime.now(timezone.utc)
        self.collections.save_board(board)
        remains_saved = self.collections.is_saved_anywhere(user.id, asset_group_id)
        self._record_change(
            user,
            group,
            image,
            action="remove_from_board",
            behavior_type=None if remains_saved else "unfavorite",
            context=context,
            board_id=board.id,
        )
        self.uow.commit()
        return self.membership(user, asset_group_id)

    def _saved_list(self, rows: list, *, limit: int) -> SavedAssetListResponse:
        has_more = len(rows) > limit
        visible = rows[:limit]
        items: list[SavedAssetRead] = []
        for row in visible:
            group = row.asset_group
            image = self._display_image(group, row.preferred_image_id)
            if image is None or group.publish_status != "published":
                continue
            items.append(
                SavedAssetRead(
                    asset_group_id=group.id,
                    title=group.title,
                    saved_at=row.created_at,
                    image=image_to_read(image),
                )
            )
        next_cursor = None
        if has_more and visible:
            last = visible[-1]
            next_cursor = _encode_cursor(last.created_at, last.asset_group_id)
        return SavedAssetListResponse(
            items=items, next_cursor=next_cursor, has_more=has_more
        )

    def _resolve_asset(
        self,
        asset_group_id: str,
        preferred_image_id: str | None,
        *,
        require_published: bool = True,
        strict_preferred: bool = True,
    ) -> tuple[AssetGroup, Image]:
        group = self.assets.get(asset_group_id)
        if group is None or (require_published and group.publish_status != "published"):
            raise NotFoundError("asset_not_found", "素材不存在或尚未发布")
        if preferred_image_id:
            preferred = self.images.get(preferred_image_id)
            if (
                preferred is not None
                and preferred.asset_group_id == group.id
                and preferred.is_current
            ):
                return group, preferred
            if strict_preferred:
                raise AppError("invalid_preferred_image", "所选图片版本不属于该素材")
        image = self._display_image(group, None)
        if image is None:
            raise NotFoundError("asset_image_not_found", "素材没有可用图片")
        return group, image

    @staticmethod
    def _display_image(group: AssetGroup, preferred_image_id: str | None) -> Image | None:
        active = [item for item in group.images if item.deleted_at is None and item.is_current]
        if preferred_image_id:
            preferred = next((item for item in active if item.id == preferred_image_id), None)
            if preferred is not None:
                return preferred
        primary = next((item for item in active if item.id == group.primary_image_id), None)
        return primary or (max(active, key=lambda item: item.version_no) if active else None)

    def _get_board(self, user_id: str, board_id: str) -> AssetCollectionBoard:
        board = self.collections.get_board(user_id, board_id)
        if board is None:
            raise NotFoundError("board_not_found", "画板不存在")
        return board

    @staticmethod
    def _board_read(board: AssetCollectionBoard) -> AssetCollectionBoardRead:
        return AssetCollectionBoardRead(
            id=board.id,
            name=board.name,
            item_count=len(board.items),
            created_at=board.created_at,
            updated_at=board.updated_at,
        )

    def _record_change(
        self,
        user: User,
        group: AssetGroup,
        image: Image,
        *,
        action: str,
        behavior_type: str | None,
        context: AssetSaveContext,
        board_id: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        event = self.events.add(
            UserUsageEvent(
                user_id=user.id,
                event_type="asset_collection",
                target_type="image",
                target_id=image.id,
                details_json=json.dumps(
                    {
                        "action": action,
                        "assetGroupId": group.id,
                        "boardId": board_id,
                        "source": context.source,
                        "position": context.position,
                        "searchLogId": context.search_log_id,
                        "keyword": context.keyword.strip()[:200],
                        "preferenceTransition": behavior_type,
                    },
                    ensure_ascii=False,
                ),
                created_at=now,
            )
        )
        if user.role != "business" or not behavior_type:
            return
        self.behavior_events.add(
            AiSearchBehaviorEvent(
                source_event_id=event.id,
                user_id=user.id,
                item_id=image.id,
                event_type=behavior_type,
                event_timestamp=int(now.timestamp() * 1000),
                event_scene=context.source,
                details_json=json.dumps(
                    {
                        "source_action": action,
                        "asset_group_id": group.id,
                        "board_id": board_id,
                        "search_log_id": context.search_log_id,
                        "position": context.position,
                    },
                    ensure_ascii=False,
                ),
            )
        )


def _normalize_board_name(value: str) -> tuple[str, str]:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        raise AppError("invalid_board_name", "请输入画板名称")
    return cleaned, cleaned.casefold()


def _encode_cursor(created_at: datetime, asset_group_id: str) -> str:
    raw = json.dumps(
        {"at": created_at.isoformat(), "id": asset_group_id}, separators=(",", ":")
    )
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[datetime | None, str | None]:
    if not cursor:
        return None, None
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        value = json.loads(raw)
        return datetime.fromisoformat(value["at"]), str(value["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AppError("invalid_cursor", "分页游标无效") from exc
