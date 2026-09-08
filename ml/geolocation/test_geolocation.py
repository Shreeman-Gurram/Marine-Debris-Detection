"""
ml/geolocation/test_geolocation.py
====================================
SONARIS — P3 Geolocation Test Script

Tests geolocation of the verified DRISHTI detection:
  class      = submarine_pipeline
  bbox_xyxy  = [165.36, 0.0, 510.17, 249.48]
  image size = 640 x 500 px

CASE A: No GPS metadata  → status='relative', lat=None, lon=None
CASE B: Test GPS metadata → status='estimated', lat/lon computed

NOTE: Case B uses SAMPLE TEST METADATA only. The coordinates
(lat=17.0, lon=78.0, heading=90) are NOT real survey GPS values.
They exist solely to verify the WGS84 transform executes correctly.

Usage:
    python ml/geolocation/test_geolocation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve project root so the script works from any cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.geolocation import (
    Detection,
    SonarMetadata,
    create_default_metadata,
    geolocate_detection,
    load_metadata_from_dict,
)

# ---------------------------------------------------------------------------
# Detection from the verified integration test result
# ---------------------------------------------------------------------------
IMAGE_ID = "sample_sonar"
IMAGE_W  = 640
IMAGE_H  = 500

# YOLO xyxy → normalized cx, cy, w, h
X1, Y1, X2, Y2 = 165.36, 0.0, 510.17, 249.48
cx_norm  = ((X1 + X2) / 2.0) / IMAGE_W        # centre x normalized
cy_norm  = ((Y1 + Y2) / 2.0) / IMAGE_H        # centre y normalized
w_norm   = (X2 - X1) / IMAGE_W                # width normalized
h_norm   = (Y2 - Y1) / IMAGE_H                # height normalized

# Sonar swath half-range — DRISHTI typical SSS survey range
# (This is a reasonable value for shallow-water survey; not from metadata)
SURVEY_RANGE_M = 50.0  # metres, nadir to far edge


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def print_geo(geo, label: str) -> None:
    d = geo.to_dict()
    print(f"\n  {label}")
    print(f"  {'status':<22}: {d['status']}")
    print(f"  {'coordinate_system':<22}: {d['coordinate_system']}")
    print(f"  {'range_m':<22}: {d['range_m']:.4f} m")
    print(f"  {'bearing_deg':<22}: {d['bearing_deg']:.1f}°")
    print(f"  {'local_x_m':<22}: {d['local_x_m']:.4f} m")
    print(f"  {'local_y_m':<22}: {d['local_y_m']:.4f} m  (along-track: unknown)")
    print(f"  {'uncertainty_m':<22}: {d['uncertainty_m']}")
    print(f"  {'latitude':<22}: {d['latitude']}")
    print(f"  {'longitude':<22}: {d['longitude']}")


def main() -> None:
    section("SONARIS P3 Geolocation Test")
    print(f"\n  Detection: submarine_pipeline  conf=0.8052")
    print(f"  bbox_xyxy : [{X1}, {Y1}, {X2}, {Y2}]")
    print(f"  cx_norm   : {cx_norm:.6f}")
    print(f"  cy_norm   : {cy_norm:.6f}")
    print(f"  w_norm    : {w_norm:.6f}")
    print(f"  h_norm    : {h_norm:.6f}")
    print(f"  Image size: {IMAGE_W} x {IMAGE_H} px")

    det = Detection.from_yolo_row(
        image_id=IMAGE_ID,
        class_id=1,          # submarine_pipeline
        cx_norm=cx_norm,
        cy_norm=cy_norm,
        w_norm=w_norm,
        h_norm=h_norm,
        confidence=0.8052,
    )

    # -------------------------------------------------------------------
    # CASE A: No GPS metadata
    # -------------------------------------------------------------------
    section("CASE A — No GPS Metadata")
    print("  Expected: status='relative', latitude=None, longitude=None")

    meta_no_gps = create_default_metadata(
        image_width_px=IMAGE_W,
        image_height_px=IMAGE_H,
        range_m=SURVEY_RANGE_M,
    )
    geo_a = geolocate_detection(det, meta_no_gps)
    print_geo(geo_a, "Result:")

    assert geo_a.latitude is None, "FAIL: latitude should be None without GPS"
    assert geo_a.longitude is None, "FAIL: longitude should be None without GPS"
    assert geo_a.status == "relative", f"FAIL: status should be 'relative', got {geo_a.status!r}"
    assert geo_a.coordinate_system == "local_sonar"
    assert geo_a.uncertainty_m is None
    print("\n  [OK] CASE A PASSED -- no fabricated GPS coordinates")

    # -------------------------------------------------------------------
    # CASE B: Sample test GPS metadata
    # -------------------------------------------------------------------
    section("CASE B — Sample TEST Metadata (NOT real survey GPS)")
    print("  WARNING: lat=17.0, lon=78.0, heading=90 are SAMPLE TEST values only.")
    print("  They are used to verify the WGS84 transform executes correctly.")
    print("  Do NOT interpret these as real survey coordinates.\n")

    meta_with_gps = load_metadata_from_dict({
        "image_width_px":  IMAGE_W,
        "image_height_px": IMAGE_H,
        "range_m":         SURVEY_RANGE_M,
        "latitude":        17.000000,    # SAMPLE TEST ONLY
        "longitude":       78.000000,    # SAMPLE TEST ONLY
        "heading_deg":     90.0,         # SAMPLE TEST ONLY — vessel heading East
        "gps_accuracy_m":  5.0,          # Typical marine DGPS
    })
    geo_b = geolocate_detection(det, meta_with_gps)
    print_geo(geo_b, "Result:")

    assert geo_b.latitude is not None, "FAIL: latitude should be computed with GPS"
    assert geo_b.longitude is not None, "FAIL: longitude should be computed with GPS"
    assert geo_b.status == "estimated", f"FAIL: status should be 'estimated', got {geo_b.status!r}"
    assert geo_b.coordinate_system == "WGS84"
    assert geo_b.uncertainty_m is not None
    # Sanity: result should be near the test origin
    assert abs(geo_b.latitude - 17.0) < 1.0, f"FAIL: computed lat too far from origin"
    assert abs(geo_b.longitude - 78.0) < 1.0, f"FAIL: computed lon too far from origin"
    print(f"\n  [OK] CASE B PASSED -- WGS84 transform executed correctly")
    print(f"    Computed: lat={geo_b.latitude:.6f}  lon={geo_b.longitude:.6f}  "
          f"uncertainty={geo_b.uncertainty_m:.2f}m")

    section("Geolocation Test Complete")
    print("  Both cases passed. No fabricated GPS coordinates.\n")


if __name__ == "__main__":
    main()
