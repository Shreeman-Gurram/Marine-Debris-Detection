"""
geolocation/metadata_loader.py
==============================
P3 ΓÇö Sonar Processing + Geolocation | SONARIS Project
Phase 3: Geolocation Foundation

Load, construct, and validate SonarMetadata from dictionaries and JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .models import SonarMetadata


def load_metadata_from_dict(data: Mapping[str, Any]) -> SonarMetadata:
    """
    Parse and validate SonarMetadata from a dictionary or mapping.

    Required keys:
        - image_width_px: int (> 0)
        - image_height_px: int (> 0)
        - range_m: float (> 0)

    Optional keys:
        - latitude: float [-90.0, 90.0]
        - longitude: float [-180.0, 180.0]
        - heading_deg: float [0.0, 360.0)
        - altitude_m: float
        - gps_accuracy_m: float (>= 0)
        - range_resolution_m: float (> 0)

    Raises:
        KeyError: If a mandatory key is missing.
        ValueError: If any key contains invalid or out-of-range values.
        TypeError: If types cannot be converted.
    """
    if not isinstance(data, Mapping):
        raise TypeError(f"Expected a dict/mapping, got {type(data).__name__}.")

    for required_key in ("image_width_px", "image_height_px", "range_m"):
        if required_key not in data:
            raise KeyError(f"Missing mandatory metadata field: '{required_key}'.")

    try:
        width = int(data["image_width_px"])
        height = int(data["image_height_px"])
        range_m = float(data["range_m"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid numeric value for mandatory fields: {exc}") from exc

    if width <= 0:
        raise ValueError(f"image_width_px must be positive, got {width}.")
    if height <= 0:
        raise ValueError(f"image_height_px must be positive, got {height}.")
    if range_m <= 0:
        raise ValueError(f"range_m must be positive, got {range_m}.")

    lat = _parse_optional_float(data.get("latitude"))
    lon = _parse_optional_float(data.get("longitude"))
    heading = _parse_optional_float(data.get("heading_deg"))
    alt = _parse_optional_float(data.get("altitude_m"))
    gps_acc = _parse_optional_float(data.get("gps_accuracy_m"))
    res_m = _parse_optional_float(data.get("range_resolution_m"))

    if lat is not None and not (-90.0 <= lat <= 90.0):
        raise ValueError(f"latitude must be in [-90.0, 90.0], got {lat}.")
    if lon is not None and not (-180.0 <= lon <= 180.0):
        raise ValueError(f"longitude must be in [-180.0, 180.0], got {lon}.")
    if heading is not None and not (0.0 <= heading < 360.0):
        raise ValueError(f"heading_deg must be in [0.0, 360.0), got {heading}.")
    if gps_acc is not None and gps_acc < 0.0:
        raise ValueError(f"gps_accuracy_m must be >= 0.0, got {gps_acc}.")
    if res_m is not None and res_m <= 0.0:
        raise ValueError(f"range_resolution_m must be > 0.0, got {res_m}.")

    return SonarMetadata(
        image_width_px=width,
        image_height_px=height,
        range_m=range_m,
        latitude=lat,
        longitude=lon,
        heading_deg=heading,
        altitude_m=alt,
        gps_accuracy_m=gps_acc,
        range_resolution_m=res_m,
    )


def load_metadata_from_json(json_path: str | Path) -> SonarMetadata:
    """
    Load and parse SonarMetadata from a JSON file.

    Args:
        json_path: Path to the JSON file.

    Returns:
        Validated SonarMetadata instance.
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    return load_metadata_from_dict(payload)


def create_default_metadata(
    image_width_px: int,
    image_height_px: int,
    range_m: float,
) -> SonarMetadata:
    """
    Convenience factory to create relative-only SonarMetadata.

    Args:
        image_width_px:  Full image width in pixels.
        image_height_px: Full image height in pixels.
        range_m:         Sonar swath half-range in metres.

    Returns:
        SonarMetadata with no GPS (status will be 'relative').
    """
    return SonarMetadata(
        image_width_px=int(image_width_px),
        image_height_px=int(image_height_px),
        range_m=float(range_m),
    )


def _parse_optional_float(val: Any) -> float | None:
    """Helper to convert optional value to float or None."""
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Could not convert {val!r} to float: {exc}") from exc
