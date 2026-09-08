"""
geolocation/locator.py
======================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 3: Geolocation Foundation

Main entry point for geolocating YOLO detections in SSS imagery.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from .coordinate_transform import local_to_wgs84
from .models import Detection, GeoLocation, SonarMetadata
from .sonar_geometry import pixel_to_sonar_coords
from .uncertainty import estimate_uncertainty


def geolocate_detection(
    detection: Detection,
    metadata: SonarMetadata,
) -> GeoLocation:
    """
    Geolocate a single P1 YOLO detection using sonar metadata.

    If metadata includes GPS coordinates (latitude, longitude, heading_deg),
    the detection is transformed into WGS84 geographic coordinates with
    estimated positional uncertainty.

    If GPS metadata is absent (as is typical for the DRISHTI-SSS benchmark dataset),
    the detection is positioned in the local sonar relative frame (cross-track
    distance from nadir, bearing ┬▒90┬░).

    Args:
        detection: A Detection instance from P1's model.
        metadata:  SonarMetadata containing sensor parameters.

    Returns:
        A GeoLocation result instance.
    """
    if not isinstance(detection, Detection):
        raise TypeError(f"Expected Detection instance, got {type(detection).__name__}.")
    if not isinstance(metadata, SonarMetadata):
        raise TypeError(f"Expected SonarMetadata instance, got {type(metadata).__name__}.")

    # 1. Compute local sonar geometry
    slant_range_m, bearing_deg, local_x_m, local_y_m, _ = pixel_to_sonar_coords(
        cx_norm=detection.bbox_cx_norm,
        cy_norm=detection.bbox_cy_norm,
        bbox_w_norm=detection.bbox_w_norm,
        metadata=metadata,
    )

    # 2. Check if geographic transformation is possible
    if metadata.has_gps():
        assert metadata.latitude is not None
        assert metadata.longitude is not None
        assert metadata.heading_deg is not None

        lat_target, lon_target = local_to_wgs84(
            latitude=metadata.latitude,
            longitude=metadata.longitude,
            heading_deg=metadata.heading_deg,
            slant_range_m=slant_range_m,
            bearing_deg=bearing_deg,
        )
        uncertainty_m = estimate_uncertainty(
            detection=detection,
            metadata=metadata,
            slant_range_m=slant_range_m,
        )
        coordinate_system = "WGS84"
        status = "estimated"
    else:
        lat_target = None
        lon_target = None
        uncertainty_m = None
        coordinate_system = "local_sonar"
        status = "relative"

    return GeoLocation(
        range_m=slant_range_m,
        bearing_deg=bearing_deg,
        local_x_m=local_x_m,
        local_y_m=local_y_m,
        coordinate_system=coordinate_system,
        status=status,
        uncertainty_m=uncertainty_m,
        latitude=lat_target,
        longitude=lon_target,
        detection=detection,
        metadata=metadata,
    )


def geolocate_detections(
    detections: Sequence[Detection] | Iterable[Detection],
    metadata: SonarMetadata,
) -> list[GeoLocation]:
    """
    Batch geolocate multiple detections from a single sonar image.

    Args:
        detections: Sequence of Detection objects.
        metadata:   SonarMetadata for the parent image.

    Returns:
        List of GeoLocation instances in the same order as detections.
    """
    return [geolocate_detection(d, metadata) for d in detections]
