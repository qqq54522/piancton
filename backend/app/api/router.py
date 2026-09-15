from fastapi import APIRouter

from app.api.v1 import (
    admin,
    announcements,
    asset_agent,
    asset_collections,
    asset_identity,
    assets,
    auth,
    business_concepts,
    business_facets,
    channel_folders,
    images,
    search_feedback,
    search_ops,
    tags,
    usage,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(announcements.router)
api_router.include_router(announcements.admin_router)
api_router.include_router(images.router)
api_router.include_router(channel_folders.router)
api_router.include_router(assets.router)
api_router.include_router(business_concepts.router)
api_router.include_router(business_facets.router)
api_router.include_router(tags.router)
api_router.include_router(asset_agent.router)
api_router.include_router(asset_collections.router)
api_router.include_router(asset_identity.router)
api_router.include_router(admin.router)
api_router.include_router(search_ops.router)
api_router.include_router(search_feedback.router)
api_router.include_router(usage.router)
