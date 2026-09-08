"""
ml/preprocessing/pipeline.py
=============================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 1: Sonar Preprocessing Foundation

Main sonar preprocessing pipeline.

Pipeline Flow
-------------
Input image (path or numpy array)
    Γåô
Validation (type, shape, non-empty, readable)
    Γåô
Load as grayscale uint8 (if path provided)
    Γåô
Denoise  [denoise.py ΓåÆ cv2.fastNlMeansDenoising]
    Γåô
Normalize  [normalize.py ΓåÆ CLAHE ΓåÆ min-max float32]
    Γåô
Output: float32 numpy array [0.0, 1.0], shape (H, W)
         + optional save to disk as PNG

Usage
-----
    from ml.preprocessing import preprocess_image

    # From file path ΓÇö returns float32 array
    result = preprocess_image("path/to/sonar_image.png")

    # From numpy array (uint8 grayscale or BGR)
    import numpy as np
    img = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
    result = preprocess_image(img)

    # With output path ΓÇö also saves preprocessed PNG to disk
    result = preprocess_image(
        "path/to/sonar.png",
        output_path="path/to/output/sonar_preprocessed.png"
    )

Phase 2 Extensions
------------------
This pipeline is designed to be extended. Future phases will add:
  - Tiling / patch extraction (Phase 2)
  - Batch processing over a dataset directory (Phase 2)
  - Geolocation metadata attachment (Phase 3+)
  - Integration with P1 YOLO detection pipeline (Phase 2)

Notes
-----
- Does NOT modify the original P2 dataset (C:\\drishti_clean)
- Output paths must be separate from dataset paths
- Deterministic: same input always produces same output
- Filenames: if saving, appends '_preprocessed' suffix to stem
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import cv2
import numpy as np

from .denoise import denoise
from .normalize import normalize_float, normalize_uint8


# Type alias for image input: a file path or a numpy array
ImageInput = Union[str, Path, np.ndarray]


def preprocess_image(
    image: ImageInput,
    output_path: Union[str, Path, None] = None,
    denoise_h: float = 10.0,
    denoise_template_win: int = 7,
    denoise_search_win: int = 21,
    clahe_clip_limit: float = 2.0,
    clahe_tile_grid: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Run the full P3 sonar preprocessing pipeline on a single image.

    Applies denoising (Non-Local Means) followed by normalization
    (CLAHE + min-max scaling) to produce a float32 [0.0, 1.0] output
    suitable for downstream ML detection (P1) and analysis.

    Args:
        image:                Input sonar image. Can be:
                                - str or pathlib.Path pointing to a
                                  .jpg / .jpeg / .png sonar image file
                                - numpy.ndarray (uint8, grayscale H├ùW or
                                  BGR H├ùW├ù3)
        output_path:          Optional. If provided (str or Path), the
                              preprocessed result is also saved as a PNG
                              file at this location. The directory will be
                              created if it does not exist. The original
                              dataset is NEVER modified.
        denoise_h:            Non-Local Means filter strength (default 10.0).
                              Range 5ΓÇô15 recommended for SSS images.
        denoise_template_win: NLM template window size in pixels (default 7).
        denoise_search_win:   NLM search window size in pixels (default 21).
        clahe_clip_limit:     CLAHE contrast limit (default 2.0).
        clahe_tile_grid:      CLAHE tile grid size (default (8, 8)).

    Returns:
        Preprocessed sonar image as a float32 numpy ndarray with shape
        (H, W) and values in [0.0, 1.0].

    Raises:
        TypeError:      If image type is unsupported.
        ValueError:     If image is empty, unreadable, or has wrong shape.
        FileNotFoundError: If a path is provided but the file does not exist.
        IOError:        If the image file cannot be decoded by OpenCV.

    Example:
        >>> import numpy as np
        >>> from ml.preprocessing import preprocess_image
        >>> img = np.random.randint(50, 200, (256, 256), dtype=np.uint8)
        >>> result = preprocess_image(img)
        >>> result.dtype
        dtype('float32')
        >>> 0.0 <= result.min() and result.max() <= 1.0
        True
    """
    # -----------------------------------------------------------------------
    # Step 1: Load / validate input
    # -----------------------------------------------------------------------
    raw = _load_as_grayscale(image)

    # -----------------------------------------------------------------------
    # Step 2: Denoise
    # -----------------------------------------------------------------------
    denoised = denoise(
        raw,
        h=denoise_h,
        template_win_size=denoise_template_win,
        search_win_size=denoise_search_win,
    )

    # -----------------------------------------------------------------------
    # Step 3: Normalize (CLAHE ΓåÆ float32 [0, 1])
    # -----------------------------------------------------------------------
    normalized = normalize_float(
        denoised,
        clip_limit=clahe_clip_limit,
        tile_grid_size=clahe_tile_grid,
    )

    # -----------------------------------------------------------------------
    # Step 4: Optional ΓÇö save to disk
    # -----------------------------------------------------------------------
    if output_path is not None:
        _save_preprocessed(normalized, Path(output_path))

    return normalized


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_as_grayscale(image: ImageInput) -> np.ndarray:
    """
    Load and return the image as a uint8 grayscale numpy array.

    - If image is a path: reads the file and converts to grayscale.
    - If image is a numpy array:
        - 2D ΓåÆ already grayscale, validated and returned.
        - 3D (H, W, 3) BGR ΓåÆ converted to grayscale.
    """
    if isinstance(image, (str, Path)):
        path = Path(image)

        if not path.exists():
            raise FileNotFoundError(
                f"Sonar image not found: {path}"
            )

        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValueError(
                f"Unsupported file format: '{path.suffix}'. "
                "Expected .jpg, .jpeg, or .png."
            )

        arr = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)

        # Ultralytics patches cv2.imread so that even IMREAD_GRAYSCALE
        # returns a 3D array (H, W, 1) instead of the standard 2D (H, W).
        # Squeeze out the singleton channel dimension when present.
        if arr is not None and arr.ndim == 3 and arr.shape[2] == 1:
            arr = arr[:, :, 0]

        if arr is None:
            raise IOError(
                f"OpenCV could not read the image file: {path}. "
                "The file may be corrupted or an unsupported encoding."
            )

        if arr.size == 0:
            raise ValueError(f"Image file loaded as empty array: {path}")

        return arr

    elif isinstance(image, np.ndarray):
        if image.size == 0:
            raise ValueError(
                "Input numpy array is empty (size == 0)."
            )

        if image.ndim == 2:
            # Already grayscale
            arr = image
        elif image.ndim == 3 and image.shape[2] == 3:
            # BGR ΓåÆ grayscale
            arr = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            raise ValueError(
                f"Unsupported array shape: {image.shape}. "
                "Expected (H, W) or (H, W, 3)."
            )

        # Ensure uint8 for downstream processing
        if arr.dtype != np.uint8:
            # Attempt safe conversion if within uint8 range
            arr_min, arr_max = float(arr.min()), float(arr.max())
            if 0.0 <= arr_min and arr_max <= 255.0:
                arr = arr.astype(np.uint8)
            else:
                raise ValueError(
                    f"Input array has dtype={arr.dtype} with values "
                    f"outside [0, 255]. Convert to uint8 before calling "
                    "preprocess_image()."
                )

        return arr

    else:
        raise TypeError(
            f"Unsupported image input type: {type(image).__name__}. "
            "Provide a file path (str/Path) or a numpy.ndarray."
        )


def _save_preprocessed(normalized: np.ndarray, output_path: Path) -> None:
    """
    Save a float32 [0, 1] normalized sonar image as a uint8 PNG.

    The float32 array is scaled to [0, 255] uint8 for disk storage.
    The original dataset path is never used here.
    """
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert float32 [0,1] ΓåÆ uint8 [0,255] for PNG storage
    to_save = (normalized * 255.0).clip(0, 255).astype(np.uint8)

    success = cv2.imwrite(str(output_path), to_save)

    if not success:
        raise IOError(
            f"Failed to write preprocessed image to: {output_path}. "
            "Check that the path is writable and the format is supported."
        )


# ===========================================================================
# Phase 2 Extensions
# ===========================================================================

# Import Phase 2 modules here (inside module scope to avoid circular imports
# and keep Phase 1 import surface clean)
from .enhance import enhance as _enhance  # noqa: E402


def preprocess_image_full(
    image: ImageInput,
    output_path: Union[str, Path, None] = None,
    denoise_h: float = 10.0,
    denoise_template_win: int = 7,
    denoise_search_win: int = 21,
    clahe_clip_limit: float = 2.0,
    clahe_tile_grid: tuple[int, int] = (8, 8),
    enhance_amount: float = 1.0,
    enhance_sigma: float = 1.0,
) -> np.ndarray:
    """
    Run the full P3 Phase 1 + Phase 2 sonar preprocessing pipeline.

    Extends preprocess_image() (Phase 1) by adding an unsharp masking
    enhancement step between CLAHE normalization and the final float32
    scaling. Phase 1's preprocess_image() function is NOT modified.

    Pipeline flow (Phase 1 + Phase 2):
        Input image (path or numpy array)
            Γåô
        _load_as_grayscale()       [Phase 1]
            Γåô
        denoise()                  [Phase 1 ΓÇö NLM denoising]
            Γåô
        normalize_uint8()          [Phase 1 ΓÇö CLAHE, uint8 output]
            Γåô
        enhance()                  [Phase 2 ΓÇö unsharp masking, uint8]
            Γåô
        min-max ΓåÆ float32 [0,1]   [Phase 2 ΓÇö final scaling]
            Γåô
        Output: float32 (H, W)

    Args:
        image:               Input sonar image. Path (str/Path) or numpy array.
                             Accepts uint8 grayscale (H,W) or BGR (H,W,3).
        output_path:         Optional. If provided, saves the preprocessed
                             result as a uint8 PNG to this path.
        denoise_h:           NLM filter strength (default 10.0).
        denoise_template_win: NLM template window size (default 7).
        denoise_search_win:  NLM search window size (default 21).
        clahe_clip_limit:    CLAHE contrast limit (default 2.0).
        clahe_tile_grid:     CLAHE tile grid size (default (8, 8)).
        enhance_amount:      Unsharp mask strength (default 1.0).
                             0.0 = no enhancement, 2.0 = strong sharpening.
        enhance_sigma:       Gaussian sigma for unsharp mask (default 1.0).

    Returns:
        Fully preprocessed sonar image as float32 ndarray (H, W) in [0, 1].

    Raises:
        TypeError:         If image type is unsupported.
        ValueError:        If image is empty, unreadable, or invalid shape.
        FileNotFoundError: If a path is provided but file does not exist.
        IOError:           If the image file cannot be decoded by OpenCV.

    Example:
        >>> import numpy as np
        >>> from ml.preprocessing import preprocess_image_full
        >>> img = np.random.randint(50, 200, (512, 512), dtype=np.uint8)
        >>> result = preprocess_image_full(img)
        >>> result.dtype
        dtype('float32')
        >>> 0.0 <= float(result.min()) and float(result.max()) <= 1.0
        True
    """
    # -------------------------------------------------------------------
    # Phase 1 steps (reuse existing internal functions)
    # -------------------------------------------------------------------
    raw = _load_as_grayscale(image)

    denoised = denoise(
        raw,
        h=denoise_h,
        template_win_size=denoise_template_win,
        search_win_size=denoise_search_win,
    )

    # normalize_uint8 = CLAHE only, returns uint8 for Phase 2 enhancement
    clahe_uint8 = normalize_uint8(
        denoised,
        clip_limit=clahe_clip_limit,
        tile_grid_size=clahe_tile_grid,
    )

    # -------------------------------------------------------------------
    # Phase 2: Enhancement (unsharp masking at uint8 stage)
    # -------------------------------------------------------------------
    enhanced = _enhance(
        clahe_uint8,
        amount=enhance_amount,
        sigma=enhance_sigma,
    )

    # -------------------------------------------------------------------
    # Phase 2: Final scaling to float32 [0, 1]
    # (same min-max logic as normalize_float, applied to enhanced image)
    # -------------------------------------------------------------------
    arr = enhanced.astype(np.float32)
    mn, mx = float(arr.min()), float(arr.max())

    if mx - mn < 1e-6:
        normalized = np.zeros_like(arr, dtype=np.float32)
    else:
        normalized = ((arr - mn) / (mx - mn)).astype(np.float32)

    # -------------------------------------------------------------------
    # Optional: save to disk
    # -------------------------------------------------------------------
    if output_path is not None:
        _save_preprocessed(normalized, Path(output_path))

    return normalized

