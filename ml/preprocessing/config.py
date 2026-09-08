"""
ml/preprocessing/config.py
==========================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 4: Dataset Configuration & Path Resolver

Provides environment-variable-driven and portable path resolution for the
external SONARIS dataset. This allows team members to point to their local
or synced Google Drive folder without hardcoding personal paths.

Environment Variables:
    SONARIS_DATA_DIR:
        Path to the root of the DRISHTI-SSS or SSS survey dataset.
        Defaults to repository 'datasets/' folder, then 'C:\\drishti_clean'.

    SONARIS_OUTPUT_DIR:
        Path where preprocessed images and tiles should be saved.
        Defaults to 'datasets/preprocessed/' within the workspace.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# Standard environment variable names
ENV_SONARIS_DATA_DIR = "SONARIS_DATA_DIR"
ENV_SONARIS_OUTPUT_DIR = "SONARIS_OUTPUT_DIR"

# Known fallback locations
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LOCAL_C_PATH = Path(r"C:\drishti_clean")
_DEFAULT_REPO_DATASET = _REPO_ROOT / "datasets"
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "datasets" / "preprocessed"


def get_dataset_dir(custom_path: Optional[str | Path] = None) -> Path:
    """
    Resolve the root directory of the SONARIS dataset.

    Resolution precedence:
        1. Explicit custom_path argument (if provided).
        2. Environment variable `SONARIS_DATA_DIR`.
        3. Local directory `C:\\drishti_clean` (if it exists).
        4. Repository `datasets/` directory (if populated).

    Returns:
        Path to the dataset directory.

    Raises:
        FileNotFoundError: If no valid dataset directory is found or configured.
    """
    if custom_path is not None:
        p = Path(custom_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"Specified dataset path does not exist: {p}")

    # Check environment variable
    env_path = os.environ.get(ENV_SONARIS_DATA_DIR)
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
        raise FileNotFoundError(
            f"{ENV_SONARIS_DATA_DIR} is set to '{env_path}', but that path does not exist."
        )

    # Check local fallback C:\drishti_clean
    if _DEFAULT_LOCAL_C_PATH.exists():
        return _DEFAULT_LOCAL_C_PATH

    # Check repo datasets/ directory if populated
    if _DEFAULT_REPO_DATASET.exists():
        # Check if there are actual image files or subdirectories
        has_content = any(
            item.is_dir() or item.suffix.lower() in {".jpg", ".png", ".bmp", ".tif"}
            for item in _DEFAULT_REPO_DATASET.iterdir()
            if item.name != ".gitkeep"
        )
        if has_content:
            return _DEFAULT_REPO_DATASET

    raise FileNotFoundError(
        f"No dataset directory found. Please set the '{ENV_SONARIS_DATA_DIR}' "
        "environment variable to your local dataset path (e.g. your synced Google Drive folder), "
        f"or place files in '{_DEFAULT_REPO_DATASET}'."
    )


def is_dataset_available() -> bool:
    """Check whether a dataset directory is currently reachable."""
    try:
        get_dataset_dir()
        return True
    except FileNotFoundError:
        return False


def get_output_dir(custom_path: Optional[str | Path] = None) -> Path:
    """
    Resolve the output directory for preprocessed images and tiles.

    Resolution precedence:
        1. Explicit custom_path argument (if provided).
        2. Environment variable `SONARIS_OUTPUT_DIR`.
        3. Workspace default: `<repo>/datasets/preprocessed/`.

    Returns:
        Path to output directory (created if it does not exist).
    """
    if custom_path is not None:
        p = Path(custom_path)
    else:
        env_path = os.environ.get(ENV_SONARIS_OUTPUT_DIR)
        p = Path(env_path) if env_path else _DEFAULT_OUTPUT_DIR

    p.mkdir(parents=True, exist_ok=True)
    return p
