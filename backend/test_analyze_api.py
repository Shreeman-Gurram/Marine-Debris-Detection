"""
backend/test_analyze_api.py
============================
SONARIS — Full API Test Script

Tests:
  1. GET  /api/health
  2. POST /api/analyze  (with test_data/sample_sonar.jpg)
  3. GET  /api/evidence/{filename}  (evidence image retrieval)

Handles both success (MongoDB configured) and 503 (MongoDB not configured)
responses from /api/analyze gracefully.

Usage:
    # Server must be running first:
    #   uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
    python backend/test_analyze_api.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL  = "http://127.0.0.1:8000"
IMG_PATH  = Path("test_data/sample_sonar.jpg")


def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def _get(path: str) -> dict:
    resp = urllib.request.urlopen(BASE_URL + path)
    return json.loads(resp.read().decode("utf-8"))


def _post_multipart(path: str, img_path: Path) -> tuple[int, dict | str]:
    """Returns (status_code, body_dict_or_str)."""
    boundary = "SONARISboundary9988"
    with open(img_path, "rb") as f:
        img_data = f.read()

    part_header = (
        "--" + boundary + "\r\n"
        'Content-Disposition: form-data; name="file"; filename="' + img_path.name + '"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8")
    part_footer = ("\r\n--" + boundary + "--\r\n").encode("utf-8")
    body = part_header + img_data + part_footer

    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method="POST",
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
    )
    try:
        resp = urllib.request.urlopen(req)
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_str = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body_str)
        except Exception:
            return e.code, body_str


def main() -> None:
    # -----------------------------------------------------------------------
    # 1. Health check
    # -----------------------------------------------------------------------
    _section("1. GET /api/health")
    health = _get("/api/health")
    print(json.dumps(health, indent=2))
    assert health.get("status") == "ok", f"FAIL: health check returned {health}"
    print("[OK] /api/health passed")

    # -----------------------------------------------------------------------
    # 2. POST /api/analyze
    # -----------------------------------------------------------------------
    _section("2. POST /api/analyze")
    print(f"  Image: {IMG_PATH}")
    status, result = _post_multipart("/api/analyze", IMG_PATH)
    print(f"  HTTP status: {status}")
    print(json.dumps(result, indent=2))

    if status == 503:
        # MongoDB not configured — expected without MONGODB_URI set
        print("\n[INFO] Got 503 — MongoDB not configured.")
        print("  This is expected if MONGODB_URI is not set in .env.")
        print("  Configure MONGODB_URI to enable persistence and analysis_id.")
        print("  All inference results above were computed by the SONARIS pipeline.")
        print("\n  To configure MongoDB:")
        print("    1. Edit .env: MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/")
        print("    2. Restart uvicorn")
        print("    3. Re-run this script")
        return

    assert status == 200, f"FAIL: expected 200, got {status}"

    # Validate real DRISHTI detection
    dets = result.get("detections", [])
    assert len(dets) > 0, "FAIL: no detections in response"
    d = dets[0]
    assert d["class_name"] == "submarine_pipeline", f"Unexpected class: {d['class_name']}"
    assert 0.75 < d["confidence"] < 0.90, f"Confidence out of expected range: {d['confidence']}"
    assert "analysis_id" in result, "FAIL: analysis_id missing from response"
    assert "evidence_image" in result, "FAIL: evidence_image missing from response"
    print(f"\n[OK] Detection verified: {d['class_name']}  conf={d['confidence']}")
    print(f"[OK] analysis_id:   {result['analysis_id']}")
    print(f"[OK] evidence_image: {result['evidence_image']}")

    # -----------------------------------------------------------------------
    # 3. Evidence image existence
    # -----------------------------------------------------------------------
    _section("3. Evidence image on disk")
    evidence_dir = Path(__file__).resolve().parent.parent / "outputs" / "evidence"
    evidence_path = evidence_dir / result["evidence_image"]
    exists = evidence_path.exists()
    print(f"  Evidence dir:  {evidence_dir}")
    print(f"  Evidence file: {evidence_path}")
    print(f"  Exists: {exists}")
    assert exists, f"FAIL: evidence image not found at {evidence_path}"
    size_kb = evidence_path.stat().st_size // 1024
    print(f"  File size: {size_kb} KB")
    print("[OK] Evidence image exists on disk")

    # -----------------------------------------------------------------------
    # 4. GET /api/evidence/{filename}
    # -----------------------------------------------------------------------
    _section("4. GET /api/evidence/{filename}")
    evidence_url = BASE_URL + "/api/evidence/" + result["evidence_image"]
    print(f"  URL: {evidence_url}")
    try:
        resp = urllib.request.urlopen(evidence_url)
        content_type = resp.headers.get("Content-Type", "")
        content_len  = len(resp.read())
        print(f"  HTTP status:   {resp.getcode()}")
        print(f"  Content-Type:  {content_type}")
        print(f"  Body size:     {content_len} bytes")
        assert resp.getcode() == 200, f"FAIL: expected 200, got {resp.getcode()}"
        assert "image" in content_type, f"FAIL: unexpected Content-Type: {content_type}"
        print("[OK] Evidence endpoint returned image data")
    except urllib.error.HTTPError as e:
        print(f"FAIL: /api/evidence returned HTTP {e.code}: {e.read().decode()}")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # 5. Path traversal safety test
    # -----------------------------------------------------------------------
    _section("5. Path traversal safety check")
    traversal_url = BASE_URL + "/api/evidence/../.env"
    try:
        urllib.request.urlopen(traversal_url)
        print("FAIL: traversal was NOT blocked!")
        sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"  Traversal attempt returned HTTP {e.code} (blocked as expected)")
        assert e.code in (400, 404), f"Unexpected status for traversal: {e.code}"
        print("[OK] Path traversal blocked correctly")

    _section("All API tests passed")
    print(f"  analysis_id:    {result['analysis_id']}")
    print(f"  evidence_image: {result['evidence_image']}")
    print(f"  detection:      {d['class_name']}  conf={d['confidence']}  risk={d['risk_level']}")
    print()


if __name__ == "__main__":
    main()
