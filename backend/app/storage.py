import os
import re
import uuid
import shutil
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile

BASE_DIR = Path(__file__).resolve().parent.parent / "storage" / "files"


def ensure_storage_dir() -> Path:
    """Ensure storage directory exists and return Path."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    return BASE_DIR


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and remove unsafe chars."""
    clean_str = filename.replace("\\", "/")
    name = os.path.basename(clean_str)
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    name = re.sub(r"^\.+", "", name)
    if not name:
        name = "unnamed_file"
    return name


def sanitize_folder_path(folder_path: str) -> str:
    """Sanitize folder path to prevent directory traversal and remove unsafe chars."""
    parts = Path(folder_path).parts
    cleaned_parts = [p for p in parts if p not in ("..", ".", "/", "\\")]
    return "/".join(cleaned_parts) if cleaned_parts else "root"


def generate_storage_key(filename: str) -> str:
    """Generate a unique disk key to prevent filename collisions."""
    safe_name = sanitize_filename(filename)
    unique_id = uuid.uuid4().hex
    return f"{unique_id}_{safe_name}"


def save_uploaded_file(upload_file: UploadFile) -> Tuple[str, int, str]:
    """
    Saves an UploadFile to disk.
    Returns: (absolute_storage_path, file_size_bytes, mime_type)
    """
    storage_dir = ensure_storage_dir()
    storage_key = generate_storage_key(upload_file.filename or "file")
    target_path = storage_dir / storage_key

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    file_size = target_path.stat().st_size
    mime_type = upload_file.content_type or "application/octet-stream"
    return str(target_path), file_size, mime_type


def save_bytes(content: bytes, filename: str, mime_type: str = "application/octet-stream") -> Tuple[str, int, str]:
    """
    Synchronously saves raw bytes to disk.
    Returns: (absolute_storage_path, file_size_bytes, mime_type)
    """
    storage_dir = ensure_storage_dir()
    storage_key = generate_storage_key(filename)
    target_path = storage_dir / storage_key

    with open(target_path, "wb") as f:
        f.write(content)

    return str(target_path), len(content), mime_type


def delete_stored_file(storage_path: Optional[str]) -> bool:
    """Safely delete stored file if within storage dir and exists."""
    if not storage_path:
        return False
    try:
        p = Path(storage_path).resolve()
        base = ensure_storage_dir().resolve()
        if (base == p.parent or base in p.parents) and p.is_file():
            p.unlink()
            return True
    except Exception:
        pass
    return False
