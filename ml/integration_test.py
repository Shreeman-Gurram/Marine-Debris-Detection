"""
ml/integration_test.py
=======================
SONARIS — End-to-End Integration Test

Pipeline:
  1. Load DRISHTI model (models/best_detector.pt)
  2. Load test image (test_data/sample_sonar.jpg)
  3. Run P3 preprocessing (preprocess_image_full — light settings)
  4. Run YOLO detection on the original BGR image
  5. Format raw detections into standard dicts
  6. Apply P1 DetectionFilter
  7. Apply P1 RiskScorer
  8. Print structured result
  9. Save annotated image to outputs/integration_test/

Usage:
    python ml/integration_test.py

Notes on DRISHTI preprocessing:
    The released DRISHTI tiles (test_data/sample_sonar.jpg) are
    already Lee-filtered + CLAHE-preprocessed by the dataset authors.
    We apply preprocess_image_full() here with light settings as a
    pipeline demonstration, not for production-grade double-processing.
    YOLO inference uses the original BGR image (not the float32 output),
    since Ultralytics handles its own internal normalization.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve project root so this script works from any working directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
from ultralytics import YOLO

from ml.preprocessing import preprocess_image_full
from ml.filtering import DetectionFilter
from ml.scoring import RiskScorer


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_PATH = PROJECT_ROOT / "models" / "best_detector.pt"
IMAGE_PATH = PROJECT_ROOT / "test_data" / "sample_sonar.jpg"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "integration_test"
CONF_THRESHOLD = 0.10      # Low threshold as per DRISHTI docs
MIN_BOX_AREA_PX = 64.0     # Reject sub-8×8 pixel boxes


# ---------------------------------------------------------------------------
# ANSI color helpers (gracefully degrade on non-ANSI terminals)
# ---------------------------------------------------------------------------
def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"

BOLD  = lambda t: _c(t, "1")
GREEN = lambda t: _c(t, "92")
RED   = lambda t: _c(t, "91")
CYAN  = lambda t: _c(t, "96")
YELLOW= lambda t: _c(t, "93")
MAG   = lambda t: _c(t, "95")

RISK_COLOR = {
    "CRITICAL": lambda t: _c(t, "91;1"),
    "HIGH":     lambda t: _c(t, "93;1"),
    "MEDIUM":   lambda t: _c(t, "96"),
    "LOW":      lambda t: _c(t, "92"),
    "N/A":      lambda t: _c(t, "90"),
}


def section(title: str) -> None:
    print(f"\n{BOLD('='*60)}")
    print(BOLD(f"  {title}"))
    print(BOLD('='*60))


def main() -> None:
    section("SONARIS Integration Test")

    # -----------------------------------------------------------------------
    # Step 1: Validate paths
    # -----------------------------------------------------------------------
    print(f"\n{'Model path:':<22} {MODEL_PATH}")
    print(f"{'Image path:':<22} {IMAGE_PATH}")

    if not MODEL_PATH.exists():
        print(RED(f"ERROR: Model not found: {MODEL_PATH}"))
        sys.exit(1)
    if not IMAGE_PATH.exists():
        print(RED(f"ERROR: Test image not found: {IMAGE_PATH}"))
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{'Output dir:':<22} {OUTPUT_DIR}")

    # -----------------------------------------------------------------------
    # Step 2: Load model
    # -----------------------------------------------------------------------
    section("Step 1 — Load DRISHTI Model")
    model = YOLO(str(MODEL_PATH))
    print(GREEN("Model loaded successfully"))
    print(f"  Task:    {model.task}")
    print(f"  Classes: {model.names}")

    # -----------------------------------------------------------------------
    # Step 3: P3 Preprocessing (demonstration, light settings)
    # -----------------------------------------------------------------------
    section("Step 2 — P3 Preprocessing (preprocess_image_full)")
    print("Note: DRISHTI tiles are already Lee+CLAHE processed by dataset authors.")
    print("      Applying light-strength preprocess_image_full() as pipeline demo.")

    preprocessed_output = OUTPUT_DIR / f"preprocessed_{IMAGE_PATH.name.replace('.jpg', '.png')}"

    processed_f32 = preprocess_image_full(
        image=str(IMAGE_PATH),
        output_path=str(preprocessed_output),
        denoise_h=3.0,            # Light: already denoised by dataset
        clahe_clip_limit=1.5,     # Light: already CLAHE'd by dataset
        clahe_tile_grid=(8, 8),
        enhance_amount=0.5,       # Mild sharpening
        enhance_sigma=1.0,
    )

    h_proc, w_proc = processed_f32.shape
    print(GREEN("P3 preprocessing complete"))
    print(f"  Output shape:  {processed_f32.shape}  dtype={processed_f32.dtype}")
    print(f"  Value range:   [{processed_f32.min():.4f}, {processed_f32.max():.4f}]")
    print(f"  Saved to:      {preprocessed_output}")

    # -----------------------------------------------------------------------
    # Step 4: YOLO detection (on original BGR image)
    # -----------------------------------------------------------------------
    section("Step 3 — YOLO Detection")
    print(f"Running inference at conf={CONF_THRESHOLD} ...")

    # Load original BGR for YOLO (Ultralytics handles its own normalization)
    bgr_image = cv2.imread(str(IMAGE_PATH))
    img_h, img_w = bgr_image.shape[:2]
    print(f"  Image dimensions: {img_w}×{img_h} px")

    yolo_results = model.predict(
        source=str(IMAGE_PATH),
        conf=CONF_THRESHOLD,
        verbose=False,
    )
    result = yolo_results[0]
    num_raw = len(result.boxes)
    print(f"  Raw detections: {num_raw}")

    # -----------------------------------------------------------------------
    # Step 5: Format detections into standard dicts
    # -----------------------------------------------------------------------
    section("Step 4 — Format Detections")
    raw_detections = []
    for box in result.boxes:
        raw_detections.append({
            "class_id":   int(box.cls[0].item()),
            "class_name": model.names[int(box.cls[0].item())],
            "confidence": float(box.conf[0].item()),
            "bbox_xyxy":  [round(c, 2) for c in box.xyxy[0].tolist()],
            "image_w":    img_w,
            "image_h":    img_h,
        })

    for i, d in enumerate(raw_detections, 1):
        print(f"  [{i}] {d['class_name']}  conf={d['confidence']:.4f}  "
              f"bbox={d['bbox_xyxy']}")

    # -----------------------------------------------------------------------
    # Step 6: P1 Filtering
    # -----------------------------------------------------------------------
    section("Step 5 — P1 Detection Filtering")
    filt = DetectionFilter(
        min_confidence=CONF_THRESHOLD,
        allowed_classes=None,       # Accept all 5 DRISHTI classes
        min_box_area_px=MIN_BOX_AREA_PX,
    )
    filter_results = filt.filter(raw_detections)

    passed = sum(1 for r in filter_results if r.filter_status == "PASS")
    failed = len(filter_results) - passed
    print(f"  Filter config:  min_conf={CONF_THRESHOLD}  "
          f"min_box_area={MIN_BOX_AREA_PX} px²  allowed_classes=ALL")
    print(f"  Passed: {passed}  |  Failed: {failed}")
    for r in filter_results:
        status_str = GREEN("PASS") if r.filter_status == "PASS" else RED("FAIL")
        reason = f"  ({r.filter_reason})" if r.filter_reason else ""
        print(f"    {r.class_name:<22} conf={r.confidence:.4f}  "
              f"→ {status_str}{reason}")

    # -----------------------------------------------------------------------
    # Step 7: P1 Risk Scoring
    # -----------------------------------------------------------------------
    section("Step 6 — P1 Risk Scoring")
    scorer = RiskScorer()
    scored = scorer.score(filter_results)

    print(f"  {'Class':<22} {'Conf':>6}  {'Severity':>8}  "
          f"{'RiskScore':>9}  {'Level'}")
    print(f"  {'-'*22} {'-'*6}  {'-'*8}  {'-'*9}  {'-'*8}")
    for s in scored:
        level_str = RISK_COLOR.get(s.risk_level, lambda t: t)(s.risk_level)
        print(f"  {s.class_name:<22} {s.confidence:>6.4f}  "
              f"{s.class_severity:>8.2f}  {s.risk_score:>9.4f}  {level_str}")

    # -----------------------------------------------------------------------
    # Step 8: Final structured summary
    # -----------------------------------------------------------------------
    section("FINAL RESULTS")
    print(f"\n  Input image  : {IMAGE_PATH}")
    print(f"  Model        : {MODEL_PATH}")
    print(f"  Total raw detections : {num_raw}")
    print(f"  Passed filter        : {passed}")
    print(f"  Failed filter        : {failed}")
    print()

    for i, s in enumerate(scored, 1):
        if s.filter_status != "PASS":
            continue
        level_str = RISK_COLOR.get(s.risk_level, lambda t: t)(s.risk_level)
        print(f"  [{i}] {CYAN(s.class_name)}")
        print(f"       Class ID       : {s.class_id}")
        print(f"       Confidence     : {s.confidence:.4f}")
        print(f"       Bounding Box   : {s.bbox_xyxy}")
        print(f"       Filter Status  : {GREEN(s.filter_status)}")
        print(f"       Class Severity : {s.class_severity:.2f}")
        print(f"       Risk Score     : {s.risk_score:.4f}")
        print(f"       Risk Level     : {level_str}")
        print()

    # -----------------------------------------------------------------------
    # Step 9: Save annotated output image
    # -----------------------------------------------------------------------
    section("Step 7 — Save Annotated Output")
    annotated_output = OUTPUT_DIR / f"annotated_{IMAGE_PATH.name}"
    result.save(filename=str(annotated_output))
    print(GREEN(f"Annotated image saved: {annotated_output}"))
    print(GREEN("\nIntegration test COMPLETE.\n"))


if __name__ == "__main__":
    main()
