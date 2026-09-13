from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.asset import AssetGroup
from app.models.asset_collection import (
    AssetCollectionBoard,
    AssetCollectionBoardItem,
    UserAssetLike,
)


class AssetCollectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_like(self, user_id: str, asset_group_id: str) -> UserAssetLike | None:
        return self.db.scalar(
            select(UserAssetLike).where(
                UserAssetLike.user_id == user_id,
                UserAssetLike.asset_group_id == asset_group_id,
            )
        )

    def list_likes(
        self,
        user_id: str,
        *,
        cursor_at: datetime | None,
        cursor_id: str | None,
        limit: int,
    ) -> list[UserAssetLike]:
        stmt = (
            select(UserAssetLike)
            .where(UserAssetLike.user_id == user_id)
            .options(
                selectinload(UserAssetLike.asset_group).selectinload(AssetGroup.images)
            )
        )
        if cursor_at is not None and cursor_id:
            stmt = stmt.where(
                or_(
                    UserAssetLike.created_at < cursor_at,
                    and_(
                        UserAssetLike.created_at == cursor_at,
                        UserAssetLike.asset_group_id < cursor_id,
                    ),
                )
            )
        return list(
            self.db.scalars(
                stmt.order_by(
                    UserAssetLike.created_at.desc(),
                    UserAssetLike.asset_group_id.desc(),
                ).limit(limit + 1)
            ).all()
        )

    def list_like_ids(self, user_id: str) -> list[str]:
        return list(
            self.db.scalars(
                select(UserAssetLike.asset_group_id)
                .where(UserAssetLike.user_id == user_id)
                .order_by(UserAssetLike.created_at.desc())
            ).all()
        )

    def add_like(self, value: UserAssetLike) -> UserAssetLike:
        self.db.add(value)
        self.db.flush()
        return value

    def delete_like(self, value: UserAssetLike) -> None:
        self.db.delete(value)
        self.db.flush()

    def list_boards(self, user_id: str) -> list[AssetCollectionBoard]:
        return list(
            self.db.scalars(
                select(AssetCollectionBoard)
                .where(AssetCollectionBoard.user_id == user_id)
                .options(selectinload(AssetCollectionBoard.items))
                .order_by(AssetCollectionBoard.updated_at.desc(), AssetCollectionBoard.id.desc())
            ).all()
        )

    def get_board(self, user_id: str, board_id: str) -> AssetCollectionBoard | None:
        return self.db.scalar(
            select(AssetCollectionBoard)
            .where(
                AssetCollectionBoard.id == board_id,
                AssetCollectionBoard.user_id == user_id,
            )
            .options(selectinload(AssetCollectionBoard.items))
        )

    def add_board(self, value: AssetCollectionBoard) -> AssetCollectionBoard:
        self.db.add(value)
        self.db.flush()
        return value

    def save_board(self, _value: AssetCollectionBoard) -> None:
        # Boards returned by this repository are already attached. Re-adding the
        # parent after one of its delete-orphan items was removed can make
        # SQLAlchemy attempt to resurrect the deleted child.
        self.db.flush()

    def delete_board(self, value: AssetCollectionBoard) -> None:
        self.db.delete(value)
        self.db.flush()

    def board_name_exists(
        self,
        user_id: str,
        normalized_name: str,
        *,
        exclude_id: str | None = None,
    ) -> bool:
        stmt = select(
            exists().where(
                AssetCollectionBoard.user_id == user_id,
                AssetCollectionBoard.normalized_name == normalized_name,
            )
        )
        if exclude_id:
            stmt = select(
                exists().where(
                    AssetCollectionBoard.user_id == user_id,
                    AssetCollectionBoard.normalized_name == normalized_name,
                    AssetCollectionBoard.id != exclude_id,
                )
            )
        return bool(self.db.scalar(stmt))

    def get_board_item(
        self, board_id: str, asset_group_id: str
    ) -> AssetCollectionBoardItem | None:
        return self.db.scalar(
            select(AssetCollectionBoardItem).where(
                AssetCollectionBoardItem.board_id == board_id,
                AssetCollectionBoardItem.asset_group_id == asset_group_id,
            )
        )

    def list_board_items(
        self,
        board_id: str,
        *,
        cursor_at: datetime | None,
        cursor_id: str | None,
        limit: int,
    ) -> list[AssetCollectionBoardItem]:
        stmt = (
            select(AssetCollectionBoardItem)
            .where(AssetCollectionBoardItem.board_id == board_id)
            .options(
                selectinload(AssetCollectionBoardItem.asset_group).selectinload(
                    AssetGroup.images
                )
            )
        )
        if cursor_at is not None and cursor_id:
            stmt = stmt.where(
                or_(
                    AssetCollectionBoardItem.created_at < cursor_at,
                    and_(
                        AssetCollectionBoardItem.created_at == cursor_at,
                        AssetCollectionBoardItem.asset_group_id < cursor_id,
                    ),
                )
            )
        return list(
            self.db.scalars(
                stmt.order_by(
                    AssetCollectionBoardItem.created_at.desc(),
                    AssetCollectionBoardItem.asset_group_id.desc(),
                ).limit(limit + 1)
            ).all()
        )

    def add_board_item(self, value: AssetCollectionBoardItem) -> AssetCollectionBoardItem:
        self.db.add(value)
        self.db.flush()
        return value

    def delete_board_item(self, value: AssetCollectionBoardItem) -> None:
        self.db.delete(value)
        self.db.flush()

    def board_ids_for_asset(self, user_id: str, asset_group_id: str) -> list[str]:
        return list(
            self.db.scalars(
                select(AssetCollectionBoardItem.board_id)
                .join(
                    AssetCollectionBoard,
                    AssetCollectionBoard.id == AssetCollectionBoardItem.board_id,
                )
                .where(
                    AssetCollectionBoard.user_id == user_id,
                    AssetCollectionBoardItem.asset_group_id == asset_group_id,
                )
                .order_by(AssetCollectionBoard.updated_at.desc())
            ).all()
        )

    def is_saved_anywhere(
        self,
        user_id: str,
        asset_group_id: str,
        *,
        exclude_board_id: str | None = None,
    ) -> bool:
        if self.get_like(user_id, asset_group_id) is not None:
            return True
        stmt = (
            select(func.count())
            .select_from(AssetCollectionBoardItem)
            .join(AssetCollectionBoard, AssetCollectionBoard.id == AssetCollectionBoardItem.board_id)
            .where(
                AssetCollectionBoard.user_id == user_id,
                AssetCollectionBoardItem.asset_group_id == asset_group_id,
            )
        )
        if exclude_board_id:
            stmt = stmt.where(AssetCollectionBoardItem.board_id != exclude_board_id)
        return bool(self.db.scalar(stmt))
