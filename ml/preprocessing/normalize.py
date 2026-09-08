"""
ml/preprocessing/normalize.py
==============================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 1: Sonar Preprocessing Foundation

Sonar image intensity normalization module.

P2 (Data Engineering) has confirmed that NO pixel-level normalization was
applied to the DRISHTI-SSS dataset. Images are stored with their original
intensity distributions. SSS images often have:
  - High-intensity highlights (hard reflectors: metal, rock)
  - Low-intensity shadows (acoustic shadow zones behind objects)
  - Strong intensity gradients from near-range to far-range
  - Uneven illumination across the swath

Method 1: CLAHE (Contrast Limited Adaptive Histogram Equalization)
-------------------------------------------------------------------
CLAHE is an extension of histogram equalization that operates on small
local tiles rather than the global image. The contrast limit prevents
over-amplification of noise in uniform regions.

Advantages for SSS:
  - Enhances local contrast, making anomaly boundaries more visible
  - Handles the large intensity gradient from near-range to far-range
  - Does not clip highlights or crush shadows as aggressively as global HE
  - Standard in sonar and medical image preprocessing literature

Parameters:
  clip_limit    ΓÇö Threshold for contrast limiting (default 2.0)
                  Higher values allow more contrast enhancement.
  tile_grid_size ΓÇö Size of grid for CLAHE (default (8, 8))

Method 2: Min-Max Normalization ΓåÆ float32 [0.0, 1.0]
------------------------------------------------------
After CLAHE, the image is converted to float32 and scaled to [0.0, 1.0].
This gives the ML pipeline (P1) a consistent intensity range regardless
of the original image's absolute intensity values.

Input/Output:
  normalize_clahe():    uint8 (H,W) ΓåÆ uint8 (H,W)    CLAHE only
  normalize_float():    uint8 (H,W) ΓåÆ float32 (H,W)   CLAHE + min-max
  normalize_uint8():    uint8 (H,W) ΓåÆ uint8 (H,W)    CLAHE + rescale back
"""

import cv2
import numpy as np


def normalize_clahe(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Apply CLAHE to a grayscale sonar image.

    Enhances local contrast across the sonar swath without global
    over-amplification of noise. Input must be grayscale uint8.

    Args:
        image:          Grayscale sonar image, dtype uint8, shape (H, W).
        clip_limit:     Contrast limiting threshold. Higher values allow
                        stronger enhancement. Default: 2.0.
        tile_grid_size: Grid size for adaptive histogram computation.
                        Default: (8, 8).

    Returns:
        CLAHE-enhanced grayscale image, dtype uint8, shape (H, W).

    Raises:
        TypeError:  If image is not a numpy.ndarray.
        ValueError: If image is empty, not uint8, or not 2D grayscale.
    """
    _validate_grayscale_uint8(image)

    clahe = cv2.createCLAHE(
        clipLimit=float(clip_limit),
        tileGridSize=tile_grid_size,
    )
    return clahe.apply(image)


def normalize_float(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Apply CLAHE then scale to float32 [0.0, 1.0].

    This is the primary normalization used by the P3 preprocessing
    pipeline. The float32 [0,1] output is the standard format for
    downstream ML and analysis steps.

    Args:
        image:          Grayscale sonar image, dtype uint8, shape (H, W).
        clip_limit:     CLAHE contrast limiting threshold. Default: 2.0.
        tile_grid_size: CLAHE tile grid size. Default: (8, 8).

    Returns:
        Normalized sonar image as float32 ndarray, shape (H, W),
        values in [0.0, 1.0].

    Raises:
        TypeError:  If image is not a numpy.ndarray.
        ValueError: If image is empty, not uint8, or not 2D grayscale.

    Example:
        >>> import numpy as np
        >>> img = np.random.randint(0, 256, (128, 128), dtype=np.uint8)
        >>> out = normalize_float(img)
        >>> out.dtype
        dtype('float32')
        >>> float(out.min()) >= 0.0 and float(out.max()) <= 1.0
        True
    """
    # Apply CLAHE first for local contrast enhancement
    enhanced = normalize_clahe(image, clip_limit=clip_limit, tile_grid_size=tile_grid_size)

    # Min-max scale to [0, 1] with epsilon guard against zero-range images
    arr = enhanced.astype(np.float32)
    mn, mx = float(arr.min()), float(arr.max())

    if mx - mn < 1e-6:
        # Uniform image (e.g., all-black background) ΓÇö return zeros
        return np.zeros_like(arr, dtype=np.float32)

    arr = (arr - mn) / (mx - mn)
    return arr.astype(np.float32)


def normalize_uint8(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Apply CLAHE and return a uint8 image (for visualization / saving).

    Use this when you need to write the normalized image to disk as
    a standard image file (PNG/JPEG), or display it with OpenCV/matplotlib.

    Args:
        image:          Grayscale sonar image, dtype uint8, shape (H, W).
        clip_limit:     CLAHE contrast limiting threshold. Default: 2.0.
        tile_grid_size: CLAHE tile grid size. Default: (8, 8).

    Returns:
        CLAHE-enhanced image as uint8 ndarray, shape (H, W).

    Raises:
        TypeError:  If image is not a numpy.ndarray.
        ValueError: If image is empty, not uint8, or not 2D grayscale.
    """
    # CLAHE already returns uint8, so this is just a named alias
    # with explicit documentation intent
    return normalize_clahe(image, clip_limit=clip_limit, tile_grid_size=tile_grid_size)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_grayscale_uint8(image: np.ndarray) -> None:
    """Validate that image is a non-empty 2D uint8 grayscale numpy array."""
    if not isinstance(image, np.ndarray):
        raise TypeError(
            f"Expected numpy.ndarray, got {type(image).__name__}."
        )
    if image.size == 0:
        raise ValueError(
            "Image array is empty (size == 0). Cannot normalize an empty image."
        )
    if image.ndim != 2:
        raise ValueError(
            f"normalize() expects a 2D grayscale image (H, W), "
            f"got ndim={image.ndim}, shape={image.shape}. "
            "Convert to grayscale before normalizing."
        )
    if image.dtype != np.uint8:
        raise ValueError(
            f"normalize() expects uint8 input, got dtype={image.dtype}. "
            "Ensure image is uint8 before normalizing."
        )
