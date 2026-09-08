"""
geolocation/sonar_geometry.py
==============================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 3: Geolocation Foundation

Sonar image coordinate ΓåÆ local physical coordinate conversion.

Side-Scan Sonar Geometry
--------------------------
A side-scan sonar (SSS) towfish emits acoustic pulses to both sides and
records the time-of-flight of returning echoes. The resulting image is a
2D waterfall where:

    Columns (X axis) = cross-track direction (range from nadir)
    Rows    (Y axis) = along-track direction (time / ping number)

Standard SSS image layout:
    ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
    Γöé ΓåÉ Port side Γöé  nadir  Γöé Starboard side ΓåÆ    Γöé
    Γöé  col 0      Γöé  col W/2Γöé              col W-1 Γöé
    ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
    Rows increase downward = towfish moves forward over time.

Coordinate conventions used in this module
--------------------------------------------
- Pixel (0, 0) is TOP-LEFT of image
- Nadir column = image_width / 2 (centre column)
- Left of nadir = port side   (negative local_x_m)
- Right of nadir = starboard  (positive local_x_m)
- range_m = swath half-range (nadir ΓåÆ far edge in metres)
- bearing_deg:  +90┬░ = starboard (right of nadir)
                ΓêÆ90┬░ = port (left of nadir)
  SSS always ensonifies 90┬░ off heading, so bearing is always ┬▒90┬░.
  Sub-metre angular resolution within the swath is not supported without
  explicit bearing-angle calibration tables (not in DRISHTI-SSS dataset).

Along-track limitation
-----------------------
Each image row corresponds to one acoustic ping. Without timestamps and
vessel speed, the along-track distance (local_y_m) cannot be computed.
It is set to 0.0 and flagged in the documentation. This is an honest
limitation of the dataset, not a code deficiency.

Equations
----------
    nadir_col_px      = image_width_px / 2.0
    pixel_from_nadir  = (cx_norm ├ù image_width_px) ΓêÆ nadir_col_px
    range_per_px      = range_m / nadir_col_px
    slant_range_m     = |pixel_from_nadir| ├ù range_per_px
    bearing_deg       = +90.0 if pixel_from_nadir ΓëÑ 0 else ΓêÆ90.0
    local_x_m         = pixel_from_nadir ├ù range_per_px
    local_y_m         = 0.0  (along-track unknown)

Object size estimation (cross-track extent):
    obj_half_width_px = (bbox_w_norm ├ù image_width_px) / 2.0
    obj_extent_m      = obj_half_width_px ├ù range_per_px
"""

from __future__ import annotations

import math

from .models import SonarMetadata


def pixel_to_sonar_coords(
    cx_norm: float,
    cy_norm: float,
    bbox_w_norm: float,
    metadata: SonarMetadata,
) -> tuple[float, float, float, float, float]:
    """
    Convert a detection's image-normalised centre to sonar local coordinates.

    This is the primary geometric transform for P3 geolocation. It converts
    YOLO-normalized bounding box centres into physically meaningful distances
    in metres from the sonar nadir.

    Args:
        cx_norm:    Bounding box centre x, normalized [0, 1].
                    0 = left edge (port), 1 = right edge (starboard).
        cy_norm:    Bounding box centre y, normalized [0, 1].
                    Used only for along-track (currently always 0).
        bbox_w_norm: Bounding box width, normalized [0, 1].
                     Used to estimate object cross-track extent.
        metadata:   SonarMetadata with image dimensions and range_m.

    Returns:
        Tuple of (slant_range_m, bearing_deg, local_x_m, local_y_m, extent_m):
            slant_range_m ΓÇö slant range from nadir to object centre (metres, ΓëÑ 0)
            bearing_deg   ΓÇö +90.0 (starboard) or ΓêÆ90.0 (port)
            local_x_m     ΓÇö signed cross-track distance (+= starboard, metres)
            local_y_m     ΓÇö along-track distance (always 0.0 ΓÇö unknown)
            extent_m      ΓÇö estimated cross-track extent of object (metres)

    Raises:
        ValueError: If metadata dimensions are invalid or range_m Γëñ 0.
        ValueError: If cx_norm, cy_norm, or bbox_w_norm are out of [0, 1].

    Example:
        >>> from geolocation.models import SonarMetadata
        >>> meta = SonarMetadata(image_width_px=1024, image_height_px=512, range_m=50.0)
        >>> rng, bearing, lx, ly, ext = pixel_to_sonar_coords(0.75, 0.5, 0.05, meta)
        >>> round(rng, 2)
        12.5
        >>> bearing
        90.0
        >>> round(lx, 2)
        12.5
        >>> ly
        0.0
    """
    _validate_metadata(metadata)
    _validate_norm_coords(cx_norm, cy_norm, bbox_w_norm)

    W = float(metadata.image_width_px)
    nadir_col_px = W / 2.0
    range_per_px = metadata.effective_range_resolution()

    # Signed pixel offset from nadir (+ = starboard, ΓêÆ = port)
    pixel_from_nadir = (cx_norm * W) - nadir_col_px

    slant_range_m = abs(pixel_from_nadir) * range_per_px
    local_x_m = pixel_from_nadir * range_per_px
    local_y_m = 0.0  # along-track: unavailable without timestamps

    # SSS bearing: 90┬░ off heading on each side
    bearing_deg = 90.0 if pixel_from_nadir >= 0.0 else -90.0

    # Object cross-track extent
    obj_half_width_px = (bbox_w_norm * W) / 2.0
    extent_m = obj_half_width_px * range_per_px

    return slant_range_m, bearing_deg, local_x_m, local_y_m, extent_m


def pixel_localization_uncertainty_m(
    bbox_w_norm: float,
    metadata: SonarMetadata,
) -> float:
    """
    Estimate the pixel-localization contribution to positional uncertainty.

    This represents the uncertainty due to not knowing exactly where within
    the bounding box the object's acoustic centre lies. Taken as half the
    bounding-box width in the cross-track direction.

    Args:
        bbox_w_norm: Bounding box width, normalized [0, 1].
        metadata:    SonarMetadata (for range resolution).

    Returns:
        Position uncertainty contribution in metres (ΓëÑ 0).
    """
    range_per_px = metadata.effective_range_resolution()
    W = float(metadata.image_width_px)
    obj_half_width_px = (bbox_w_norm * W) / 2.0
    return obj_half_width_px * range_per_px


# ---------------------------------------------------------------------------
# Internal validation helpers
# ---------------------------------------------------------------------------

def _validate_metadata(metadata: SonarMetadata) -> None:
    """Validate SonarMetadata fields required for geometry computation."""
    if not isinstance(metadata, SonarMetadata):
        raise TypeError(
            f"Expected SonarMetadata, got {type(metadata).__name__}."
        )
    if metadata.image_width_px <= 0:
        raise ValueError(
            f"image_width_px must be > 0, got {metadata.image_width_px}."
        )
    if metadata.image_height_px <= 0:
        raise ValueError(
            f"image_height_px must be > 0, got {metadata.image_height_px}."
        )
    if metadata.range_m <= 0:
        raise ValueError(
            f"range_m must be > 0 (metres), got {metadata.range_m}. "
            "Provide the sonar swath half-range in metres."
        )


def _validate_norm_coords(
    cx_norm: float,
    cy_norm: float,
    bbox_w_norm: float,
) -> None:
    """Validate normalized bounding box coordinates are in [0, 1]."""
    for name, value in [("cx_norm", cx_norm), ("cy_norm", cy_norm)]:
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"{name} must be in [0.0, 1.0], got {value}."
            )
    if not (0.0 < bbox_w_norm <= 1.0):
        raise ValueError(
            f"bbox_w_norm must be in (0.0, 1.0], got {bbox_w_norm}."
        )
