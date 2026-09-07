"""Validate upload/read/delete with a unique small object, without printing credentials."""

import tempfile
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.services.storage_factory import build_storage
from app.services.tos_storage import TosStorageProvider


def main():
    storage = build_storage(get_settings())
    if not isinstance(storage, TosStorageProvider):
        raise RuntimeError("STORAGE_BACKEND must be tos")
    key = f"tos-check-{uuid.uuid4()}.txt"
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "check.txt"
        source.write_bytes(b"piancton-storage-check")
        try:
            storage.upload_file(key, source, "text/plain")
            result = storage.path_for(key)
            try:
                if result.read_bytes() != source.read_bytes():
                    raise RuntimeError("content mismatch")
            finally:
                storage.release(result)
        finally:
            storage.delete_key(key)
    print("TOS upload/read/delete check passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"TOS check failed: {getattr(exc, 'code', 'storage_check_failed')}")
        raise SystemExit(1) from None
