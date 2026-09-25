"""
backend/app/services/tracking_service.py
==========================================
SONARIS Phase 1 — Persistent Anomaly Tracking Engine

Consumes the detection output already produced by AnalysisService for each
sequential sonar frame and links detections across frames into persistent tracks.

Detection structure (produced by AnalysisService.analyze() → detections list):
    {
        "class_id":      int,
        "class_name":    str,
        "confidence":    float,          # rounded to 4 dp
        "bbox":          [x1, y1, x2, y2],  # absolute pixel coords for that frame
        "filter_status": "PASS" | "FAIL",
        "filter_reason": str | None,
        "risk_score":    float,
        "risk_level":    "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
        "geolocation":   dict,           # untouched — not used by tracker
    }

Tracking algorithm (IoU-based multi-class tracker):
    For each frame in chronological order:
      1. Only consider detections with filter_status == "PASS".
      2. For each active track, gather all detections of the SAME class_name.
      3. Compute IoU between the track's last known bbox and each candidate detection.
      4. Greedily assign the highest-IoU candidate to the track when IoU >= threshold.
         (One detection may only be assigned to one track per frame.)
      5. Unassigned detections become new tracks.
      6. Tracks that received no assignment in this frame have their age incremented.
      7. Tracks whose age exceeds TRACKING_MAX_AGE are closed (moved to finished).

Bounding-box coordinate notes:
    All bbox coordinates are stored in the per-frame pixel coordinate system of
    the image that produced them.  Different frames may have different image
    dimensions (e.g. if frames are cropped or have variable resolution).
    IoU is computed in the SAME coordinate space as the track's last known bbox,
    which is always the pixel space of the frame where that bbox was observed.
    Callers are responsible for ensuring that bboxes being compared belong to
    images of compatible resolution (or pre-normalise them before passing here).
    The tracker stores the raw per-frame bboxes — it does NOT normalise or project
    across different image sizes itself.

No geographic coordinates are fabricated or modified.
The existing geolocation dict is stored verbatim if passed through, but is not
required and is not used by any tracking logic.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("sonaris.tracking")

# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------

#: Minimum IoU required to associate a detection with an existing track.
#: Empirically appropriate for sonar data where objects shift slightly between
#: pings (see audit report §TRACKING ALGORITHM for justification).
TRACKING_IOU_THRESHOLD: float = 0.35

#: Number of consecutive frames a track may survive without a matched detection
#: before it is considered expired.  Value of 2 allows for single-frame YOLO
#: flicker without prematurely splitting a real persistent track.
TRACKING_MAX_AGE: int = 2


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass
class _TrackEntry:
    """
    Internal mutable state for one active or finished track.
    Not exposed directly to callers — use TrackSummary for external use.
    """
    track_id:        str
    class_id:        int
    class_name:      str
    first_frame:     int
    last_frame:      int
    frames_seen:     int          = 0
    age:             int          = 0   # frames since last matched detection
    last_bbox:       List[float]  = field(default_factory=list)

    # Histories — one entry per matched frame
    bbox_history:       List[Dict] = field(default_factory=list)
    confidence_history: List[float] = field(default_factory=list)
    risk_history:       List[str]   = field(default_factory=list)
    risk_score_history: List[float] = field(default_factory=list)


@dataclass
class TrackSummary:
    """
    Public, JSON-serialisable summary of one persistent anomaly track.
    Returned by SonarTracker.get_tracks() after processing all frames.
    """
    track_id:   str
    class_id:   int
    class_name: str
    first_frame: int
    last_frame:  int
    frames_seen: int

    #: Best (highest) confidence seen across all matched frames.
    max_confidence: float
    #: Highest risk level seen (ordered: CRITICAL > HIGH > MEDIUM > LOW).
    max_risk_level: str
    #: Average confidence across matched frames.
    avg_confidence: float
    #: Average risk score across matched frames.
    avg_risk_score: float

    #: Per-matched-frame details.
    bbox_history:       List[Dict]  # [{frame_index, bbox, confidence, risk_level, risk_score}]
    confidence_history: List[float]
    risk_history:       List[str]
    risk_score_history: List[float]


# ---------------------------------------------------------------------------
# IoU helper
# ---------------------------------------------------------------------------

def _compute_iou(
    box_a: List[float],
    box_b: List[float],
) -> float:
    """
    Compute Intersection over Union (IoU) for two axis-aligned bounding boxes.

    Both boxes are in [x1, y1, x2, y2] absolute-pixel format, matching the
    ``bbox`` field produced by AnalysisService.

    Returns:
        float in [0.0, 1.0].  Returns 0.0 for degenerate (zero-area) boxes.
    """
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    # Intersection rectangle
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    inter_w = max(0.0, ix2 - ix1)
    inter_h = max(0.0, iy2 - iy1)
    inter_area = inter_w * inter_h

    if inter_area == 0.0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union_area = area_a + area_b - inter_area

    if union_area <= 0.0:
        return 0.0

    return inter_area / union_area


# ---------------------------------------------------------------------------
# Risk-level ordering helper
# ---------------------------------------------------------------------------

_RISK_ORDER: Dict[str, int] = {
    "LOW":      0,
    "MEDIUM":   1,
    "HIGH":     2,
    "CRITICAL": 3,
}


def _max_risk(a: str, b: str) -> str:
    """Return the higher of two risk-level strings."""
    return a if _RISK_ORDER.get(a, 0) >= _RISK_ORDER.get(b, 0) else b


# ---------------------------------------------------------------------------
# Main tracker class
# ---------------------------------------------------------------------------

class SonarTracker:
    """
    Persistent anomaly tracker for sequential sonar frames.

    Usage::

        tracker = SonarTracker(iou_threshold=0.35, max_age=2)
        for frame_index, detections in enumerate(frame_detections_list):
            tracker.update(frame_index=frame_index, detections=detections)
        summaries = tracker.get_tracks()

    Parameters
    ----------
    iou_threshold : float
        Minimum IoU required to associate a detection with an existing active
        track.  Default: TRACKING_IOU_THRESHOLD (0.35).
    max_age : int
        Maximum number of consecutive missed frames before a track is expired.
        Default: TRACKING_MAX_AGE (2).
    """

    def __init__(
        self,
        iou_threshold: float = TRACKING_IOU_THRESHOLD,
        max_age: int = TRACKING_MAX_AGE,
    ) -> None:
        if not (0.0 < iou_threshold <= 1.0):
            raise ValueError(
                f"iou_threshold must be in (0, 1], got {iou_threshold}"
            )
        if max_age < 0:
            raise ValueError(f"max_age must be >= 0, got {max_age}")

        self._iou_threshold = iou_threshold
        self._max_age       = max_age
        self._active:   List[_TrackEntry] = []   # tracks still alive
        self._finished: List[_TrackEntry] = []   # tracks that expired
        self._frame_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        frame_index: int,
        detections: List[Dict[str, Any]],
    ) -> None:
        """
        Process one frame's worth of detections.

        Parameters
        ----------
        frame_index : int
            Zero-based chronological index of this frame within the batch.
            The caller is responsible for guaranteeing chronological order.
        detections : list of dict
            Detection dicts exactly as returned by AnalysisService.analyze()
            (``result["detections"]``).  Only detections with
            ``filter_status == "PASS"`` are considered; others are silently
            skipped.
        """
        self._frame_count += 1

        # Filter to only PASS detections — same semantics as evidence image
        passed = [
            d for d in (detections or [])
            if d.get("filter_status") == "PASS"
        ]

        # Set of detection indices already assigned to a track this frame
        assigned_det_indices: set = set()

        # ------------------------------------------------------------------
        # Step 1: Try to match each active track to a detection
        # ------------------------------------------------------------------
        for track in self._active:
            best_iou   = -1.0
            best_det_i = -1

            for det_i, det in enumerate(passed):
                if det_i in assigned_det_indices:
                    continue
                # Class must match
                if det["class_name"] != track.class_name:
                    continue
                iou = _compute_iou(track.last_bbox, det["bbox"])
                if iou >= self._iou_threshold and iou > best_iou:
                    best_iou   = iou
                    best_det_i = det_i

            if best_det_i >= 0:
                # Matched — update track
                det = passed[best_det_i]
                assigned_det_indices.add(best_det_i)
                self._update_track(track, frame_index=frame_index, det=det)
                logger.debug(
                    "Track %s matched  class=%s  IoU=%.3f  frame=%d",
                    track.track_id, track.class_name, best_iou, frame_index,
                )
            else:
                # Not matched — age the track
                track.age += 1
                logger.debug(
                    "Track %s unmatched  class=%s  age=%d  frame=%d",
                    track.track_id, track.class_name, track.age, frame_index,
                )

        # ------------------------------------------------------------------
        # Step 2: Expire tracks that exceeded max_age
        # ------------------------------------------------------------------
        still_active = []
        for track in self._active:
            if track.age > self._max_age:
                logger.debug(
                    "Track %s EXPIRED  class=%s  frames_seen=%d",
                    track.track_id, track.class_name, track.frames_seen,
                )
                self._finished.append(track)
            else:
                still_active.append(track)
        self._active = still_active

        # ------------------------------------------------------------------
        # Step 3: Create new tracks for unassigned detections
        # ------------------------------------------------------------------
        for det_i, det in enumerate(passed):
            if det_i in assigned_det_indices:
                continue
            new_track = self._create_track(frame_index=frame_index, det=det)
            self._active.append(new_track)
            logger.debug(
                "New track %s  class=%s  frame=%d",
                new_track.track_id, new_track.class_name, frame_index,
            )

    def get_tracks(self) -> List[TrackSummary]:
        """
        Return summaries of ALL tracks (active + expired/finished) after all
        frames have been processed via ``update()``.

        Active tracks are those that received at least one detection and have
        not yet exceeded max_age by the time the last frame was processed.

        Returns
        -------
        list of TrackSummary
            One entry per identified persistent anomaly.  Sorted by
            (first_frame, class_name, track_id) for deterministic ordering.
        """
        all_tracks = self._finished + self._active
        summaries  = [self._summarise(t) for t in all_tracks]
        summaries.sort(key=lambda s: (s.first_frame, s.class_name, s.track_id))
        return summaries

    def reset(self) -> None:
        """Clear all tracking state (useful for testing / re-use of instance)."""
        self._active   = []
        self._finished = []
        self._frame_count = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_track(frame_index: int, det: Dict[str, Any]) -> _TrackEntry:
        """Initialise a brand-new track from a detection dict."""
        track_id = f"track_{uuid.uuid4().hex[:8]}"
        bbox     = list(det["bbox"])
        track    = _TrackEntry(
            track_id    = track_id,
            class_id    = det["class_id"],
            class_name  = det["class_name"],
            first_frame = frame_index,
            last_frame  = frame_index,
            frames_seen = 1,
            age         = 0,
            last_bbox   = bbox,
        )
        track.bbox_history.append({
            "frame_index": frame_index,
            "bbox":        bbox,
            "confidence":  det["confidence"],
            "risk_level":  det.get("risk_level", "N/A"),
            "risk_score":  det.get("risk_score", 0.0),
        })
        track.confidence_history.append(det["confidence"])
        track.risk_history.append(det.get("risk_level", "N/A"))
        track.risk_score_history.append(det.get("risk_score", 0.0))
        return track

    @staticmethod
    def _update_track(
        track: _TrackEntry,
        frame_index: int,
        det: Dict[str, Any],
    ) -> None:
        """Apply a matched detection to an existing track."""
        bbox = list(det["bbox"])
        track.last_bbox  = bbox
        track.last_frame = frame_index
        track.frames_seen += 1
        track.age = 0  # reset age on successful match
        track.bbox_history.append({
            "frame_index": frame_index,
            "bbox":        bbox,
            "confidence":  det["confidence"],
            "risk_level":  det.get("risk_level", "N/A"),
            "risk_score":  det.get("risk_score", 0.0),
        })
        track.confidence_history.append(det["confidence"])
        track.risk_history.append(det.get("risk_level", "N/A"))
        track.risk_score_history.append(det.get("risk_score", 0.0))

    @staticmethod
    def _summarise(track: _TrackEntry) -> TrackSummary:
        """Compute a read-only TrackSummary from a _TrackEntry."""
        confs  = track.confidence_history or [0.0]
        scores = track.risk_score_history or [0.0]
        risks  = track.risk_history or ["LOW"]

        max_risk = risks[0]
        for r in risks[1:]:
            max_risk = _max_risk(max_risk, r)

        return TrackSummary(
            track_id           = track.track_id,
            class_id           = track.class_id,
            class_name         = track.class_name,
            first_frame        = track.first_frame,
            last_frame         = track.last_frame,
            frames_seen        = track.frames_seen,
            max_confidence     = round(max(confs), 4),
            avg_confidence     = round(sum(confs) / len(confs), 4),
            max_risk_level     = max_risk,
            avg_risk_score     = round(sum(scores) / len(scores), 4),
            bbox_history       = list(track.bbox_history),
            confidence_history = list(track.confidence_history),
            risk_history       = list(track.risk_history),
            risk_score_history = list(track.risk_score_history),
        )


# ---------------------------------------------------------------------------
# Convenience function (stateless, for simple callers)
# ---------------------------------------------------------------------------

def track_frames(
    frames: List[List[Dict[str, Any]]],
    iou_threshold: float = TRACKING_IOU_THRESHOLD,
    max_age: int = TRACKING_MAX_AGE,
) -> List[TrackSummary]:
    """
    Stateless convenience wrapper around SonarTracker.

    Parameters
    ----------
    frames : list of list of dict
        Outer list is ordered frames; each inner list is the ``detections``
        list from one AnalysisService result.
    iou_threshold : float
        IoU threshold passed to SonarTracker.
    max_age : int
        max_age passed to SonarTracker.

    Returns
    -------
    list of TrackSummary
    """
    tracker = SonarTracker(iou_threshold=iou_threshold, max_age=max_age)
    for frame_index, detections in enumerate(frames):
        tracker.update(frame_index=frame_index, detections=detections)
    return tracker.get_tracks()
