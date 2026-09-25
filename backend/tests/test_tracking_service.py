"""
backend/tests/test_tracking_service.py
========================================
SONARIS Phase 1 — Unit Tests for tracking_service.py

Covers all nine required scenarios without any file I/O, model loading,
MongoDB connection, or network access.

Run with:
    python -m pytest backend/tests/test_tracking_service.py -v
  or from project root:
    python -m pytest backend/tests/ -v

Detection dict format mirrors AnalysisService output:
    {
        "class_id":      int,
        "class_name":    str,
        "confidence":    float,
        "bbox":          [x1, y1, x2, y2],   # absolute pixels
        "filter_status": "PASS",
        "filter_reason": None,
        "risk_score":    float,
        "risk_level":    str,
        "geolocation":   {},                  # not used by tracker
    }
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make the project root importable so we can reach the service module
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from backend.app.services.tracking_service import (
    SonarTracker,
    TrackSummary,
    _compute_iou,
    track_frames,
    TRACKING_IOU_THRESHOLD,
    TRACKING_MAX_AGE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _det(
    class_name: str = "shipwreck",
    class_id: int = 2,
    bbox: list | None = None,
    confidence: float = 0.80,
    risk_level: str = "HIGH",
    risk_score: float = 0.75,
    filter_status: str = "PASS",
) -> dict:
    """Build a minimal detection dict matching AnalysisService output format."""
    return {
        "class_id":      class_id,
        "class_name":    class_name,
        "confidence":    confidence,
        "bbox":          bbox or [100.0, 100.0, 200.0, 200.0],
        "filter_status": filter_status,
        "filter_reason": None,
        "risk_score":    risk_score,
        "risk_level":    risk_level,
        "geolocation":   {},
    }


def _shifted(bbox: list, dx: float = 10.0, dy: float = 10.0) -> list:
    """Shift a bbox by (dx, dy) to simulate small inter-frame movement."""
    x1, y1, x2, y2 = bbox
    return [x1 + dx, y1 + dy, x2 + dx, y2 + dy]


# ---------------------------------------------------------------------------
# IoU unit tests (standalone helper)
# ---------------------------------------------------------------------------

class TestComputeIoU:

    def test_perfect_overlap_returns_one(self):
        box = [0.0, 0.0, 100.0, 100.0]
        assert _compute_iou(box, box) == pytest.approx(1.0)

    def test_no_overlap_returns_zero(self):
        a = [0.0, 0.0, 50.0, 50.0]
        b = [60.0, 60.0, 110.0, 110.0]
        assert _compute_iou(a, b) == pytest.approx(0.0)

    def test_partial_overlap(self):
        # Two 100x100 boxes, one shifted right by 50 → 50x100 intersection
        a = [0.0, 0.0, 100.0, 100.0]
        b = [50.0, 0.0, 150.0, 100.0]
        # inter = 50*100=5000, union = 100*100 + 100*100 - 5000 = 15000
        expected = 5000.0 / 15000.0
        assert _compute_iou(a, b) == pytest.approx(expected, rel=1e-5)

    def test_degenerate_zero_area_box(self):
        a = [10.0, 10.0, 10.0, 10.0]  # zero area
        b = [10.0, 10.0, 20.0, 20.0]
        assert _compute_iou(a, b) == pytest.approx(0.0)

    def test_contained_box(self):
        outer = [0.0, 0.0, 100.0, 100.0]
        inner = [25.0, 25.0, 75.0, 75.0]
        # inter = 50*50=2500, union = 10000 + 2500 - 2500 = 10000
        expected = 2500.0 / 10000.0
        assert _compute_iou(outer, inner) == pytest.approx(expected, rel=1e-5)


# ---------------------------------------------------------------------------
# Scenario 1: One object across 3 frames → one track
# ---------------------------------------------------------------------------

class TestOneObjectThreeFrames:

    def test_produces_exactly_one_track(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        frames = [
            [_det(bbox=bbox)],
            [_det(bbox=bbox)],
            [_det(bbox=bbox)],
        ]
        tracks = track_frames(frames)
        assert len(tracks) == 1

    def test_track_spans_all_frames(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        frames = [
            [_det(bbox=bbox)],
            [_det(bbox=bbox)],
            [_det(bbox=bbox)],
        ]
        track = track_frames(frames)[0]
        assert track.frames_seen == 3
        assert track.first_frame == 0
        assert track.last_frame == 2

    def test_track_has_correct_class(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        frames = [[_det(bbox=bbox)] for _ in range(3)]
        track = track_frames(frames)[0]
        assert track.class_name == "shipwreck"
        assert track.class_id == 2


# ---------------------------------------------------------------------------
# Scenario 2: Same object with moderate bbox movement → one track
# ---------------------------------------------------------------------------

class TestModerateBboxMovement:

    def test_small_shift_stays_same_track(self):
        bbox0 = [100.0, 100.0, 200.0, 200.0]
        bbox1 = _shifted(bbox0, dx=8.0, dy=5.0)   # ~8.5px shift
        bbox2 = _shifted(bbox1, dx=8.0, dy=5.0)
        frames = [
            [_det(bbox=bbox0)],
            [_det(bbox=bbox1)],
            [_det(bbox=bbox2)],
        ]
        tracks = track_frames(frames)
        assert len(tracks) == 1
        assert tracks[0].frames_seen == 3

    def test_bbox_history_recorded_per_frame(self):
        bbox0 = [100.0, 100.0, 200.0, 200.0]
        bbox1 = _shifted(bbox0, dx=5.0, dy=5.0)
        frames = [
            [_det(bbox=bbox0)],
            [_det(bbox=bbox1)],
        ]
        track = track_frames(frames)[0]
        assert len(track.bbox_history) == 2
        assert track.bbox_history[0]["frame_index"] == 0
        assert track.bbox_history[1]["frame_index"] == 1


# ---------------------------------------------------------------------------
# Scenario 3: Different classes → separate tracks
# ---------------------------------------------------------------------------

class TestDifferentClassesSeparateTracks:

    def test_two_classes_give_two_tracks(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        frames = [
            [
                _det(class_name="shipwreck",          class_id=2, bbox=bbox),
                _det(class_name="mine_cylinder",       class_id=4, bbox=bbox),
            ]
        ]
        tracks = track_frames(frames)
        assert len(tracks) == 2
        names = {t.class_name for t in tracks}
        assert names == {"shipwreck", "mine_cylinder"}

    def test_similar_bbox_different_class_no_merge(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        frames = [
            [_det(class_name="shipwreck",    class_id=2, bbox=bbox)],
            [_det(class_name="mine_cylinder", class_id=4, bbox=bbox)],
        ]
        tracks = track_frames(frames)
        assert len(tracks) == 2
        for t in tracks:
            assert t.frames_seen == 1


# ---------------------------------------------------------------------------
# Scenario 4: Low IoU → new track (not merged with existing)
# ---------------------------------------------------------------------------

class TestLowIouCreatesNewTrack:

    def test_non_overlapping_bbox_creates_new_track(self):
        bbox_a = [0.0,   0.0,   100.0, 100.0]
        bbox_b = [500.0, 500.0, 600.0, 600.0]  # no overlap
        frames = [
            [_det(bbox=bbox_a)],
            [_det(bbox=bbox_b)],
        ]
        tracks = track_frames(frames)
        assert len(tracks) == 2
        for t in tracks:
            assert t.frames_seen == 1

    def test_iou_just_below_threshold_creates_new_track(self):
        # IoU of exactly 0.0 (no overlap) → always new track regardless
        bbox_a = [0.0,   0.0,   100.0, 100.0]
        bbox_b = [101.0, 0.0,   201.0, 100.0]
        frames = [
            [_det(bbox=bbox_a)],
            [_det(bbox=bbox_b)],
        ]
        tracker = SonarTracker(iou_threshold=0.35, max_age=2)
        tracker.update(0, frames[0])
        tracker.update(1, frames[1])
        tracks = tracker.get_tracks()
        assert len(tracks) == 2


# ---------------------------------------------------------------------------
# Scenario 5: Temporary missed detection → existing track survives
# ---------------------------------------------------------------------------

class TestMissedFrameTrackSurvives:

    def test_one_missed_frame_track_continues(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        frames = [
            [_det(bbox=bbox)],   # frame 0 — detected
            [],                  # frame 1 — missed (empty frame)
            [_det(bbox=bbox)],   # frame 2 — detected again
        ]
        tracks = track_frames(frames, max_age=2)
        assert len(tracks) == 1
        assert tracks[0].frames_seen == 2  # only frames where matched
        assert tracks[0].first_frame  == 0
        assert tracks[0].last_frame   == 2

    def test_max_age_one_survives_single_miss(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        frames = [
            [_det(bbox=bbox)],
            [],
            [_det(bbox=bbox)],
        ]
        tracks = track_frames(frames, max_age=1)
        assert len(tracks) == 1


# ---------------------------------------------------------------------------
# Scenario 6: Track expiration after max_age
# ---------------------------------------------------------------------------

class TestTrackExpiration:

    def test_track_expires_after_max_age_exceeded(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        # Frame 0: detected. Frame 1,2,3: missed.  max_age=1 → expires after 2 misses
        frames = [
            [_det(bbox=bbox)],
            [],
            [],
            [],
        ]
        tracks = track_frames(frames, max_age=1)
        assert len(tracks) == 1
        assert tracks[0].frames_seen == 1
        assert tracks[0].last_frame == 0

    def test_two_separate_appearances_become_two_tracks(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        # Detected, then long gap (exceeds max_age), then detected again.
        # Should be treated as two independent objects/tracks.
        frames = [
            [_det(bbox=bbox)],   # frame 0
            [],                  # frame 1 — age=1
            [],                  # frame 2 — age=2 (equals max_age, still alive)
            [],                  # frame 3 — age=3 (> max_age=2, expired)
            [_det(bbox=bbox)],   # frame 4 — new track created
        ]
        tracks = track_frames(frames, max_age=2)
        assert len(tracks) == 2
        assert tracks[0].frames_seen == 1
        assert tracks[1].frames_seen == 1


# ---------------------------------------------------------------------------
# Scenario 7: Two objects of same class → separate tracks
# ---------------------------------------------------------------------------

class TestTwoSameClassSeparateTracks:

    def test_two_non_overlapping_same_class_tracked_separately(self):
        bbox_left  = [10.0,  10.0,  110.0, 110.0]
        bbox_right = [500.0, 500.0, 600.0, 600.0]
        frames = [
            [
                _det(class_name="ghost_net", class_id=3, bbox=bbox_left),
                _det(class_name="ghost_net", class_id=3, bbox=bbox_right),
            ],
            [
                _det(class_name="ghost_net", class_id=3, bbox=bbox_left),
                _det(class_name="ghost_net", class_id=3, bbox=bbox_right),
            ],
        ]
        tracks = track_frames(frames)
        assert len(tracks) == 2
        for t in tracks:
            assert t.class_name == "ghost_net"
            assert t.frames_seen == 2

    def test_each_track_has_distinct_track_id(self):
        bbox_a = [0.0,   0.0,   50.0,  50.0]
        bbox_b = [400.0, 400.0, 450.0, 450.0]
        frames = [
            [
                _det(bbox=bbox_a),
                _det(bbox=bbox_b),
            ]
        ]
        tracks = track_frames(frames)
        assert len(tracks) == 2
        ids = [t.track_id for t in tracks]
        assert ids[0] != ids[1]


# ---------------------------------------------------------------------------
# Scenario 8: Empty frame
# ---------------------------------------------------------------------------

class TestEmptyFrame:

    def test_all_empty_frames_produce_no_tracks(self):
        tracks = track_frames([[], [], []])
        assert tracks == []

    def test_empty_frame_does_not_crash(self):
        tracker = SonarTracker()
        tracker.update(frame_index=0, detections=[])
        assert tracker.get_tracks() == []

    def test_none_detections_list_handled(self):
        # Callers might pass None for a frame with no result
        tracker = SonarTracker()
        tracker.update(frame_index=0, detections=None)
        assert tracker.get_tracks() == []

    def test_failed_filter_status_ignored(self):
        # FAIL detections must be silently skipped
        det = _det(filter_status="FAIL")
        tracks = track_frames([[det]])
        assert tracks == []


# ---------------------------------------------------------------------------
# Scenario 9: Multiple detections in one frame
# ---------------------------------------------------------------------------

class TestMultipleDetectionsOneFrame:

    def test_multiple_detections_create_multiple_tracks(self):
        frames = [[
            _det(class_name="shipwreck",        class_id=2, bbox=[100.0, 100.0, 200.0, 200.0]),
            _det(class_name="crab_pot",          class_id=0, bbox=[300.0, 300.0, 400.0, 400.0]),
            _det(class_name="submarine_pipeline", class_id=1, bbox=[50.0,  50.0,  150.0, 150.0]),
        ]]
        tracks = track_frames(frames)
        assert len(tracks) == 3
        names = {t.class_name for t in tracks}
        assert names == {"shipwreck", "crab_pot", "submarine_pipeline"}

    def test_same_detection_not_assigned_to_two_tracks(self):
        # Two tracks of same class from frame 0; frame 1 has ONE detection.
        # Only one track should be updated; one should age.
        bbox_a = [0.0,   0.0,   100.0, 100.0]
        bbox_b = [400.0, 400.0, 500.0, 500.0]
        bbox_c = [5.0,   5.0,   105.0, 105.0]  # overlaps bbox_a heavily

        frames = [
            [
                _det(class_name="ghost_net", class_id=3, bbox=bbox_a),
                _det(class_name="ghost_net", class_id=3, bbox=bbox_b),
            ],
            [
                _det(class_name="ghost_net", class_id=3, bbox=bbox_c),
            ],
        ]
        tracks = track_frames(frames)
        # One of the two tracks should have frames_seen=2, the other frames_seen=1
        assert len(tracks) == 2
        seen_counts = sorted(t.frames_seen for t in tracks)
        assert seen_counts == [1, 2]


# ---------------------------------------------------------------------------
# TrackSummary content tests
# ---------------------------------------------------------------------------

class TestTrackSummaryContent:

    def test_confidence_history_matches_input(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        frames = [
            [_det(bbox=bbox, confidence=0.80)],
            [_det(bbox=bbox, confidence=0.90)],
        ]
        track = track_frames(frames)[0]
        assert track.confidence_history == pytest.approx([0.80, 0.90])
        assert track.max_confidence    == pytest.approx(0.90)
        assert track.avg_confidence    == pytest.approx(0.85)

    def test_risk_history_max_level_correct(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        frames = [
            [_det(bbox=bbox, risk_level="LOW",    risk_score=0.2)],
            [_det(bbox=bbox, risk_level="CRITICAL", risk_score=0.9)],
            [_det(bbox=bbox, risk_level="MEDIUM", risk_score=0.5)],
        ]
        track = track_frames(frames)[0]
        assert track.max_risk_level == "CRITICAL"
        assert track.risk_history == ["LOW", "CRITICAL", "MEDIUM"]

    def test_configurable_iou_threshold(self):
        # With a very high threshold (0.95) a slightly shifted box should NOT match
        bbox_a = [0.0, 0.0, 100.0, 100.0]
        bbox_b = [20.0, 20.0, 120.0, 120.0]   # IoU ≈ 0.60 < 0.95
        frames = [
            [_det(bbox=bbox_a)],
            [_det(bbox=bbox_b)],
        ]
        tracks = track_frames(frames, iou_threshold=0.95)
        assert len(tracks) == 2

    def test_configurable_iou_threshold_low_allows_match(self):
        # With a low threshold (0.10) a moderately shifted box SHOULD match
        bbox_a = [0.0,  0.0,  100.0, 100.0]
        bbox_b = [20.0, 20.0, 120.0, 120.0]   # IoU ≈ 0.60 > 0.10
        frames = [
            [_det(bbox=bbox_a)],
            [_det(bbox=bbox_b)],
        ]
        tracks = track_frames(frames, iou_threshold=0.10)
        assert len(tracks) == 1
        assert tracks[0].frames_seen == 2

    def test_invalid_iou_threshold_raises(self):
        with pytest.raises(ValueError):
            SonarTracker(iou_threshold=0.0)

    def test_invalid_max_age_raises(self):
        with pytest.raises(ValueError):
            SonarTracker(max_age=-1)

    def test_default_constants_are_correct(self):
        assert TRACKING_IOU_THRESHOLD == 0.35
        assert TRACKING_MAX_AGE       == 2
