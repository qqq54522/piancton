from fastapi import APIRouter

from app.api.v1 import admin, ai, auth, images, tags

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(images.router)
api_router.include_router(tags.router)
api_router.include_router(ai.router)
api_router.include_router(admin.router)
