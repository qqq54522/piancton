from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import (
    get_asset_collection_service,
    get_current_user,
    require_csrf,
)
from app.models.user import User
from app.schemas.asset_collection import (
    AssetCollectionBoardCreate,
    AssetCollectionBoardListResponse,
    AssetCollectionBoardRead,
    AssetCollectionBoardUpdate,
    AssetCollectionMembership,
    AssetCollectionSummary,
    AssetSaveContext,
    SavedAssetListResponse,
)
from app.services.asset_collection_service import AssetCollectionService

router = APIRouter(prefix="/me/asset-collections", tags=["asset-collections"])


@router.get("/summary", response_model=AssetCollectionSummary)
def get_summary(
    user: User = Depends(get_current_user),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.summary(user)


@router.get("/assets/{asset_group_id}/membership", response_model=AssetCollectionMembership)
def get_membership(
    asset_group_id: str,
    user: User = Depends(get_current_user),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.membership(user, asset_group_id)


@router.get("/likes", response_model=SavedAssetListResponse)
def list_likes(
    cursor: str | None = None,
    limit: int = 48,
    user: User = Depends(get_current_user),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.list_likes(user, cursor=cursor, limit=max(1, min(limit, 100)))


@router.put("/likes/{asset_group_id}", response_model=AssetCollectionMembership)
def like_asset(
    asset_group_id: str,
    payload: AssetSaveContext,
    user: User = Depends(require_csrf),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.like(user, asset_group_id, payload)


@router.delete("/likes/{asset_group_id}", response_model=AssetCollectionMembership)
def unlike_asset(
    asset_group_id: str,
    payload: AssetSaveContext,
    user: User = Depends(require_csrf),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.unlike(user, asset_group_id, payload)


@router.get("/boards", response_model=AssetCollectionBoardListResponse)
def list_boards(
    user: User = Depends(get_current_user),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.list_boards(user)


@router.post(
    "/boards",
    response_model=AssetCollectionBoardRead,
    status_code=status.HTTP_201_CREATED,
)
def create_board(
    payload: AssetCollectionBoardCreate,
    user: User = Depends(require_csrf),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.create_board(user, payload.name)


@router.patch("/boards/{board_id}", response_model=AssetCollectionBoardRead)
def rename_board(
    board_id: str,
    payload: AssetCollectionBoardUpdate,
    user: User = Depends(require_csrf),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.rename_board(user, board_id, payload.name)


@router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(
    board_id: str,
    user: User = Depends(require_csrf),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    service.delete_board(user, board_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/boards/{board_id}/items", response_model=SavedAssetListResponse)
def list_board_items(
    board_id: str,
    cursor: str | None = None,
    limit: int = 48,
    user: User = Depends(get_current_user),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.list_board_items(
        user, board_id, cursor=cursor, limit=max(1, min(limit, 100))
    )


@router.put(
    "/boards/{board_id}/items/{asset_group_id}",
    response_model=AssetCollectionMembership,
)
def add_to_board(
    board_id: str,
    asset_group_id: str,
    payload: AssetSaveContext,
    user: User = Depends(require_csrf),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.add_to_board(user, board_id, asset_group_id, payload)


@router.delete(
    "/boards/{board_id}/items/{asset_group_id}",
    response_model=AssetCollectionMembership,
)
def remove_from_board(
    board_id: str,
    asset_group_id: str,
    payload: AssetSaveContext,
    user: User = Depends(require_csrf),
    service: AssetCollectionService = Depends(get_asset_collection_service),
):
    return service.remove_from_board(user, board_id, asset_group_id, payload)
