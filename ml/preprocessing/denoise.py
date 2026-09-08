"""
ml/preprocessing/denoise.py
============================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 1: Sonar Preprocessing Foundation

Sonar image denoising module.

Side-Scan Sonar (SSS) images exhibit speckle noise ΓÇö a coherent imaging
artifact caused by interference of sound waves reflecting off the seabed.
This module reduces speckle while preserving useful structures such as
shipwreck outlines, pipeline shadows, and net patterns.

Method: Non-Local Means Denoising (cv2.fastNlMeansDenoising)
---------------------------------------------------------------
Non-local means (NLM) works by averaging pixel values from patches that are
similar to the patch around each target pixel, across the whole image.
This makes it effective at:
  - Reducing random speckle noise
  - Preserving edge-like sonar targets (shadows, highlights)
  - Avoiding the over-blurring seen with Gaussian or median filters

Reference: Buades, Coll, Morel (2005) ΓÇö "A Non-Local Algorithm for Image
Denoising", CVPR 2005.

Parameters (all configurable):
  h                  ΓÇö Filter strength (higher = more smoothing, less detail)
                       Recommended range: 5ΓÇô15 for SSS images
  template_win_size  ΓÇö Size of patch compared for similarity (odd number)
  search_win_size    ΓÇö Size of search window (odd number, > template_win_size)

Input/Output:
  Input:  numpy.ndarray ΓÇö uint8, shape (H, W) grayscale or (H, W, 3) BGR
  Output: numpy.ndarray ΓÇö uint8, same shape as input
"""

import cv2
import numpy as np


def denoise(
    image: np.ndarray,
    h: float = 10.0,
    template_win_size: int = 7,
    search_win_size: int = 21,
) -> np.ndarray:
    """
    Apply Non-Local Means denoising to a sonar image.

    Reduces speckle noise while preserving sonar target structures.
    Works on grayscale (H, W) or 3-channel BGR (H, W, 3) uint8 images.
    For 3-channel images, channels are processed independently via
    cv2.fastNlMeansDenoisingColored, which is appropriate when the image
    is a sonar scan stored as a colour image (identical or near-identical
    channels).

    Args:
        image:             Input sonar image as a numpy uint8 array.
                           Shape must be (H, W) or (H, W, 3).
        h:                 Filter strength parameter. Controls the degree
                           of smoothing. Higher values remove more noise
                           but may blur fine structures. Default: 10.0.
        template_win_size: Side length of the patch window (pixels, odd).
                           Default: 7.
        search_win_size:   Side length of the search window (pixels, odd).
                           Must be > template_win_size. Default: 21.

    Returns:
        Denoised image as a numpy uint8 array with the same shape as input.

    Raises:
        TypeError:  If image is not a numpy.ndarray.
        ValueError: If image is empty, has wrong dtype, or unsupported shape.

    Example:
        >>> import numpy as np
        >>> img = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
        >>> denoised = denoise(img)
        >>> denoised.shape == img.shape
        True
    """
    _validate_image(image)

    if image.dtype != np.uint8:
        raise ValueError(
            f"denoise() expects a uint8 image, got dtype={image.dtype}. "
            "Convert to uint8 before denoising."
        )

    # Enforce odd window sizes (OpenCV requirement)
    template_win_size = _ensure_odd(template_win_size)
    search_win_size = _ensure_odd(search_win_size)

    if search_win_size <= template_win_size:
        search_win_size = template_win_size + 14  # ensure search > template

    ndim = image.ndim

    if ndim == 2:
        # Grayscale sonar image ΓÇö standard path
        denoised = cv2.fastNlMeansDenoising(
            src=image,
            h=float(h),
            templateWindowSize=template_win_size,
            searchWindowSize=search_win_size,
        )
    elif ndim == 3 and image.shape[2] == 3:
        # 3-channel BGR image (SSS stored as colour)
        denoised = cv2.fastNlMeansDenoisingColored(
            src=image,
            h=float(h),
            hColor=float(h),
            templateWindowSize=template_win_size,
            searchWindowSize=search_win_size,
        )
    else:
        raise ValueError(
            f"Unsupported image shape: {image.shape}. "
            "Expected (H, W) grayscale or (H, W, 3) BGR."
        )

    return denoised


def _validate_image(image: np.ndarray) -> None:
    """Shared input validation for sonar image arrays."""
    if not isinstance(image, np.ndarray):
        raise TypeError(
            f"Expected a numpy.ndarray, got {type(image).__name__}."
        )
    if image.size == 0:
        raise ValueError(
            "Image array is empty (size == 0). Cannot process an empty image."
        )
    if image.ndim not in (2, 3):
        raise ValueError(
            f"Image must be 2D (H, W) or 3D (H, W, C), got ndim={image.ndim}."
        )


def _ensure_odd(value: int) -> int:
    """Return value if odd, else value + 1."""
    return value if value % 2 == 1 else value + 1
