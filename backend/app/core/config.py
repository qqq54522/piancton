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
    storage_backend: str = "local"
    tos_bucket: str = ""
    tos_region: str = "cn-shanghai"
    tos_endpoint: str = "https://tos-cn-shanghai.volces.com"
    tos_prefix: str = "piancton"
    tos_access_key_id: str = ""
    tos_secret_access_key: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    session_cookie_name: str = "piancton_session"
    csrf_cookie_name: str = "piancton_csrf"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 168
    max_upload_bytes: int = 100 * 1024 * 1024
    max_image_pixels: int = 80_000_000
    max_long_image_pixels: int = 160_000_000
    long_image_min_aspect_ratio: float = 3.0
    thumbnail_max_size: int = 640
    public_base_url: str = ""
    login_max_attempts: int = 5
    login_window_minutes: int = 15
    login_block_minutes: int = 30
    search_backend: str = "database"
    meilisearch_url: str = ""
    meilisearch_api_key: str = ""
    meilisearch_index: str = "images"
    search_timeout_seconds: float = 2.0
    embedding_top_n: int = 100
    ai_search_enabled: bool = False
    ai_search_sync_enabled: bool = True
    ai_search_base_url: str = "https://aisearch.cn-beijing.volces.com"
    ai_search_api_key: str = ""
    ai_search_application_id: str = ""
    ai_search_search_path: str = ""
    ai_search_chat_enabled: bool = False
    ai_search_chat_path: str = ""
    ai_search_chat_dataset_ids: str = ""
    ai_search_chat_timeout_seconds: float = 60.0
    ai_search_recommend_enabled: bool = False
    ai_search_recommend_path: str = ""
    ai_search_home_recommend_path: str = ""
    ai_search_recommend_timeout_seconds: float = 8.0
    ai_search_dataset_id: str = ""
    ai_search_image_dataset_id: str = ""
    ai_search_image_search_path: str = ""
    ai_search_image_sync_enabled: bool = False
    ai_search_timeout_seconds: float = 8.0
    ai_search_page_size: int = 10
    ai_search_public_base_url: str = ""
    ai_search_behavior_enabled: bool = False
    ai_search_behavior_api_key: str = ""
    ai_search_behavior_dataset_id: str = ""
    ai_search_behavior_sync_interval_seconds: int = 30
    ai_search_behavior_sync_batch_size: int = 100
    ai_search_behavior_sync_startup_delay_seconds: int = 10
    reranker_top_n: int = 50
    search_total_timeout_seconds: float = 180.0
    search_meilisearch_timeout_seconds: float = 0.2
    search_embedding_timeout_seconds: float = 2.5
    search_understanding_timeout_seconds: float = 75.0
    search_system_routing_timeout_seconds: float = 45.0
    search_selling_point_timeout_seconds: float = 60.0
    search_proof_point_timeout_seconds: float = 45.0
    search_candidate_review_timeout_seconds: float = 45.0
    search_candidate_review_limit: int = 5
    search_result_recommendation_timeout_seconds: float = 45.0
    search_result_recommendation_limit: int = 12
    search_understanding_grace_seconds: float = 5.0
    search_understanding_retry_attempts: int = 1
    search_understanding_retry_backoff_seconds: float = 1.0
    search_selling_point_decision_cards_enabled: bool = True
    search_reranker_timeout_seconds: float = 2.0
    search_candidate_limit: int = 20
    search_cache_ttl_seconds: float = 300.0
    search_cache_max_entries: int = 512
    model_config = SettingsConfigDict(
        env_file=(
            BACKEND_DIR / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
