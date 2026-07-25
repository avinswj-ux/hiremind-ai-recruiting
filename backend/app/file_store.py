from __future__ import annotations

import hashlib
import re
from pathlib import Path

from fastapi import UploadFile

from .config import UPLOAD_DIR, settings

ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt"}


def safe_filename(filename: str) -> str:
    name = Path(filename or "resume").name
    return re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]", "_", name)[:180]


async def save_upload(file: UploadFile, storage_key: str) -> tuple[Path, int, str]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("仅支持 PDF、DOCX、TXT")

    destination = UPLOAD_DIR / storage_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    limit = settings.max_file_size_mb * 1024 * 1024
    digest = hashlib.sha256()
    size = 0

    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise ValueError(f"单个文件不能超过 {settings.max_file_size_mb} MB")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    return destination, size, digest.hexdigest()


def path_for(storage_key: str) -> Path:
    return UPLOAD_DIR / storage_key
