"""
backend/app/services/analysis_service.py
=========================================
SONARIS Backend — Analysis Service Layer

Runs the full SONARIS sonar anomaly detection pipeline for a single image:
  1. P3 Preprocessing  (ml.preprocessing)
  2. YOLO Detection    (Ultralytics YOLO + models/best_detector.pt)
  3. P1 Filtering      (ml.filtering)
  4. P1 Risk Scoring   (ml.scoring)
  5. P3 Geolocation    (ml.geolocation)
  6. Evidence Image    (annotated sonar image saved to outputs/evidence/)

Keeps all ML logic inside ml/ — this service only coordinates calls.
HTTP logic lives in main.py; database logic lives in database/mongodb.py.

Geolocation Notes:
    The SONARIS API does NOT fabricate GPS coordinates.
    If the caller supplies no sonar_metadata in the request body:
      - range_m defaults to DRISHTI_DEFAULT_RANGE_M (50.0 m)
      - latitude/longitude/heading_deg are None → status='relative'
    If the caller supplies GPS fields → status='estimated' (WGS84 coords returned)

Evidence Image Notes:
    - Saved to <project_root>/outputs/evidence/ with a UUID-based filename.
    - Annotated with YOLO bounding boxes, class names, and confidence scores.
    - Original uploaded image is NEVER overwritten.
    - Only filename (not full path) is returned in the API response for safe serving.
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Resolve project root — walk up until we find models/best_detector.pt
# ---------------------------------------------------------------------------
def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "models" / "best_detector.pt").exists():
            return parent
    return here.parent.parent.parent.parent  # prototype/backend/app/services/file.py

_PROJECT_ROOT = _find_project_root()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import cv2
import numpy as np
from ultralytics import YOLO

from ml.preprocessing import preprocess_image_full
from ml.filtering import DetectionFilter
from ml.scoring import RiskScorer
from ml.geolocation import (
    Detection as GeoDetection,
    SonarMetadata,
    create_default_metadata,
    geolocate_detection,
    load_metadata_from_dict,
)

logger = logging.getLogger("sonaris.analysis")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONF_THRESHOLD          = 0.10    # Low threshold per DRISHTI docs
MIN_BOX_AREA_PX         = 64.0   # Reject boxes smaller than 8×8 pixels
DRISHTI_DEFAULT_RANGE_M = 50.0   # SSS swath half-range fallback (metres)
EVIDENCE_DIR            = _PROJECT_ROOT / "outputs" / "evidence"

# Evidence image annotation colours (BGR)
_COLOUR_BY_LEVEL = {
    "CRITICAL": (0,   0,   220),   # Red
    "HIGH":     (0,   100, 255),   # Orange
    "MEDIUM":   (0,   200, 255),   # Yellow
    "LOW":      (0,   200,  50),   # Green
    "N/A":      (180, 180, 180),   # Grey
}
_DEFAULT_COLOUR = (200, 200, 200)


class AnalysisService:
    """
    Singleton-style service that loads the YOLO model once and reuses it.

    Usage:
        service = AnalysisService(model_path=Path("models/best_detector.pt"))
        result = service.analyze(image_path, sonar_metadata_dict)
    """

    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"YOLO model not found: {model_path}")
        self._model = YOLO(str(model_path))
        self._filter = DetectionFilter(
            min_confidence=CONF_THRESHOLD,
            allowed_classes=None,
            min_box_area_px=MIN_BOX_AREA_PX,
        )
        self._scorer = RiskScorer()
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    def analyze(
        self,
        image_path: Path,
        original_filename: str = "upload.jpg",
        sonar_metadata_dict: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the full SONARIS pipeline on a single sonar image.

        Args:
            image_path:          Path to the (temp) uploaded sonar image file.
            original_filename:   Original filename as submitted by the client.
            sonar_metadata_dict: Optional dict with SonarMetadata fields.

        Returns:
            Dict with keys: filename, detections, total_detections,
                            evidence_image, created_at.
        """
        # -------------------------------------------------------------------
        # Step 1: P3 Preprocessing (light settings — DRISHTI tiles are
        # already denoised; preprocessing is for pipeline consistency)
        # -------------------------------------------------------------------
        preprocess_image_full(
            image=str(image_path),
            output_path=None,       # No disk save during API call for speed
            denoise_h=3.0,
            clahe_clip_limit=1.5,
            clahe_tile_grid=(8, 8),
            enhance_amount=0.5,
            enhance_sigma=1.0,
        )

        # -------------------------------------------------------------------
        # Step 2: YOLO Detection on original BGR image
        # -------------------------------------------------------------------
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            raise ValueError(f"cv2 could not read uploaded image: {image_path}")
        # Ultralytics patches cv2.imread to return (H,W,1) for grayscale;
        # ensure we always have a 3-channel image for annotation drawing.
        if bgr.ndim == 3 and bgr.shape[2] == 1:
            bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
        elif bgr.ndim == 2:
            bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)

        img_h, img_w = bgr.shape[:2]

        yolo_results = self._model.predict(
            source=str(image_path),
            conf=CONF_THRESHOLD,
            verbose=False,
        )
        yolo_result = yolo_results[0]

        # -------------------------------------------------------------------
        # Step 3: Format raw detections into standard dicts
        # -------------------------------------------------------------------
        raw_detections = []
        for box in yolo_result.boxes:
            raw_detections.append({
                "class_id":   int(box.cls[0].item()),
                "class_name": self._model.names[int(box.cls[0].item())],
                "confidence": float(box.conf[0].item()),
                "bbox_xyxy":  [round(c, 4) for c in box.xyxy[0].tolist()],
                "image_w":    img_w,
                "image_h":    img_h,
            })

        # -------------------------------------------------------------------
        # Step 4: P1 Filtering
        # -------------------------------------------------------------------
        filter_results = self._filter.filter(raw_detections)

        # -------------------------------------------------------------------
        # Step 5: P1 Risk Scoring
        # -------------------------------------------------------------------
        scored = self._scorer.score(filter_results)

        # -------------------------------------------------------------------
        # Step 6: P3 Geolocation — NEVER fabricate GPS coordinates
        # -------------------------------------------------------------------
        metadata = self._build_metadata(
            img_w=img_w,
            img_h=img_h,
            user_meta=sonar_metadata_dict,
        )

        # -------------------------------------------------------------------
        # Step 7: Assemble detection results
        # -------------------------------------------------------------------
        detections_out: List[Dict[str, Any]] = []
        for s in scored:
            x1, y1, x2, y2 = s.bbox_xyxy
            cx_norm = ((x1 + x2) / 2.0) / img_w
            cy_norm = ((y1 + y2) / 2.0) / img_h
            w_norm  = (x2 - x1) / img_w
            h_norm  = (y2 - y1) / img_h

            geo_det = GeoDetection.from_yolo_row(
                image_id=image_path.stem,
                class_id=s.class_id,
                cx_norm=max(0.0, min(1.0, cx_norm)),
                cy_norm=max(0.0, min(1.0, cy_norm)),
                w_norm=max(1e-6, min(1.0, w_norm)),
                h_norm=max(1e-6, min(1.0, h_norm)),
                confidence=s.confidence,
            )
            geo = geolocate_detection(geo_det, metadata)

            detections_out.append({
                "class_id":      s.class_id,
                "class_name":    s.class_name,
                "confidence":    round(s.confidence, 4),
                "bbox":          [round(c, 2) for c in s.bbox_xyxy],
                "filter_status": s.filter_status,
                "filter_reason": s.filter_reason,
                "risk_score":    round(s.risk_score, 4),
                "risk_level":    s.risk_level,
                "geolocation":   geo.to_dict(),
            })

        # -------------------------------------------------------------------
        # Step 8: Evidence image — annotated copy saved to outputs/evidence/
        # -------------------------------------------------------------------
        evidence_filename = self._save_evidence_image(
            bgr=bgr,
            detections=detections_out,
            original_filename=original_filename,
        )

        return {
            "filename":         original_filename,
            "created_at":       datetime.now(timezone.utc).isoformat(),
            "detections":       detections_out,
            "total_detections": len(detections_out),
            "evidence_image":   evidence_filename,
        }

    # ------------------------------------------------------------------
    # Evidence image generation
    # ------------------------------------------------------------------

    def _save_evidence_image(
        self,
        bgr: np.ndarray,
        detections: List[Dict[str, Any]],
        original_filename: str,
    ) -> str:
        """
        Draw bounding boxes, class names, and confidence scores on the BGR
        image and save it to outputs/evidence/.

        Returns:
            The evidence image filename (basename only, not full path).
        """
        annotated = bgr.copy()

        for det in detections:
            if det.get("filter_status") != "PASS":
                continue

            x1, y1, x2, y2 = [int(round(c)) for c in det["bbox"]]
            label = f"{det['class_name']}  {det['confidence']:.2f}"
            risk  = det.get("risk_level", "N/A")
            colour = _COLOUR_BY_LEVEL.get(risk, _DEFAULT_COLOUR)

            # Bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), colour, 2)

            # Label background
            font       = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.55
            thickness  = 1
            (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            label_y = max(y1 - 4, th + 4)
            cv2.rectangle(
                annotated,
                (x1, label_y - th - baseline - 2),
                (x1 + tw + 4, label_y + 2),
                colour, cv2.FILLED,
            )

            # Label text (dark for readability)
            text_colour = (20, 20, 20)
            cv2.putText(
                annotated, label,
                (x1 + 2, label_y - baseline),
                font, font_scale, text_colour, thickness, cv2.LINE_AA,
            )

            # Risk badge bottom-right of box
            risk_label = f"Risk:{risk}"
            (rw, rh), _ = cv2.getTextSize(risk_label, font, 0.42, 1)
            rx = x2 - rw - 4
            ry = y2 + rh + 4
            if ry < annotated.shape[0]:
                cv2.putText(
                    annotated, risk_label,
                    (rx, ry), font, 0.42, colour, 1, cv2.LINE_AA,
                )

        # Watermark
        watermark = "SONARIS Evidence"
        cv2.putText(
            annotated, watermark,
            (6, annotated.shape[0] - 6),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4,
            (200, 200, 200), 1, cv2.LINE_AA,
        )

        # Unique filename: <stem>_<uuid8>.jpg
        stem = Path(original_filename).stem
        uid  = uuid.uuid4().hex[:8]
        evidence_filename = f"{stem}_evidence_{uid}.jpg"
        evidence_path = EVIDENCE_DIR / evidence_filename

        cv2.imwrite(str(evidence_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])
        logger.info("Evidence image saved: %s", evidence_path)
        return evidence_filename

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_metadata(
        img_w: int,
        img_h: int,
        user_meta: Optional[Dict[str, Any]],
    ) -> SonarMetadata:
        """
        Build SonarMetadata from image dimensions and optional user-provided dict.

        If user_meta is None or does not contain GPS fields, returns metadata
        with no lat/lon/heading → geolocation status = 'relative'.
        Does NOT fabricate any coordinates.
        """
        if user_meta is None:
            return create_default_metadata(
                image_width_px=img_w,
                image_height_px=img_h,
                range_m=DRISHTI_DEFAULT_RANGE_M,
            )

        merged = dict(user_meta)
        merged["image_width_px"] = img_w
        merged["image_height_px"] = img_h

        if "range_m" not in merged or merged["range_m"] is None:
            merged["range_m"] = DRISHTI_DEFAULT_RANGE_M

        return load_metadata_from_dict(merged)
