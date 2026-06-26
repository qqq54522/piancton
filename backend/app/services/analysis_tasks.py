from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.ai.contracts import ModelProvider
from app.core.config import get_settings
from app.services.ai_service import AiService
from app.services.embedding_index import EmbeddingIndexSync
from app.services.image_analysis_service import ImageAnalysisService
from app.services.image_service import ImageService
from app.services.storage_service import LocalStorageProvider

logger = logging.getLogger(__name__)


def run_image_analysis_task(
    image_id: str,
    analysis_run_id: str,
    provider: ModelProvider,
    session_factory: Callable[[], Session],
) -> None:
    """Run image analysis outside the request lifecycle with a fresh DB session."""

    settings = get_settings()
    db = session_factory()
    images = ImageService(
        db,
        LocalStorageProvider(settings.storage_dir),
        settings.max_upload_bytes,
        settings.max_image_pixels,
        settings.thumbnail_max_size,
    )
    analysis = ImageAnalysisService(db, embedding_index=EmbeddingIndexSync.from_settings())
    try:
        analysis.mark_running(image_id, analysis_run_id)
        path, _image = images.content(image_id)
        result = AiService(provider).analyze_image(path)
        analysis.save_ai_analysis(image_id, result, analysis_run_id=analysis_run_id)
    except Exception:
        logger.exception("Image analysis task failed", extra={"image_id": image_id})
        analysis.uow.rollback()
        try:
            analysis.mark_failed(image_id, analysis_run_id)
        except Exception:
            analysis.uow.rollback()
    finally:
        db.close()
