from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai,
    assets,
    auth,
    business_concepts,
    images,
    search_feedback,
    search_ops,
    tags,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(images.router)
api_router.include_router(assets.router)
api_router.include_router(business_concepts.router)
api_router.include_router(tags.router)
api_router.include_router(ai.router)
api_router.include_router(admin.router)
api_router.include_router(search_ops.router)
api_router.include_router(search_feedback.router)
