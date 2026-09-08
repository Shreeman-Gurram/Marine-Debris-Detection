"""
backend/app/services/model_loader.py
====================================
SONARIS Model Acquisition & Resolution Layer

Ensures the DRISHTI YOLO model weights (best_detector.pt) are available
before inference runs:
  1. Checks if models/best_detector.pt exists locally.
     If found -> returns path immediately (zero delay, keeps local dev fast).
  2. If missing, checks MODEL_DOWNLOAD_URL (or YOLO_MODEL_URL) environment variable.
     If set -> downloads the weights securely to models/best_detector.pt once.
  3. If missing and no download URL is configured -> raises an actionable error.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("sonaris.model_loader")


def _find_project_root() -> Path:
    """Resolve project root directory containing models/."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "models" / "best_detector.pt").exists():
            return parent
    # Default to prototype root
    return here.parent.parent.parent


def get_default_model_path() -> Path:
    """Return standard local path: <project_root>/models/best_detector.pt."""
    custom_path = os.environ.get("YOLO_MODEL_PATH", "").strip()
    if custom_path:
        return Path(custom_path)
    return _find_project_root() / "models" / "best_detector.pt"


def is_model_available() -> bool:
    """Check if model exists locally or download URL is provided."""
    model_path = get_default_model_path()
    if model_path.is_file() and model_path.stat().st_size > 1_000_000:
        return True
    return bool(os.environ.get("MODEL_DOWNLOAD_URL", "").strip() or
                os.environ.get("YOLO_MODEL_URL", "").strip())


def download_model(url: str, destination: Path) -> Path:
    """
    Download model weights from a direct HTTP(S) URL into destination.
    Uses atomic temporary file write to avoid partial/corrupted weights.
    """
    import requests

    logger.info("Downloading YOLO model from: %s", url)
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Download to temporary file in same directory for atomic rename
    temp_file = destination.with_suffix(".tmp")
    try:
        with requests.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            total_bytes = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(temp_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

        if downloaded < 1_000_000:
            raise ValueError(
                f"Downloaded model is unexpectedly small ({downloaded} bytes). "
                "Verify the download URL points directly to best_detector.pt binary."
            )

        temp_file.replace(destination)
        logger.info(
            "YOLO model successfully downloaded to %s (%d bytes).",
            destination, downloaded,
        )
        return destination
    except Exception as exc:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
        logger.error("Failed to download model from %s: %s", url, exc)
        raise RuntimeError(f"Failed to download YOLO model: {exc}") from exc


def ensure_model_available() -> Path:
    """
    Ensure the YOLO model is available on disk and return its Path.

    Resolution:
      1. If models/best_detector.pt exists and is valid -> return it.
      2. If not, but MODEL_DOWNLOAD_URL or YOLO_MODEL_URL is set -> download it.
      3. Otherwise -> raise RuntimeError with clear instructions.
    """
    model_path = get_default_model_path()

    # 1. Local file exists and is reasonably sized (> 1MB)
    if model_path.is_file() and model_path.stat().st_size > 1_000_000:
        logger.debug("Using existing local YOLO model at: %s", model_path)
        return model_path

    # 2. Check download URL
    download_url = (
        os.environ.get("MODEL_DOWNLOAD_URL", "").strip() or
        os.environ.get("YOLO_MODEL_URL", "").strip()
    )

    if download_url:
        logger.info("Local model not found at %s. Attempting download...", model_path)
        return download_model(download_url, model_path)

    # 3. Model missing and no download URL
    raise RuntimeError(
        f"YOLO model weights not found at: {model_path}\n"
        "To resolve this in a cloud environment:\n"
        "  1. Host best_detector.pt (e.g. GitHub Releases, Hugging Face, or S3/R2)\n"
        "  2. Set environment variable: MODEL_DOWNLOAD_URL=<direct_download_url>\n"
        "In local development:\n"
        "  Place best_detector.pt into the 'models/' folder in the project root."
    )
