from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "标签图片仓库"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = f"sqlite:///{PROJECT_DIR / 'data' / 'piancton.db'}"
    storage_dir: Path = PROJECT_DIR / "storage" / "images"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    session_cookie_name: str = "piancton_session"
    csrf_cookie_name: str = "piancton_csrf"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 168
    max_upload_bytes: int = 100 * 1024 * 1024
    max_image_pixels: int = 80_000_000
    thumbnail_max_size: int = 640
    login_max_attempts: int = 5
    login_window_minutes: int = 15
    login_block_minutes: int = 30
    model_provider: str = "placeholder"
    model_provider_order: str = "primary,fallback1,fallback2"
    model_name: str = ""
    model_base_url: str = ""
    model_api_key: str = ""
    model_temperature: float = 0.2
    model_timeout_seconds: int = 120
    fallback1_name: str = ""
    fallback1_base_url: str = ""
    fallback1_api_key: str = ""
    fallback1_temperature: float = 0.2
    fallback2_name: str = ""
    fallback2_base_url: str = ""
    fallback2_api_key: str = ""
    fallback2_temperature: float = 0.2
    image_analysis_model_name: str = ""
    image_analysis_base_url: str = ""
    image_analysis_api_key: str = ""
    image_analysis_temperature: float = 0.2
    asset_phrase_model_name: str = ""
    asset_phrase_base_url: str = ""
    asset_phrase_api_key: str = ""
    asset_phrase_temperature: float = 0.2
    search_fallback_model_name: str = ""
    search_fallback_base_url: str = ""
    search_fallback_api_key: str = ""
    search_fallback_temperature: float = 0.2
    search_backend: str = "database"
    meilisearch_url: str = ""
    meilisearch_api_key: str = ""
    meilisearch_index: str = "images"
    search_timeout_seconds: float = 2.0
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model_name: str = ""
    embedding_timeout_seconds: float = 10.0
    embedding_top_n: int = 100
    reranker_base_url: str = ""
    reranker_api_key: str = ""
    reranker_model_name: str = ""
    reranker_timeout_seconds: float = 5.0
    reranker_top_n: int = 50
    search_total_timeout_seconds: float = 2.5
    search_meilisearch_timeout_seconds: float = 0.2
    search_embedding_timeout_seconds: float = 2.5
    search_understanding_timeout_seconds: float = 75.0
    search_system_routing_timeout_seconds: float = 15.0
    search_selling_point_timeout_seconds: float = 25.0
    search_proof_point_timeout_seconds: float = 20.0
    search_candidate_review_timeout_seconds: float = 20.0
    search_candidate_review_limit: int = 5
    search_result_recommendation_timeout_seconds: float = 6.0
    search_result_recommendation_limit: int = 12
    search_understanding_grace_seconds: float = 5.0
    search_understanding_retry_attempts: int = 1
    search_understanding_retry_backoff_seconds: float = 1.0
    search_reranker_timeout_seconds: float = 2.0
    search_candidate_limit: int = 20
    search_cache_ttl_seconds: float = 300.0
    search_cache_max_entries: int = 512

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
