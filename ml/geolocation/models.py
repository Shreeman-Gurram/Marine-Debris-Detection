"""
geolocation/models.py
======================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 3: Geolocation Foundation

Data models for the P3 geolocation pipeline.

These dataclasses form the shared schema between:
  - P1 YOLO detection output (Detection)
  - P3 geolocation processing (SonarMetadata ΓåÆ GeoLocation)
  - P4 backend storage
  - P5 frontend display

Coordinate System Summary
--------------------------
Two coordinate systems are used, always explicitly labelled:

1. LOCAL SONAR (coordinate_system = "local_sonar")
   Origin: sonar nadir (directly below towfish)
   x_m:    cross-track distance (+ = starboard, ΓêÆ = port)
   y_m:    along-track distance (+ = ahead; 0 when timestamp unavailable)
   Always available when range_m is known.

2. WGS84 GEOGRAPHIC (coordinate_system = "WGS84")
   latitude, longitude in decimal degrees
   Only available when sensor GPS + heading are provided.

Status values
-------------
"relative"    ΓÇö only local sonar coords, no GPS available
"estimated"   ΓÇö WGS84 coords computed from GPS + heading
"no_metadata" ΓÇö insufficient input to compute any position
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Class name lookup (matches P2 DRISHTI-SSS class IDs)
# ---------------------------------------------------------------------------
DRISHTI_CLASS_NAMES: dict[int, str] = {
    0: "crab_pot",
    1: "submarine_pipeline",
    2: "shipwreck",
    3: "ghost_net",
    4: "mine_cylinder",
}


@dataclass
class SonarMetadata:
    """
    All metadata required by the P3 geolocation pipeline for one sonar image.

    Mandatory fields (always required):
        image_width_px   ΓÇö full image width in pixels
        image_height_px  ΓÇö full image height in pixels
        range_m          ΓÇö sonar swath half-range in metres
                           (distance from nadir to far edge of swath)
                           Must be supplied by the operator. NOT in dataset.

    Optional fields (from survey hardware ΓÇö not in DRISHTI-SSS dataset):
        latitude         ΓÇö sensor GPS latitude, WGS84 decimal degrees
        longitude        ΓÇö sensor GPS longitude, WGS84 decimal degrees
        heading_deg      ΓÇö vessel/towfish heading, degrees clockwise from North
        altitude_m       ΓÇö sensor altitude above seabed (metres)
        gps_accuracy_m   ΓÇö GPS horizontal accuracy (1-sigma, metres)
        range_resolution_m ΓÇö metres per pixel in the range direction
                             If None, derived from range_m / (image_width_px/2)

    Notes:
        - range_m is the HALF-swath range (nadir to far edge), not full width
        - heading_deg uses geographic convention: 0┬░=North, 90┬░=East, 180┬░=South
        - Without latitude+longitude+heading_deg, only local_sonar coords are available
    """
    image_width_px: int
    image_height_px: int
    range_m: float

    # Optional survey hardware fields
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    heading_deg: Optional[float] = None
    altitude_m: Optional[float] = None
    gps_accuracy_m: Optional[float] = None
    range_resolution_m: Optional[float] = None

    def has_gps(self) -> bool:
        """Return True if latitude, longitude, AND heading are all available."""
        return (
            self.latitude is not None
            and self.longitude is not None
            and self.heading_deg is not None
        )

    def effective_range_resolution(self) -> float:
        """
        Return metres-per-pixel in the cross-track direction.

        Uses range_resolution_m if provided, otherwise derives it from
        range_m and image_width_px.
        """
        if self.range_resolution_m is not None:
            return self.range_resolution_m
        # Swath covers nadir ΓåÆ far edge = range_m over half the image width
        return self.range_m / (self.image_width_px / 2.0)


@dataclass
class Detection:
    """
    A single object detection from P1's YOLO pipeline.

    Coordinates use YOLO normalized format (0.0ΓÇô1.0 relative to image size).

    This dataclass accepts P1 output directly. If P1 produces a different
    schema, use an adapter rather than modifying this class.

    Fields:
        image_id      ΓÇö image filename stem (e.g. "survey_001_tile_002_003")
        class_id      ΓÇö YOLO class index 0ΓÇô4 (see DRISHTI_CLASS_NAMES)
        class_name    ΓÇö human-readable class label
        confidence    ΓÇö detection confidence [0.0, 1.0]
        bbox_cx_norm  ΓÇö bounding box center x (normalized 0ΓÇô1)
        bbox_cy_norm  ΓÇö bounding box center y (normalized 0ΓÇô1)
        bbox_w_norm   ΓÇö bounding box width (normalized 0ΓÇô1)
        bbox_h_norm   ΓÇö bounding box height (normalized 0ΓÇô1)
    """
    image_id: str
    class_id: int
    class_name: str
    confidence: float
    bbox_cx_norm: float
    bbox_cy_norm: float
    bbox_w_norm: float
    bbox_h_norm: float

    @classmethod
    def from_yolo_row(
        cls,
        image_id: str,
        class_id: int,
        cx_norm: float,
        cy_norm: float,
        w_norm: float,
        h_norm: float,
        confidence: float = 1.0,
    ) -> "Detection":
        """
        Construct a Detection from raw YOLO values.

        Args:
            image_id:   Image filename stem.
            class_id:   Integer class index (0ΓÇô4).
            cx_norm:    Normalized center x [0, 1].
            cy_norm:    Normalized center y [0, 1].
            w_norm:     Normalized width [0, 1].
            h_norm:     Normalized height [0, 1].
            confidence: Detection confidence [0, 1]. Default 1.0 for GT labels.

        Raises:
            ValueError: If class_id is not in DRISHTI_CLASS_NAMES.
        """
        if class_id not in DRISHTI_CLASS_NAMES:
            raise ValueError(
                f"Unknown class_id {class_id}. "
                f"Expected one of {sorted(DRISHTI_CLASS_NAMES.keys())}."
            )
        return cls(
            image_id=image_id,
            class_id=class_id,
            class_name=DRISHTI_CLASS_NAMES[class_id],
            confidence=float(confidence),
            bbox_cx_norm=float(cx_norm),
            bbox_cy_norm=float(cy_norm),
            bbox_w_norm=float(w_norm),
            bbox_h_norm=float(h_norm),
        )


@dataclass
class GeoLocation:
    """
    The geolocation result for a single detection.

    Always contains local sonar coordinates (range_m, bearing_deg,
    local_x_m, local_y_m). Geographic coordinates are only populated
    when GPS + heading metadata was available.

    Fields:
        range_m           ΓÇö slant range from sonar nadir to object (metres)
        bearing_deg       ΓÇö bearing from nadir (+90=starboard, ΓêÆ90=port)
        local_x_m         ΓÇö cross-track distance from nadir (+= starboard)
        local_y_m         ΓÇö along-track distance (0.0 when unknown)
        coordinate_system ΓÇö "local_sonar" or "WGS84"
        status            ΓÇö "relative" | "estimated" | "no_metadata"
        uncertainty_m     ΓÇö 1-sigma position uncertainty (metres), None if unknown
        latitude          ΓÇö WGS84 latitude (None if GPS unavailable)
        longitude         ΓÇö WGS84 longitude (None if GPS unavailable)
        detection         ΓÇö the originating Detection object
        metadata          ΓÇö the SonarMetadata used for computation
    """
    range_m: float
    bearing_deg: float
    local_x_m: float
    local_y_m: float
    coordinate_system: str
    status: str
    uncertainty_m: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    detection: Detection
    metadata: SonarMetadata

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict representation."""
        return {
            "image_id": self.detection.image_id,
            "class_name": self.detection.class_name,
            "confidence": self.detection.confidence,
            "range_m": self.range_m,
            "bearing_deg": self.bearing_deg,
            "local_x_m": self.local_x_m,
            "local_y_m": self.local_y_m,
            "coordinate_system": self.coordinate_system,
            "status": self.status,
            "uncertainty_m": self.uncertainty_m,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
