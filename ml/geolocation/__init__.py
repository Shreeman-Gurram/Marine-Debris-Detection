"""
geolocation
===========
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 3: Geolocation Foundation

This package provides:
  - Sonar image-to-physical coordinate transformations (cross-track distance, bearing)
  - Transformation to WGS84 latitude/longitude when GPS metadata is available
  - Positional uncertainty estimation
  - Flexible metadata loading and verification
  - Clean data interchange models for YOLO detections and geolocated results
"""

from .coordinate_transform import (
    METRES_PER_DEGREE_LAT,
    local_to_wgs84,
)
from .locator import (
    geolocate_detection,
    geolocate_detections,
)
from .metadata_loader import (
    create_default_metadata,
    load_metadata_from_dict,
    load_metadata_from_json,
)
from .models import (
    DRISHTI_CLASS_NAMES,
    Detection,
    GeoLocation,
    SonarMetadata,
)
from .sonar_geometry import (
    pixel_localization_uncertainty_m,
    pixel_to_sonar_coords,
)
from .uncertainty import (
    DEFAULT_GPS_ACCURACY_M,
    estimate_uncertainty,
)

__all__ = [
    # Data Models
    "SonarMetadata",
    "Detection",
    "GeoLocation",
    "DRISHTI_CLASS_NAMES",
    # Geometry & Transforms
    "pixel_to_sonar_coords",
    "pixel_localization_uncertainty_m",
    "local_to_wgs84",
    "METRES_PER_DEGREE_LAT",
    # Uncertainty
    "estimate_uncertainty",
    "DEFAULT_GPS_ACCURACY_M",
    # Locators
    "geolocate_detection",
    "geolocate_detections",
    # Metadata helpers
    "load_metadata_from_dict",
    "load_metadata_from_json",
    "create_default_metadata",
]
