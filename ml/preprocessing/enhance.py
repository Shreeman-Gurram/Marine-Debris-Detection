"""
ml/preprocessing/enhance.py
============================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 2: Sonar Enhancement + Tiling

Sonar image contrast enhancement module.

Why Unsharp Masking (not another CLAHE)
-----------------------------------------
Phase 1 already applies CLAHE inside normalize_float(). Applying CLAHE again
in Phase 2 would double-equalize the histogram and risk creating artificial
gradient patterns that do not correspond to real sonar features.

Unsharp masking is COMPLEMENTARY to CLAHE:
  - CLAHE (Phase 1): equalizes local contrast across the swath gradient
  - Unsharp mask (Phase 2): sharpens the edges/boundaries that CLAHE revealed

This two-step order ΓÇö equalize THEN sharpen ΓÇö is standard practice in
sonar and medical image preprocessing pipelines.

Method: Unsharp Masking
-----------------------
    sharpened = clip(original + amount * (original - GaussianBlur(original)), 0, 255)

The Gaussian blur produces a smoothed version of the image. Subtracting it
from the original isolates high-frequency components (edges, fine details).
Adding a scaled version of these back to the original amplifies them.

For SSS sonar:
  - Sharpens acoustic shadow boundaries ΓåÆ clearer shipwreck / pipeline edges
  - Enhances specular highlight shapes
  - Does not amplify uniform seabed noise (low-frequency ΓåÆ blurred away)

Parameters (all configurable):
  amount ΓÇö strength of sharpening (default 1.0; range 0.5ΓÇô2.0 for SSS)
  sigma  ΓÇö Gaussian blur kernel sigma; controls which frequencies are sharpened
           Larger sigma ΓåÆ sharpens broader structures (default 1.0)

Input/Output:
  Input:  numpy.ndarray ΓÇö uint8, shape (H, W) grayscale
  Output: numpy.ndarray ΓÇö uint8, shape (H, W), values in [0, 255]
"""

import cv2
import numpy as np


def enhance(
    image: np.ndarray,
    amount: float = 1.0,
    sigma: float = 1.0,
) -> np.ndarray:
    """
    Apply unsharp masking to a denoised, normalized sonar image.

    Sharpens acoustic shadow boundaries and specular target edges without
    amplifying speckle noise. Designed to run AFTER Phase 1 denoising and
    CLAHE normalization, on a uint8 grayscale image.

    Args:
        image:  Grayscale sonar image, dtype uint8, shape (H, W).
                Should be the output of normalize_uint8() from Phase 1.
        amount: Sharpening strength. Multiplier for the high-frequency
                component. Default 1.0.
                  - 0.0 ΓåÆ no effect (returns input unchanged)
                  - 0.5 ΓåÆ subtle sharpening
                  - 1.0 ΓåÆ standard (recommended for SSS)
                  - 2.0 ΓåÆ aggressive sharpening
        sigma:  Gaussian blur kernel standard deviation (pixels). Controls
                the spatial scale of features to sharpen. Default 1.0.
                  - 0.5ΓÇô1.0 ΓåÆ sharpen fine boundaries (shadow edges)
                  - 1.5ΓÇô2.0 ΓåÆ sharpen broader structures (large wrecks)

    Returns:
        Sharpened grayscale sonar image as uint8 ndarray, shape (H, W).
        Values are clipped to [0, 255].

    Raises:
        TypeError:  If image is not a numpy.ndarray.
        ValueError: If image is empty, not uint8, or not 2D grayscale.
        ValueError: If amount < 0 or sigma <= 0.

    Example:
        >>> import numpy as np
        >>> img = np.random.randint(50, 200, (256, 256), dtype=np.uint8)
        >>> sharpened = enhance(img, amount=1.0, sigma=1.0)
        >>> sharpened.shape == img.shape
        True
        >>> sharpened.dtype
        dtype('uint8')
    """
    _validate_enhance_input(image, amount, sigma)

    if amount == 0.0:
        # No-op shortcut
        return image.copy()

    # Compute blurred version ΓÇö determines which frequencies are amplified
    # Kernel size is derived from sigma: 6*sigma+1, rounded to odd number
    ksize = _sigma_to_ksize(sigma)
    blurred = cv2.GaussianBlur(image, (ksize, ksize), sigmaX=sigma, sigmaY=sigma)

    # Unsharp mask formula: original + amount * (original - blurred)
    # Use float32 for intermediate to avoid uint8 overflow
    img_f = image.astype(np.float32)
    blur_f = blurred.astype(np.float32)

    sharpened_f = img_f + amount * (img_f - blur_f)

    # Clip back to valid uint8 range
    sharpened = np.clip(sharpened_f, 0.0, 255.0).astype(np.uint8)

    return sharpened


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_enhance_input(
    image: np.ndarray,
    amount: float,
    sigma: float,
) -> None:
    """Validate inputs for the enhance() function."""
    if not isinstance(image, np.ndarray):
        raise TypeError(
            f"enhance() expects a numpy.ndarray, got {type(image).__name__}."
        )
    if image.size == 0:
        raise ValueError(
            "enhance() received an empty image (size == 0)."
        )
    if image.ndim != 2:
        raise ValueError(
            f"enhance() expects a 2D grayscale image (H, W), "
            f"got ndim={image.ndim}, shape={image.shape}. "
            "Convert to grayscale before enhancing."
        )
    if image.dtype != np.uint8:
        raise ValueError(
            f"enhance() expects uint8 input, got dtype={image.dtype}. "
            "Pass the output of normalize_uint8() from Phase 1."
        )
    if amount < 0:
        raise ValueError(
            f"amount must be >= 0, got {amount}."
        )
    if sigma <= 0:
        raise ValueError(
            f"sigma must be > 0, got {sigma}."
        )


def _sigma_to_ksize(sigma: float) -> int:
    """Compute a suitable odd Gaussian kernel size from sigma.

    Uses the standard rule: ksize = ceil(6 * sigma), rounded to odd.
    Minimum kernel size is 3.
    """
    raw = int(round(6.0 * sigma))
    raw = max(raw, 3)
    # Ensure odd (OpenCV requirement for GaussianBlur)
    if raw % 2 == 0:
        raw += 1
    return raw
