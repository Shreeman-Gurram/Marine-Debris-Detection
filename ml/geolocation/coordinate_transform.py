"""
geolocation/coordinate_transform.py
===================================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 3: Geolocation Foundation

Transform local sonar coordinates to WGS84 geographic coordinates
(latitude, longitude in decimal degrees).

Geodetic Reference
------------------
Uses the WGS84 ellipsoid approximation suitable for local acoustic positioning
(ranges < 1000m). At survey ranges typical of SSS (25m - 200m), the small-angle
flat-Earth projection introduces less than 1mm of error compared to full
ellipsoidal geodesics, while being computationally efficient.

Coordinate Conventions
----------------------
- latitude:   WGS84 decimal degrees [-90.0, 90.0]
- longitude:  WGS84 decimal degrees [-180.0, 180.0]
- heading_deg: Vessel/towfish heading clockwise from True North [0.0, 360.0)
               0┬░ = North, 90┬░ = East, 180┬░ = South, 270┬░ = West
- bearing_deg: Object bearing relative to vessel heading:
               +90.0┬░ = Starboard (right)
               -90.0┬░ = Port (left)
- slant_range_m: Distance from sonar nadir to target (metres, >= 0)

Equations
---------
1. True geographic bearing from sensor to object:
       true_bearing_deg = (heading_deg + bearing_deg) % 360.0
       true_bearing_rad = radians(true_bearing_deg)

2. North and East displacements (metres):
       d_north_m = slant_range_m * cos(true_bearing_rad)
       d_east_m  = slant_range_m * sin(true_bearing_rad)

3. Latitude and Longitude offsets (degrees):
       METRES_PER_DEGREE_LAT = 111320.0
       delta_lat = d_north_m / METRES_PER_DEGREE_LAT
       delta_lon = d_east_m / (METRES_PER_DEGREE_LAT * cos(radians(latitude)))

4. Target coordinates:
       lat_target = latitude + delta_lat
       lon_target = longitude + delta_lon
"""

from __future__ import annotations

import math

# Metres per degree latitude on standard WGS84 approximation
METRES_PER_DEGREE_LAT = 111320.0


def local_to_wgs84(
    latitude: float,
    longitude: float,
    heading_deg: float,
    slant_range_m: float,
    bearing_deg: float,
) -> tuple[float, float]:
    """
    Convert local sonar observation to WGS84 latitude and longitude.

    Args:
        latitude:      Sensor GPS latitude in decimal degrees [-90.0, 90.0].
        longitude:     Sensor GPS longitude in decimal degrees [-180.0, 180.0].
        heading_deg:   Sensor heading in degrees from True North [0.0, 360.0).
        slant_range_m: Distance from nadir to target in metres (>= 0).
        bearing_deg:   Offset bearing from heading (+90.0 = starboard, -90.0 = port).

    Returns:
        (target_latitude, target_longitude) in WGS84 decimal degrees.

    Raises:
        ValueError: If coordinates or parameters are outside physically valid ranges.
    """
    _validate_geodetic_inputs(latitude, longitude, heading_deg, slant_range_m)

    # Calculate true geographic bearing to object
    true_bearing_deg = (heading_deg + bearing_deg) % 360.0
    true_bearing_rad = math.radians(true_bearing_deg)

    # Displacements in metres
    d_north_m = slant_range_m * math.cos(true_bearing_rad)
    d_east_m = slant_range_m * math.sin(true_bearing_rad)

    # Convert to decimal degree offsets
    delta_lat = d_north_m / METRES_PER_DEGREE_LAT

    # Cosine scaling for longitude with safety against division by zero at poles
    lat_rad = math.radians(latitude)
    cos_lat = math.cos(lat_rad)
    if abs(cos_lat) < 1e-7:
        # Extremely close to pole
        delta_lon = 0.0
    else:
        delta_lon = d_east_m / (METRES_PER_DEGREE_LAT * cos_lat)

    target_lat = latitude + delta_lat
    target_lon = longitude + delta_lon

    # Clamp / normalize target coordinates
    target_lat = max(-90.0, min(90.0, target_lat))
    target_lon = ((target_lon + 180.0) % 360.0) - 180.0

    return target_lat, target_lon


def _validate_geodetic_inputs(
    latitude: float,
    longitude: float,
    heading_deg: float,
    slant_range_m: float,
) -> None:
    """Validate geodetic input values."""
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"latitude must be in [-90.0, 90.0], got {latitude}.")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"longitude must be in [-180.0, 180.0], got {longitude}.")
    if not (0.0 <= heading_deg < 360.0):
        raise ValueError(f"heading_deg must be in [0.0, 360.0), got {heading_deg}.")
    if slant_range_m < 0.0:
        raise ValueError(f"slant_range_m must be >= 0.0, got {slant_range_m}.")
