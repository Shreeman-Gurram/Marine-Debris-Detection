"""
ml/preprocessing/tiler.py
==========================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 2: Sonar Enhancement + Tiling

Sonar image tiling module.

Why Tile SSS Images?
---------------------
Side-Scan Sonar images are often much larger than YOLO's native 640├ù640
input size. Training YOLO on full-resolution large images causes:
  - Downsampling that loses small object detail (ghost nets, mine cylinders)
  - High GPU memory usage

Tiling decomposes the full image into 640├ù640 patches that YOLO can consume
without internal downsampling, preserving spatial detail of small objects.

Tile Size: 640 ├ù 640
---------------------
YOLOv8/v11 native input size. Using the same size means:
  - P1 can use tiles without resizing
  - Spatial resolution is fully preserved
  - No mismatch between training and inference tile sizes

Overlap: 64 pixels (default, 10% of 640)
------------------------------------------
Overlap ensures objects near tile boundaries appear fully in at least one
tile. Without overlap, objects cut exactly at a boundary would be invisible
to the detector in both tiles.

Edge Handling: Reflect Padding
--------------------------------
Images whose dimensions are not multiples of (tile_size - overlap) need
padding at the right/bottom edges. We use cv2.BORDER_REFLECT_101, which
mirrors the image content rather than padding with zeros. This avoids:
  - Dark artificial borders that could train the detector to ignore edges
  - Uniform-value padding that distorts normalization statistics

Output Format
-------------
tile_image() returns a list of TileInfo named tuples, each containing:
  - tile:     float32 (tile_h, tile_w) array, values [0, 1]
  - row:      row index of tile (0-based)
  - col:      col index of tile (0-based)
  - x_offset: left edge of this tile in the original image (before padding)
  - y_offset: top edge of this tile in the original image (before padding)
  - tile_h:   height of tile in pixels
  - tile_w:   width of tile in pixels

Naming Convention (for saving tiles to disk):
  {original_stem}_tile_{row:03d}_{col:03d}.png
"""

from __future__ import annotations

from typing import NamedTuple, List

import cv2
import numpy as np


class TileInfo(NamedTuple):
    """
    Metadata for a single tile extracted from a sonar image.

    Attributes:
        tile:     float32 numpy array (tile_h, tile_w), values in [0.0, 1.0].
        row:      Zero-based row index of this tile in the tile grid.
        col:      Zero-based column index of this tile in the tile grid.
        x_offset: Left edge (in pixels) of this tile in the ORIGINAL image
                  coordinate space (before any padding). Used for annotation
                  transformation. May be negative if the tile extends beyond
                  the left edge (only possible with overlap > 0 on first tile,
                  which does not happen in this implementation).
        y_offset: Top edge (in pixels) of this tile in the ORIGINAL image
                  coordinate space (before any padding).
        tile_h:   Height of this tile in pixels.
        tile_w:   Width of this tile in pixels.
    """
    tile: np.ndarray
    row: int
    col: int
    x_offset: int
    y_offset: int
    tile_h: int
    tile_w: int


def tile_image(
    image: np.ndarray,
    tile_h: int = 640,
    tile_w: int = 640,
    overlap: int = 64,
) -> List[TileInfo]:
    """
    Decompose a preprocessed sonar image into overlapping tiles.

    Takes a float32 [0, 1] grayscale image (output of preprocess_image_full)
    and produces a list of overlapping tiles of size tile_h ├ù tile_w.

    Images smaller than the requested tile size in either dimension are
    padded to fill exactly one tile. Images larger are decomposed into a
    grid of overlapping tiles, with reflect-padding at the edges.

    Args:
        image:    Preprocessed sonar image. dtype must be float32, shape
                  (H, W), values in [0.0, 1.0]. This is the output of
                  preprocess_image_full() from pipeline.py.
        tile_h:   Height of each tile in pixels. Default 640 (YOLO native).
        tile_w:   Width of each tile in pixels. Default 640 (YOLO native).
        overlap:  Number of pixels each tile overlaps with its neighbours.
                  Default 64 (10% of 640). Must be < tile_h and < tile_w.

    Returns:
        List of TileInfo named tuples, one per tile, in row-major order
        (left-to-right, top-to-bottom). Each tile is a float32 (tile_h, tile_w)
        array with values in [0.0, 1.0].

    Raises:
        TypeError:  If image is not a numpy.ndarray.
        ValueError: If image is empty, not float32, not 2D, or parameters
                    are invalid.

    Example:
        >>> import numpy as np
        >>> img = np.random.rand(800, 1200).astype(np.float32)
        >>> tiles = tile_image(img, tile_h=640, tile_w=640, overlap=64)
        >>> all(t.tile.shape == (640, 640) for t in tiles)
        True
        >>> all(t.tile.dtype == np.float32 for t in tiles)
        True
    """
    _validate_tile_input(image, tile_h, tile_w, overlap)

    H, W = image.shape
    stride_h = tile_h - overlap
    stride_w = tile_w - overlap

    # -----------------------------------------------------------------
    # Pad image so that tiles cover the full image without partial edges
    # -----------------------------------------------------------------
    pad_h = _required_padding(H, tile_h, stride_h)
    pad_w = _required_padding(W, tile_w, stride_w)

    if pad_h > 0 or pad_w > 0:
        # Convert to uint8 for cv2.copyMakeBorder, then back
        img_u8 = (image * 255.0).clip(0, 255).astype(np.uint8)
        img_padded_u8 = cv2.copyMakeBorder(
            img_u8,
            top=0, bottom=pad_h,
            left=0, right=pad_w,
            borderType=cv2.BORDER_REFLECT_101,
        )
        padded = img_padded_u8.astype(np.float32) / 255.0
    else:
        padded = image

    padded_H, padded_W = padded.shape

    # -----------------------------------------------------------------
    # Extract tiles
    # -----------------------------------------------------------------
    tiles: List[TileInfo] = []
    row_idx = 0

    y = 0
    while y + tile_h <= padded_H:
        col_idx = 0
        x = 0
        while x + tile_w <= padded_W:
            tile_array = padded[y : y + tile_h, x : x + tile_w].copy()

            tiles.append(TileInfo(
                tile=tile_array,
                row=row_idx,
                col=col_idx,
                x_offset=x,
                y_offset=y,
                tile_h=tile_h,
                tile_w=tile_w,
            ))

            col_idx += 1
            x += stride_w

        row_idx += 1
        y += stride_h

    return tiles


def tile_filename(stem: str, row: int, col: int) -> str:
    """
    Generate the standard filename for a tile.

    Args:
        stem: Original image filename without extension (e.g. "survey_001").
        row:  Zero-based row index.
        col:  Zero-based column index.

    Returns:
        Filename string (without directory) e.g. "survey_001_tile_000_001.png"
    """
    return f"{stem}_tile_{row:03d}_{col:03d}.png"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_tile_input(
    image: np.ndarray,
    tile_h: int,
    tile_w: int,
    overlap: int,
) -> None:
    """Validate inputs to tile_image()."""
    if not isinstance(image, np.ndarray):
        raise TypeError(
            f"tile_image() expects a numpy.ndarray, got {type(image).__name__}."
        )
    if image.size == 0:
        raise ValueError("tile_image() received an empty image (size == 0).")
    if image.ndim != 2:
        raise ValueError(
            f"tile_image() expects a 2D image (H, W), "
            f"got ndim={image.ndim}, shape={image.shape}."
        )
    if image.dtype != np.float32:
        raise ValueError(
            f"tile_image() expects float32 input (output of preprocess_image_full), "
            f"got dtype={image.dtype}."
        )
    if tile_h <= 0 or tile_w <= 0:
        raise ValueError(
            f"tile_h and tile_w must be positive, got tile_h={tile_h}, tile_w={tile_w}."
        )
    if overlap < 0:
        raise ValueError(f"overlap must be >= 0, got {overlap}.")
    if overlap >= tile_h:
        raise ValueError(
            f"overlap ({overlap}) must be less than tile_h ({tile_h})."
        )
    if overlap >= tile_w:
        raise ValueError(
            f"overlap ({overlap}) must be less than tile_w ({tile_w})."
        )


def _required_padding(dimension: int, tile_size: int, stride: int) -> int:
    """
    Calculate how many pixels to pad at the far edge so that tiles
    of size tile_size with the given stride exactly cover the dimension.

    Returns 0 if no padding is needed (dimension already fits perfectly).
    """
    if dimension <= tile_size:
        # Image fits in a single tile; pad to tile_size
        return max(0, tile_size - dimension)

    # How many complete strides fit?
    n_strides = (dimension - tile_size + stride - 1) // stride
    covered = tile_size + n_strides * stride
    return max(0, covered - dimension)
