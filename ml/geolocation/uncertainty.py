"""
geolocation/uncertainty.py
==========================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 3: Geolocation Foundation

Positional uncertainty estimation for geolocated sonar detections.

Uncertainty Model
-----------------
The estimated position error combines four independent, orthogonal error
sources added in quadrature (root sum of squares, 1-sigma):

1. GPS Horizontal Accuracy (e_gps):
   From sensor hardware (metadata.gps_accuracy_m). If unspecified, defaults
   to standard marine DGPS error of 5.0 metres.

2. Range Resolution (e_range):
   Physical cross-track resolution of the sonar image
   (metadata.effective_range_resolution(), metres/pixel).

3. Pixel Localization Uncertainty (e_pixel):
   Uncertainty of where the object's acoustic reflection center lies within
   its detected bounding box, taken as half the bounding box width in metres:
   (detection.bbox_w_norm * image_width_px / 2.0) * range_per_px.

4. Heading / Compass Error (e_heading):
   Small angular errors in sensor heading propagate with distance:
   e_heading = slant_range_m * tan(1.0┬░)
   (assumes typical 1.0┬░ gyro / fluxgate compass accuracy).

Total Position Uncertainty (1-sigma, metres):
    sigma_total = sqrt(e_gps┬▓ + e_range┬▓ + e_pixel┬▓ + e_heading┬▓)

Relative Sonar Coordinates (No GPS)
-----------------------------------
When GPS is not available (status = "relative"), absolute geographic
uncertainty cannot be calculated, so uncertainty_m is set to None.
"""

from __future__ import annotations

import math
from typing import Optional

from .models import Detection, SonarMetadata
from .sonar_geometry import pixel_localization_uncertainty_m

# Default marine GPS horizontal accuracy (metres, 1-sigma) when not provided
DEFAULT_GPS_ACCURACY_M = 5.0

# Assumed towfish/vessel compass heading uncertainty (degrees)
ASSUMED_HEADING_UNCERTAINTY_DEG = 1.0


def estimate_uncertainty(
    detection: Detection,
    metadata: SonarMetadata,
    slant_range_m: float,
) -> Optional[float]:
    """
    Compute total positional uncertainty (1-sigma radius in metres).

    Args:
        detection:     Detection instance containing bounding box dimensions.
        metadata:      SonarMetadata instance.
        slant_range_m: Distance from nadir to target (metres).

    Returns:
        1-sigma position uncertainty in metres, or None if GPS is not available.
    """
    if not metadata.has_gps():
        return None

    # 1. GPS error
    e_gps = (
        metadata.gps_accuracy_m
        if metadata.gps_accuracy_m is not None
        else DEFAULT_GPS_ACCURACY_M
    )

    # 2. Range resolution error
    e_range = metadata.effective_range_resolution()

    # 3. Pixel localization error
    e_pixel = pixel_localization_uncertainty_m(detection.bbox_w_norm, metadata)

    # 4. Heading error
    heading_rad = math.radians(ASSUMED_HEADING_UNCERTAINTY_DEG)
    e_heading = slant_range_m * math.tan(heading_rad)

    # Combine in quadrature (RSS)
    total_variance = (e_gps ** 2) + (e_range ** 2) + (e_pixel ** 2) + (e_heading ** 2)
    return math.sqrt(total_variance)
