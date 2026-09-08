"""
ml/scoring/risk_scorer.py
==========================
SONARIS — P1 Anomaly Risk Scoring Module
Prototype implementation (no equivalent existed in any develop/feature branch).

Assigns a risk score to each DRISHTI detection that passed the DetectionFilter.

Scoring Method
--------------
Risk scoring combines two factors:
  1. Class Severity: a fixed, domain-driven weight per anomaly class.
     Reflects the operational hazard level of each DRISHTI object class
     to naval/survey operations.
  2. Detection Confidence: the raw YOLO model confidence for this box.

Formula:
    risk_score = class_severity * confidence

This gives a value in [0.0, 1.0] where both low-confidence high-severity
and high-confidence low-severity detections score proportionally.

Class Severity Table (DRISHTI SONARIS classes)
----------------------------------------------
    mine_cylinder       → 1.00  [CRITICAL] UXO, immediate hazard
    shipwreck           → 0.80  [HIGH]     Navigation hazard, salvage
    ghost_net           → 0.60  [MEDIUM]   Entanglement, ecological
    submarine_pipeline  → 0.50  [MEDIUM]   Infrastructure, survey priority
    crab_pot            → 0.30  [LOW]      Minor obstruction

Risk Level Bands
----------------
    score ≥ 0.75  → CRITICAL
    score ≥ 0.50  → HIGH
    score ≥ 0.25  → MEDIUM
    score  < 0.25 → LOW

Input: FilterResult objects (from ml.filtering.DetectionFilter)
Output: ScoredDetection dataclasses with risk_score and risk_level added.

Usage
-----
    from ml.filtering import DetectionFilter
    from ml.scoring import RiskScorer

    scorer = RiskScorer()
    scored = scorer.score(filter_results)
    for s in scored:
        print(s.class_name, s.risk_score, s.risk_level)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any

from ml.filtering.detection_filter import FilterResult


# ---------------------------------------------------------------------------
# Class severity lookup table
# DRISHTI SONARIS model class IDs (0–4) → operational hazard weight
# ---------------------------------------------------------------------------
_CLASS_SEVERITY: Dict[str, float] = {
    "mine_cylinder":      1.00,
    "shipwreck":          0.80,
    "ghost_net":          0.60,
    "submarine_pipeline": 0.50,
    "crab_pot":           0.30,
}

# Risk level thresholds (score → label)
_RISK_THRESHOLDS = [
    (0.75, "CRITICAL"),
    (0.50, "HIGH"),
    (0.25, "MEDIUM"),
    (0.00, "LOW"),
]


@dataclass
class ScoredDetection:
    """
    A filtered detection augmented with anomaly risk scoring.

    Attributes:
        class_id:      YOLO class index.
        class_name:    Human-readable class name.
        confidence:    Model confidence in [0.0, 1.0].
        bbox_xyxy:     Bounding box [x1, y1, x2, y2] in absolute pixels.
        image_w:       Source image width.
        image_h:       Source image height.
        filter_status: "PASS" or "FAIL" from DetectionFilter.
        filter_reason: Reason string if FAIL.
        class_severity: Domain-based hazard weight for this class.
        risk_score:    Combined risk score in [0.0, 1.0].
        risk_level:    Categorical label: CRITICAL / HIGH / MEDIUM / LOW.
    """
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: List[float]
    image_w: int
    image_h: int
    filter_status: str
    filter_reason: str
    class_severity: float
    risk_score: float
    risk_level: str

    def to_dict(self) -> Dict[str, Any]:
        """Return all fields as a plain dictionary."""
        x1, y1, x2, y2 = self.bbox_xyxy
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox_xyxy": [round(c, 2) for c in self.bbox_xyxy],
            "image_w": self.image_w,
            "image_h": self.image_h,
            "filter_status": self.filter_status,
            "filter_reason": self.filter_reason,
            "class_severity": self.class_severity,
            "risk_score": round(self.risk_score, 4),
            "risk_level": self.risk_level,
        }


class RiskScorer:
    """
    Assign anomaly risk scores to SONARIS YOLO detections.

    Only scores detections that passed the DetectionFilter (filter_status
    == "PASS"). FAIL detections are included in the output with
    risk_score=0.0 and risk_level="N/A".

    Args:
        class_severity_override: Optional dict mapping class_name → float
            to override the default severity table for custom use cases.

    Example:
        >>> from ml.filtering import DetectionFilter
        >>> from ml.scoring import RiskScorer
        >>> scorer = RiskScorer()
        >>> # scorer.score(filter_results) returns List[ScoredDetection]
    """

    def __init__(
        self,
        class_severity_override: Dict[str, float] | None = None,
    ) -> None:
        self._severity = dict(_CLASS_SEVERITY)
        if class_severity_override:
            self._severity.update(class_severity_override)

    def score(self, filter_results: List[FilterResult]) -> List[ScoredDetection]:
        """
        Score a list of FilterResult objects.

        Args:
            filter_results: Output of DetectionFilter.filter().

        Returns:
            List of ScoredDetection objects. Order matches input.
            FAIL detections are included with risk_score=0.0, risk_level="N/A".
        """
        scored: List[ScoredDetection] = []
        for result in filter_results:
            if result.filter_status == "PASS":
                severity = self._severity.get(result.class_name, 0.50)
                raw_score = severity * result.confidence
                risk_score = max(0.0, min(1.0, raw_score))
                risk_level = self._classify_risk(risk_score)
            else:
                severity = self._severity.get(result.class_name, 0.50)
                risk_score = 0.0
                risk_level = "N/A"

            scored.append(ScoredDetection(
                class_id=result.class_id,
                class_name=result.class_name,
                confidence=result.confidence,
                bbox_xyxy=result.bbox_xyxy,
                image_w=result.image_w,
                image_h=result.image_h,
                filter_status=result.filter_status,
                filter_reason=result.filter_reason,
                class_severity=severity,
                risk_score=risk_score,
                risk_level=risk_level,
            ))
        return scored

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_risk(score: float) -> str:
        """Map a numeric risk score to a categorical risk level string."""
        for threshold, label in _RISK_THRESHOLDS:
            if score >= threshold:
                return label
        return "LOW"
