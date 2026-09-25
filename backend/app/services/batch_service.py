"""
backend/app/services/batch_service.py
==========================================
SONARIS Phase 2 — Batch Analysis Service

Coordinates sequential processing of multiple sonar image frames using the
existing AnalysisService pipeline and integrates with the Phase 1 SonarTracker
to produce persistent anomaly tracks across frames.

Design principles:
- Does NOT duplicate any ML logic (preprocessing, YOLO, filtering, scoring,
  geolocation).  AnalysisService.analyze() is the single source of truth.
- Processes frames one at a time to bound memory use (no simultaneous BGR arrays).
- Maximum batch size is configurable via BATCH_MAX_FILES environment variable.
- Does NOT fabricate GPS coordinates; geolocation from each frame is preserved
  verbatim and re-attached to track history entries.
- Shared sonar metadata (heading, range, GPS) is passed unchanged to every
  AnalysisService call so each frame uses identical metadata semantics.
- BatchAnalysisService wraps a pre-existing AnalysisService instance and must
  never load a second YOLO model.

Batch result contract
---------------------
{
    "batch_id":               str,      # UUID4
    "type":                   "batch",
    "created_at":             str,      # UTC ISO-8601
    "total_frames":           int,
    "processed_frames":       int,      # frames where status == "ok"
    "total_raw_detections":   int,      # sum of PASS detections across all frames
    "total_persistent_tracks":int,
    "duplicates_merged":      int,      # raw_detections − persistent_tracks
    "frames":                 list[FrameResult],
    "tracks":                 list[TrackResult],
}

FrameResult keys:
    frame_index, original_filename, detections, evidence_filename,
    processing_status

TrackResult keys:
    track_id, class_id, class_name, frames_seen, first_frame, last_frame,
    max_confidence, avg_confidence, max_risk_score, avg_risk_score,
    highest_risk_level, bbox_history (with geolocation), confidence_history,
    risk_history, risk_score_history, frame_indices
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .analysis_service import AnalysisService
from .tracking_service import (
    SonarTracker,
    TRACKING_IOU_THRESHOLD,
    TRACKING_MAX_AGE,
)

logger = logging.getLogger("sonaris.batch")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Maximum number of images accepted per batch request.
#: Override via BATCH_MAX_FILES environment variable.
BATCH_MAX_FILES: int = int(os.environ.get("BATCH_MAX_FILES", "10"))


# ---------------------------------------------------------------------------
# Batch service
# ---------------------------------------------------------------------------

class BatchAnalysisService:
    """
    Orchestrates sequential frame processing and persistent anomaly tracking
    for a multi-image sonar batch.

    Parameters
    ----------
    analysis_service : AnalysisService
        Pre-initialised single-image service whose YOLO model is reused for
        every frame.  Must NOT be None.

    Usage::

        batch_svc = BatchAnalysisService(analysis_service=existing_service)
        result = batch_svc.analyze_batch(frames=[(path0, "frame0.jpg"), ...])
    """

    def __init__(self, analysis_service: AnalysisService) -> None:
        if analysis_service is None:
            raise ValueError("analysis_service must not be None.")
        self._analysis_service = analysis_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_batch(
        self,
        frames: List[Tuple[Path, str]],
        sonar_metadata_dict: Optional[Dict[str, Any]] = None,
        iou_threshold: float = TRACKING_IOU_THRESHOLD,
        max_age: int = TRACKING_MAX_AGE,
    ) -> Dict[str, Any]:
        """
        Process a batch of sequential sonar image frames.

        Parameters
        ----------
        frames : list of (Path, str)
            Ordered list of ``(image_path, original_filename)`` tuples.
            Processing order determines frame_index; the caller is responsible
            for ensuring chronological ordering.
        sonar_metadata_dict : dict, optional
            Shared navigation metadata applied to every frame (range_m,
            heading_deg, latitude, longitude, gps_accuracy_m).
            If None, each frame falls back to AnalysisService defaults.
            GPS coordinates are never invented — if not provided, geolocation
            status will be 'relative' (local_sonar coordinate system).
        iou_threshold : float
            IoU threshold forwarded to SonarTracker.
        max_age : int
            max_age forwarded to SonarTracker.

        Returns
        -------
        dict
            Full batch result matching the contract defined in this module's
            docstring.

        Raises
        ------
        ValueError
            If zero or more than BATCH_MAX_FILES frames are provided.
        """
        if not frames:
            raise ValueError("Batch requires at least one image.")
        if len(frames) > BATCH_MAX_FILES:
            raise ValueError(
                f"Batch exceeds maximum of {BATCH_MAX_FILES} images "
                f"(received {len(frames)})."
            )

        batch_id = str(uuid.uuid4())
        tracker  = SonarTracker(iou_threshold=iou_threshold, max_age=max_age)

        frame_results: List[Dict[str, Any]] = []
        # frame_det_map: frame_index → list of detection dicts (for geo re-join)
        frame_det_map: Dict[int, List[Dict[str, Any]]] = {}
        total_raw = 0

        # -------------------------------------------------------------------
        # Sequential frame processing
        # -------------------------------------------------------------------
        for frame_index, (image_path, original_filename) in enumerate(frames):
            try:
                result = self._analysis_service.analyze(
                    image_path=image_path,
                    original_filename=original_filename,
                    sonar_metadata_dict=sonar_metadata_dict,
                )
                detections: List[Dict[str, Any]] = result.get("detections", [])

                # Count only PASS detections as "raw" for the batch summary
                pass_count = sum(
                    1 for d in detections if d.get("filter_status") == "PASS"
                )
                total_raw += pass_count

                tracker.update(frame_index=frame_index, detections=detections)
                frame_det_map[frame_index] = detections

                frame_results.append({
                    "frame_index":       frame_index,
                    "original_filename": original_filename,
                    "detections":        detections,
                    "evidence_filename": result.get("evidence_image"),
                    "processing_status": "ok",
                })

                logger.info(
                    "Batch frame %d/%d processed. file=%s  PASS_detections=%d",
                    frame_index + 1, len(frames), original_filename, pass_count,
                )

            except Exception as exc:
                logger.error(
                    "Batch frame %d failed. file=%s  error=%s",
                    frame_index, original_filename, exc,
                )
                # Update tracker with empty detections so indices stay aligned
                tracker.update(frame_index=frame_index, detections=[])
                frame_det_map[frame_index] = []

                frame_results.append({
                    "frame_index":       frame_index,
                    "original_filename": original_filename,
                    "detections":        [],
                    "evidence_filename": None,
                    "processing_status": f"error: {exc}",
                })

        # -------------------------------------------------------------------
        # Assemble persistent track summaries
        # -------------------------------------------------------------------
        track_summaries = tracker.get_tracks()
        tracks_out: List[Dict[str, Any]] = []

        for ts in track_summaries:
            # Re-attach geolocation from frame results (not fabricated — it is
            # the exact geolocation dict produced by AnalysisService for each
            # matched detection in that frame).
            enriched_bbox_history = self._enrich_bbox_history(
                bbox_history=ts.bbox_history,
                frame_det_map=frame_det_map,
                class_name=ts.class_name,
            )

            frame_indices = [e["frame_index"] for e in ts.bbox_history]
            max_risk_score = (
                round(max(ts.risk_score_history), 4)
                if ts.risk_score_history
                else 0.0
            )

            tracks_out.append({
                "track_id":            ts.track_id,
                "class_id":            ts.class_id,
                "class_name":          ts.class_name,
                "frames_seen":         ts.frames_seen,
                "first_frame":         ts.first_frame,
                "last_frame":          ts.last_frame,
                "max_confidence":      ts.max_confidence,
                "avg_confidence":      ts.avg_confidence,
                "max_risk_score":      max_risk_score,
                "avg_risk_score":      ts.avg_risk_score,
                "highest_risk_level":  ts.max_risk_level,
                "bbox_history":        enriched_bbox_history,
                "confidence_history":  ts.confidence_history,
                "risk_history":        ts.risk_history,
                "risk_score_history":  ts.risk_score_history,
                "frame_indices":       frame_indices,
            })

        # -------------------------------------------------------------------
        # Build batch summary
        # -------------------------------------------------------------------
        processed_frames = sum(
            1 for f in frame_results if f["processing_status"] == "ok"
        )
        persistent_tracks = len(track_summaries)
        # Each persistent track accounts for 1 "real" anomaly; the rest of the
        # raw detections that matched it are counted as merged duplicates.
        duplicates_merged = max(0, total_raw - persistent_tracks)

        return {
            "batch_id":                batch_id,
            "type":                    "batch",
            "created_at":              datetime.now(timezone.utc).isoformat(),
            "total_frames":            len(frames),
            "processed_frames":        processed_frames,
            "total_raw_detections":    total_raw,
            "total_persistent_tracks": persistent_tracks,
            "duplicates_merged":       duplicates_merged,
            "frames":                  frame_results,
            "tracks":                  tracks_out,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _enrich_bbox_history(
        bbox_history: List[Dict[str, Any]],
        frame_det_map: Dict[int, List[Dict[str, Any]]],
        class_name: str,
    ) -> List[Dict[str, Any]]:
        """
        For every bbox_history entry, find the corresponding detection in the
        frame results and attach its geolocation dict verbatim.

        The geolocation is NOT modified, averaged, or fabricated.  If the
        matching detection cannot be found (e.g. frame errored), geolocation
        is set to None explicitly.

        Match strategy: same class_name + exact bbox list equality within the
        same frame.  If multiple detections share class_name and bbox (extremely
        unlikely), the first match is used.
        """
        enriched = []
        for entry in bbox_history:
            fi   = entry["frame_index"]
            bbox = entry["bbox"]
            geo  = None

            for det in frame_det_map.get(fi, []):
                if det.get("class_name") == class_name and det.get("bbox") == bbox:
                    geo = det.get("geolocation")
                    break

            enriched.append({**entry, "geolocation": geo})

        return enriched
