"""
ml/filtering/detection_filter.py
==================================
SONARIS — P1 Detection Filtering Module
Prototype implementation (no equivalent existed in any develop/feature branch).

Filters raw YOLO detections from best_detector.pt based on:
  - Confidence threshold (below threshold → FAIL)
  - Allowed class whitelist (not in list → FAIL)
  - Minimum bounding box area in pixels (tiny slivers → FAIL)

Detection Format (input dict)
------------------------------
Each detection is a dictionary with these keys:
    class_id    : int   — YOLO class index (0–4 for DRISHTI)
    class_name  : str   — Human-readable class name
    confidence  : float — Raw model confidence in [0.0, 1.0]
    bbox_xyxy   : list  — Absolute pixel coords [x1, y1, x2, y2]
    image_w     : int   — Original image width in pixels
    image_h     : int   — Original image height in pixels

Output (FilterResult)
----------------------
A FilterResult dataclass augmenting the detection dict with:
    filter_status  : "PASS" | "FAIL"
    filter_reason  : Human-readable decision reason (empty string for PASS)

Usage
-----
    from ml.filtering import DetectionFilter

    filt = DetectionFilter(min_confidence=0.10)
    results = filt.filter(detections)
    passed = [r for r in results if r.filter_status == "PASS"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class FilterResult:
    """
    A single detection augmented with filtering metadata.

    Attributes:
        class_id:      YOLO class index.
        class_name:    Human-readable class name.
        confidence:    Model confidence score in [0.0, 1.0].
        bbox_xyxy:     Bounding box [x1, y1, x2, y2] in absolute pixels.
        image_w:       Source image width (pixels).
        image_h:       Source image height (pixels).
        filter_status: "PASS" if detection passed all filters, else "FAIL".
        filter_reason: Empty string for PASS; description of why FAIL.
    """
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: List[float]
    image_w: int
    image_h: int
    filter_status: str = "PASS"
    filter_reason: str = ""

    @property
    def box_area_px(self) -> float:
        """Bounding box area in pixels."""
        x1, y1, x2, y2 = self.bbox_xyxy
        return max(0.0, (x2 - x1) * (y2 - y1))

    def to_dict(self) -> Dict[str, Any]:
        """Return all fields as a plain dictionary."""
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox_xyxy": self.bbox_xyxy,
            "image_w": self.image_w,
            "image_h": self.image_h,
            "box_area_px": round(self.box_area_px, 2),
            "filter_status": self.filter_status,
            "filter_reason": self.filter_reason,
        }


class DetectionFilter:
    """
    Rule-based filter for SONARIS YOLO anomaly detections.

    Applies a configurable set of hard rules to accept or reject each
    detection from the DRISHTI YOLO model output. Detections that fail
    any rule are marked FAIL with an explanatory reason.

    Rules (applied in order; first failure stops further checks):
        1. Confidence threshold — confidence < min_confidence → FAIL
        2. Class whitelist      — class_id not in allowed_classes → FAIL
                                  (skipped if allowed_classes is None)
        3. Minimum box area     — box_area_px < min_box_area_px → FAIL

    Args:
        min_confidence:   Minimum acceptable confidence score. Default 0.10.
        allowed_classes:  Optional list of allowed class IDs. If None,
                          all DRISHTI classes (0–4) are accepted.
        min_box_area_px:  Minimum bounding box area in pixels. Detections
                          smaller than this are likely noise artefacts.
                          Default 64 (8×8 pixels).

    Example:
        >>> filt = DetectionFilter(min_confidence=0.25)
        >>> det = {
        ...     "class_id": 1, "class_name": "submarine_pipeline",
        ...     "confidence": 0.80, "bbox_xyxy": [100, 50, 400, 250],
        ...     "image_w": 640, "image_h": 500,
        ... }
        >>> results = filt.filter([det])
        >>> results[0].filter_status
        'PASS'
    """

    def __init__(
        self,
        min_confidence: float = 0.10,
        allowed_classes: Optional[List[int]] = None,
        min_box_area_px: float = 64.0,
    ) -> None:
        if not (0.0 <= min_confidence <= 1.0):
            raise ValueError(
                f"min_confidence must be in [0.0, 1.0], got {min_confidence}."
            )
        if min_box_area_px < 0:
            raise ValueError(
                f"min_box_area_px must be >= 0, got {min_box_area_px}."
            )

        self.min_confidence = min_confidence
        self.allowed_classes = allowed_classes
        self.min_box_area_px = min_box_area_px

    def filter(self, detections: List[Dict[str, Any]]) -> List[FilterResult]:
        """
        Apply all filter rules to a list of detections.

        Args:
            detections: List of detection dicts. Each dict must contain:
                        class_id, class_name, confidence, bbox_xyxy,
                        image_w, image_h.

        Returns:
            List of FilterResult objects, one per input detection.
            Order is preserved. Detections are never removed — they are
            marked PASS or FAIL.

        Raises:
            KeyError: If a detection dict is missing a required key.
        """
        results: List[FilterResult] = []
        for det in detections:
            result = FilterResult(
                class_id=det["class_id"],
                class_name=det["class_name"],
                confidence=det["confidence"],
                bbox_xyxy=det["bbox_xyxy"],
                image_w=det["image_w"],
                image_h=det["image_h"],
            )
            self._apply_rules(result)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Internal rule application
    # ------------------------------------------------------------------

    def _apply_rules(self, result: FilterResult) -> None:
        """Apply all filter rules in order. Mutates result in place."""
        # Rule 1: Confidence threshold
        if result.confidence < self.min_confidence:
            result.filter_status = "FAIL"
            result.filter_reason = (
                f"Confidence {result.confidence:.4f} < "
                f"threshold {self.min_confidence:.4f}"
            )
            return

        # Rule 2: Class whitelist
        if self.allowed_classes is not None:
            if result.class_id not in self.allowed_classes:
                result.filter_status = "FAIL"
                result.filter_reason = (
                    f"Class ID {result.class_id} ({result.class_name}) "
                    f"not in allowed_classes={self.allowed_classes}"
                )
                return

        # Rule 3: Minimum bounding box area
        if result.box_area_px < self.min_box_area_px:
            result.filter_status = "FAIL"
            result.filter_reason = (
                f"Box area {result.box_area_px:.1f} px² < "
                f"minimum {self.min_box_area_px:.1f} px²"
            )
            return

        # All rules passed
        result.filter_status = "PASS"
        result.filter_reason = ""
