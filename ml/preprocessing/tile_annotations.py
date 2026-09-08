"""
ml/preprocessing/tile_annotations.py
======================================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 2: Sonar Enhancement + Tiling

YOLO annotation coordinate transformation for sonar image tiles.

Why This Is Needed
-------------------
When a large sonar image is tiled (see tiler.py), the YOLO bounding-box
annotations from P2 (which are normalized relative to the FULL image size)
must be transformed to be normalized relative to each TILE's size.

Without this transformation, P1 would try to train with coordinates that
point to the wrong regions of each tile.

Coordinate System
-----------------
YOLO format (P2's annotations):
    class_id  cx  cy  w  h
    - cx, cy: center x, center y ΓÇö normalized [0, 1] relative to full image
    - w, h:   box width, height ΓÇö normalized [0, 1] relative to full image

After transformation (tile-local YOLO format):
    class_id  cx  cy  w  h
    - cx, cy: center x, center y ΓÇö normalized [0, 1] relative to TILE
    - w, h:   box width, height ΓÇö normalized [0, 1] relative to TILE

Transformation Steps (per annotation per tile):
    1. Convert YOLO normalized ΓåÆ absolute pixel coords in full image
       x1 = (cx - w/2) * image_w
       y1 = (cy - h/2) * image_h
       x2 = (cx + w/2) * image_w
       y2 = (cy + h/2) * image_h

    2. Compute intersection with tile region
       tx1 = max(x1, tile.x_offset)
       ty1 = max(y1, tile.y_offset)
       tx2 = min(x2, tile.x_offset + tile.tile_w)
       ty2 = min(y2, tile.y_offset + tile.tile_h)

    3. Skip if no intersection or area ratio too small
       original_area = (x2 - x1) * (y2 - y1)
       clipped_area  = (tx2 - tx1) * (ty2 - ty1)
       if clipped_area / original_area < min_area_ratio: skip

    4. Convert to tile-local normalized coords
       local_cx = (tx1 + tx2) / 2 - tile.x_offset  ΓåÆ divide by tile.tile_w
       local_cy = (ty1 + ty2) / 2 - tile.y_offset  ΓåÆ divide by tile.tile_h
       local_w  = (tx2 - tx1) / tile.tile_w
       local_h  = (ty2 - ty1) / tile.tile_h

Partial Object Rule (min_area_ratio = 0.25 default)
-----------------------------------------------------
Objects whose visible area in a tile is less than 25% of their original
area are excluded from that tile's labels. This prevents training on tiny
slivers of objects that provide no useful detection signal.

  Objects crossing a tile boundary appear in BOTH tiles ΓÇö this is
  intentional and correct. Overlap is designed to ensure most objects
  appear fully in at least one tile.

P1 Safety
---------
This module is STANDALONE. It is not called by P1's training pipeline.
P1 continues to use `C:\\drishti_clean` directly.
This module is invoked only when explicitly generating a tiled dataset.
"""

from __future__ import annotations

from typing import List, Tuple

from .tiler import TileInfo


# Type alias for a parsed YOLO annotation row
# (class_id, cx, cy, w, h) ΓÇö all floats, coords normalized 0ΓÇô1
_Annotation = Tuple[int, float, float, float, float]


def transform_annotations(
    yolo_label_lines: List[str],
    image_h: int,
    image_w: int,
    tile_info: TileInfo,
    min_area_ratio: float = 0.25,
) -> List[str]:
    """
    Transform full-image YOLO annotations to tile-local YOLO annotations.

    For each annotation in the full image, determines whether it intersects
    the given tile and, if so, produces a tile-local YOLO annotation string.

    Args:
        yolo_label_lines: List of raw YOLO annotation strings from a .txt
                          label file. Each line format:
                          "class_id cx cy w h"  (space-separated, normalized)
                          Blank lines and malformed lines are skipped safely.
        image_h:          Full image height in pixels (before tiling).
        image_w:          Full image width in pixels (before tiling).
        tile_info:        TileInfo named tuple from tile_image(). Provides
                          tile dimensions and offset within the full image.
        min_area_ratio:   Minimum fraction of the original bounding box area
                          that must be visible within the tile to include the
                          annotation. Default 0.25 (25%).
                          Set to 0.0 to include all intersecting annotations.
                          Set to 1.0 to include only fully-contained boxes.

    Returns:
        List of YOLO annotation strings (same format as input) normalized
        to the tile's coordinate space. Empty list if no annotations
        intersect this tile above the area threshold.
        Returns empty list if input is empty (valid negative tile sample).

    Raises:
        ValueError: If image_h or image_w <= 0, or tile dimensions invalid.
        ValueError: If min_area_ratio is not in [0, 1].

    Example:
        >>> from ml.preprocessing.tiler import TileInfo
        >>> import numpy as np
        >>> tile = TileInfo(
        ...     tile=np.zeros((640, 640), dtype=np.float32),
        ...     row=0, col=0, x_offset=0, y_offset=0, tile_h=640, tile_w=640
        ... )
        >>> labels = ["2 0.5 0.5 0.4 0.3"]   # shipwreck, centered in image
        >>> result = transform_annotations(labels, 640, 640, tile)
        >>> len(result) == 1
        True
    """
    _validate_transform_inputs(image_h, image_w, tile_info, min_area_ratio)

    if not yolo_label_lines:
        return []

    tile_x0 = tile_info.x_offset
    tile_y0 = tile_info.y_offset
    tile_x1 = tile_x0 + tile_info.tile_w
    tile_y1 = tile_y0 + tile_info.tile_h

    results: List[str] = []

    for raw_line in yolo_label_lines:
        line = raw_line.strip()
        if not line:
            continue

        parsed = _parse_yolo_line(line)
        if parsed is None:
            # Malformed line ΓÇö skip silently (P2 already validated annotations)
            continue

        class_id, cx_norm, cy_norm, w_norm, h_norm = parsed

        # Step 1: Convert to absolute pixel coords in full image
        x1 = (cx_norm - w_norm / 2.0) * image_w
        y1 = (cy_norm - h_norm / 2.0) * image_h
        x2 = (cx_norm + w_norm / 2.0) * image_w
        y2 = (cy_norm + h_norm / 2.0) * image_h

        orig_area = max(0.0, (x2 - x1) * (y2 - y1))
        if orig_area <= 0:
            continue

        # Step 2: Intersect with tile region
        ix1 = max(x1, tile_x0)
        iy1 = max(y1, tile_y0)
        ix2 = min(x2, tile_x1)
        iy2 = min(y2, tile_y1)

        if ix2 <= ix1 or iy2 <= iy1:
            # No intersection with this tile
            continue

        # Step 3: Area ratio check
        clip_area = (ix2 - ix1) * (iy2 - iy1)
        if clip_area / orig_area < min_area_ratio:
            continue

        # Step 4: Convert to tile-local normalized coordinates
        local_cx = ((ix1 + ix2) / 2.0 - tile_x0) / tile_info.tile_w
        local_cy = ((iy1 + iy2) / 2.0 - tile_y0) / tile_info.tile_h
        local_w  = (ix2 - ix1) / tile_info.tile_w
        local_h  = (iy2 - iy1) / tile_info.tile_h

        # Clamp to [0, 1] (safety ΓÇö should already be valid given intersection check)
        local_cx = float(max(0.0, min(1.0, local_cx)))
        local_cy = float(max(0.0, min(1.0, local_cy)))
        local_w  = float(max(0.0, min(1.0, local_w)))
        local_h  = float(max(0.0, min(1.0, local_h)))

        if local_w <= 0 or local_h <= 0:
            continue

        results.append(
            f"{class_id} {local_cx:.6f} {local_cy:.6f} "
            f"{local_w:.6f} {local_h:.6f}"
        )

    return results


def load_yolo_labels(label_path) -> List[str]:
    """
    Read a YOLO label .txt file and return its non-empty lines.

    Args:
        label_path: Path to YOLO .txt annotation file (str or pathlib.Path).
                    Returns empty list if the file does not exist (valid
                    negative sample / background image).

    Returns:
        List of stripped annotation strings. Empty list for missing files
        or files with no valid annotations.
    """
    from pathlib import Path
    path = Path(label_path)
    if not path.exists():
        return []
    lines = [line.strip() for line in path.read_text().splitlines()]
    return [line for line in lines if line]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_yolo_line(line: str):
    """
    Parse a single YOLO annotation line.

    Returns (class_id, cx, cy, w, h) or None if malformed.
    """
    parts = line.split()
    if len(parts) != 5:
        return None
    try:
        class_id = int(parts[0])
        cx = float(parts[1])
        cy = float(parts[2])
        w  = float(parts[3])
        h  = float(parts[4])
    except ValueError:
        return None

    # Sanity check: YOLO coords must be in (0, 1]
    if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < w <= 1 and 0 < h <= 1):
        return None

    return class_id, cx, cy, w, h


def _validate_transform_inputs(
    image_h: int,
    image_w: int,
    tile_info: TileInfo,
    min_area_ratio: float,
) -> None:
    """Validate inputs to transform_annotations()."""
    if image_h <= 0 or image_w <= 0:
        raise ValueError(
            f"image_h and image_w must be positive, "
            f"got image_h={image_h}, image_w={image_w}."
        )
    if tile_info.tile_h <= 0 or tile_info.tile_w <= 0:
        raise ValueError(
            f"tile_info has invalid tile dimensions: "
            f"tile_h={tile_info.tile_h}, tile_w={tile_info.tile_w}."
        )
    if not (0.0 <= min_area_ratio <= 1.0):
        raise ValueError(
            f"min_area_ratio must be in [0.0, 1.0], got {min_area_ratio}."
        )
