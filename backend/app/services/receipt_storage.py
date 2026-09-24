from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[2]
RECEIPTS_DIR = BACKEND_ROOT / "uploads" / "receipts"

_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def save_receipt(
    *,
    file: BinaryIO,
    content_type: str | None,
) -> str:
    """Persist a payment receipt in the MVP local receipt directory."""
    extension = _CONTENT_TYPE_EXTENSIONS.get(content_type or "")
    if extension is None:
        raise ValueError(
            "Receipt must be a JPEG, PNG, or WebP image."
        )

    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    destination = RECEIPTS_DIR / filename

    try:
        file.seek(0)
        with destination.open("wb") as output:
            shutil.copyfileobj(file, output)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return f"uploads/receipts/{filename}"


def delete_receipt(receipt_path: str) -> None:
    """Delete a locally stored receipt by its relative storage path."""
    relative_path = Path(receipt_path)

    if (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or relative_path.parts[:2] != ("uploads", "receipts")
    ):
        return

    target = BACKEND_ROOT.joinpath(*relative_path.parts)

    try:
        target.resolve().relative_to(RECEIPTS_DIR.resolve())
    except ValueError:
        return

    target.unlink(missing_ok=True)
