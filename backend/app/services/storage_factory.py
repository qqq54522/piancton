from functools import lru_cache
from urllib.parse import urlparse

from app.core.errors import AppError
from app.services.storage_service import LocalStorageProvider, StorageProvider
from app.services.tos_storage import TosStorageProvider


@lru_cache(maxsize=4)
def _client(ak: str, sk: str, endpoint: str, region: str):
    import tos

    return tos.TosClientV2(
        ak,
        sk,
        endpoint,
        region,
        connection_time=5,
        socket_timeout=30,
        max_retry_count=1,
        enable_crc=True,
    )


def build_storage(settings) -> StorageProvider:
    if settings.storage_backend == "local":
        return LocalStorageProvider(settings.storage_dir)
    if settings.storage_backend != "tos":
        raise AppError("storage_config_invalid", "图片存储类型配置无效", status_code=503)
    if not all(
        (
            settings.tos_bucket,
            settings.tos_region,
            settings.tos_endpoint,
            settings.tos_access_key_id,
            settings.tos_secret_access_key,
        )
    ):
        raise AppError("storage_config_invalid", "对象存储配置不完整", status_code=503)
    endpoint = urlparse(settings.tos_endpoint)
    if endpoint.scheme != "https" or not endpoint.hostname or endpoint.username:
        raise AppError("storage_config_invalid", "对象存储地址必须为 HTTPS", status_code=503)
    return TosStorageProvider(
        settings.storage_dir,
        _client(
            settings.tos_access_key_id,
            settings.tos_secret_access_key,
            settings.tos_endpoint,
            settings.tos_region,
        ),
        settings.tos_bucket,
        settings.tos_prefix,
    )
