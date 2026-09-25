"""
backend/tests/test_batch_service.py
=====================================
SONARIS Phase 2 — Unit Tests for BatchAnalysisService

Uses MagicMock to replace AnalysisService so no real YOLO model, no real
images, and no MongoDB connection are needed.

Run with:
    python -m pytest backend/tests/test_batch_service.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from backend.app.services.batch_service import BatchAnalysisService, BATCH_MAX_FILES
from backend.app.services.tracking_service import TRACKING_IOU_THRESHOLD


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _det(
    class_name: str = "shipwreck",
    class_id:   int  = 2,
    bbox:       list | None = None,
    confidence: float = 0.80,
    risk_level: str   = "HIGH",
    risk_score: float = 0.75,
    filter_status: str = "PASS",
    geo_status: str = "relative",
) -> dict:
    """Return a detection dict matching AnalysisService output format."""
    return {
        "class_id":      class_id,
        "class_name":    class_name,
        "confidence":    confidence,
        "bbox":          bbox or [100.0, 100.0, 200.0, 200.0],
        "filter_status": filter_status,
        "filter_reason": None,
        "risk_score":    risk_score,
        "risk_level":    risk_level,
        "geolocation":   {
            "coordinate_system": "local_sonar",
            "status":            geo_status,
            "latitude":          None,
            "longitude":         None,
        },
    }


def _analyze_result(filename: str, detections: list, evidence: str = "ev.jpg") -> dict:
    """Return a fake AnalysisService.analyze() result dict."""
    return {
        "filename":         filename,
        "created_at":       datetime.now(timezone.utc).isoformat(),
        "detections":       detections,
        "total_detections": len(detections),
        "evidence_image":   evidence,
    }


def _make_service(side_effects: list) -> tuple:
    """
    Build a BatchAnalysisService with a mocked AnalysisService.
    side_effects: list of return values for successive analyze() calls.
    Returns (batch_svc, mock_analysis_service).
    """
    mock_analysis = MagicMock()
    mock_analysis.analyze.side_effect = side_effects
    batch_svc = BatchAnalysisService(analysis_service=mock_analysis)
    return batch_svc, mock_analysis


def _dummy_frames(n: int) -> list:
    """Return n fake (Path, filename) tuples for testing."""
    return [(Path(f"dummy_frame_{i}.jpg"), f"frame_{i}.jpg") for i in range(n)]


# ---------------------------------------------------------------------------
# Test 1: One-frame batch
# ---------------------------------------------------------------------------

class TestOneFrameBatch:

    def test_single_frame_returns_batch_result(self):
        det = _det()
        svc, _ = _make_service([_analyze_result("frame0.jpg", [det])])
        result = svc.analyze_batch(_dummy_frames(1))
        assert result["type"] == "batch"
        assert result["total_frames"] == 1
        assert result["processed_frames"] == 1

    def test_single_frame_one_track(self):
        det = _det()
        svc, _ = _make_service([_analyze_result("frame0.jpg", [det])])
        result = svc.analyze_batch(_dummy_frames(1))
        assert result["total_persistent_tracks"] == 1
        assert len(result["tracks"]) == 1

    def test_single_frame_has_batch_id(self):
        svc, _ = _make_service([_analyze_result("frame0.jpg", [])])
        result = svc.analyze_batch(_dummy_frames(1))
        assert "batch_id" in result
        assert len(result["batch_id"]) == 36  # UUID4 length

    def test_single_frame_result_structure(self):
        det = _det()
        svc, _ = _make_service([_analyze_result("frame0.jpg", [det])])
        result = svc.analyze_batch(_dummy_frames(1))
        frame = result["frames"][0]
        assert frame["frame_index"]       == 0
        assert frame["original_filename"] == "frame_0.jpg"
        assert frame["processing_status"] == "ok"
        assert isinstance(frame["detections"], list)


# ---------------------------------------------------------------------------
# Test 2: Multi-frame batch
# ---------------------------------------------------------------------------

class TestMultiFrameBatch:

    def test_three_frames_processed(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        side_effects = [
            _analyze_result("f0.jpg", [_det(bbox=bbox)]),
            _analyze_result("f1.jpg", [_det(bbox=bbox)]),
            _analyze_result("f2.jpg", [_det(bbox=bbox)]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(3))
        assert result["total_frames"]     == 3
        assert result["processed_frames"] == 3
        assert len(result["frames"])      == 3

    def test_frame_order_preserved_in_output(self):
        side_effects = [
            _analyze_result("alpha.jpg", []),
            _analyze_result("beta.jpg",  []),
            _analyze_result("gamma.jpg", []),
        ]
        svc, _ = _make_service(side_effects)
        frames = [
            (Path("a.jpg"), "alpha.jpg"),
            (Path("b.jpg"), "beta.jpg"),
            (Path("c.jpg"), "gamma.jpg"),
        ]
        result = svc.analyze_batch(frames)
        filenames = [f["original_filename"] for f in result["frames"]]
        assert filenames == ["alpha.jpg", "beta.jpg", "gamma.jpg"]

    def test_frame_indices_are_sequential(self):
        side_effects = [
            _analyze_result(f"f{i}.jpg", []) for i in range(4)
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(4))
        indices = [f["frame_index"] for f in result["frames"]]
        assert indices == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# Test 3: Same anomaly across frames → one persistent track
# ---------------------------------------------------------------------------

class TestSameAnomalyAcrossFrames:

    def test_same_class_and_bbox_across_three_frames_gives_one_track(self):
        bbox = [50.0, 50.0, 150.0, 150.0]
        side_effects = [
            _analyze_result("f0.jpg", [_det(bbox=bbox)]),
            _analyze_result("f1.jpg", [_det(bbox=bbox)]),
            _analyze_result("f2.jpg", [_det(bbox=bbox)]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(3))
        assert result["total_persistent_tracks"] == 1
        track = result["tracks"][0]
        assert track["frames_seen"]  == 3
        assert track["first_frame"]  == 0
        assert track["last_frame"]   == 2

    def test_track_class_attributes_correct(self):
        bbox = [50.0, 50.0, 150.0, 150.0]
        side_effects = [
            _analyze_result("f0.jpg", [_det(class_name="mine_cylinder", class_id=4, bbox=bbox)]),
            _analyze_result("f1.jpg", [_det(class_name="mine_cylinder", class_id=4, bbox=bbox)]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(2))
        track = result["tracks"][0]
        assert track["class_name"] == "mine_cylinder"
        assert track["class_id"]   == 4


# ---------------------------------------------------------------------------
# Test 4: Different anomalies remain separate tracks
# ---------------------------------------------------------------------------

class TestDifferentAnomaliesSeparateTracks:

    def test_two_different_classes_in_same_frame_give_two_tracks(self):
        side_effects = [
            _analyze_result("f0.jpg", [
                _det(class_name="shipwreck",    class_id=2),
                _det(class_name="ghost_net",    class_id=3, bbox=[300.0, 300.0, 400.0, 400.0]),
            ]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(1))
        assert result["total_persistent_tracks"] == 2
        names = {t["class_name"] for t in result["tracks"]}
        assert names == {"shipwreck", "ghost_net"}

    def test_same_class_far_apart_boxes_give_two_tracks(self):
        bbox_a = [0.0,   0.0,   80.0,  80.0]
        bbox_b = [900.0, 900.0, 980.0, 980.0]  # no overlap at all
        side_effects = [
            _analyze_result("f0.jpg", [
                _det(class_name="crab_pot", class_id=0, bbox=bbox_a),
                _det(class_name="crab_pot", class_id=0, bbox=bbox_b),
            ]),
            _analyze_result("f1.jpg", [
                _det(class_name="crab_pot", class_id=0, bbox=bbox_a),
                _det(class_name="crab_pot", class_id=0, bbox=bbox_b),
            ]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(2))
        assert result["total_persistent_tracks"] == 2
        for t in result["tracks"]:
            assert t["frames_seen"] == 2


# ---------------------------------------------------------------------------
# Test 5: Raw detection count vs persistent track count
# ---------------------------------------------------------------------------

class TestRawVsPersistentCount:

    def test_raw_detection_count_sums_all_pass_detections(self):
        bbox = [100.0, 100.0, 200.0, 200.0]
        # 3 frames, 1 PASS detection each → 3 raw
        side_effects = [
            _analyze_result(f"f{i}.jpg", [_det(bbox=bbox)]) for i in range(3)
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(3))
        assert result["total_raw_detections"] == 3

    def test_fail_detections_excluded_from_raw_count(self):
        side_effects = [
            _analyze_result("f0.jpg", [
                _det(filter_status="PASS"),
                _det(filter_status="FAIL", bbox=[300.0, 300.0, 400.0, 400.0]),
            ]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(1))
        # Only 1 PASS detection counted
        assert result["total_raw_detections"] == 1

    def test_multiple_frames_raw_count_summed(self):
        side_effects = [
            _analyze_result("f0.jpg", [_det(), _det(bbox=[300.0, 300.0, 400.0, 400.0])]),
            _analyze_result("f1.jpg", [_det()]),
            _analyze_result("f2.jpg", []),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(3))
        assert result["total_raw_detections"] == 3


# ---------------------------------------------------------------------------
# Test 6: Duplicate/merged detection count
# ---------------------------------------------------------------------------

class TestDuplicatesMergedCount:

    def test_one_track_seen_in_three_frames_merges_two(self):
        # 3 raw PASS detections → 1 persistent track → 2 duplicates merged
        bbox = [100.0, 100.0, 200.0, 200.0]
        side_effects = [
            _analyze_result(f"f{i}.jpg", [_det(bbox=bbox)]) for i in range(3)
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(3))
        assert result["total_persistent_tracks"] == 1
        assert result["duplicates_merged"]       == 2

    def test_two_tracks_each_seen_twice_merges_two(self):
        # 4 raw → 2 persistent → 2 merged
        bbox_a = [0.0,   0.0,   100.0, 100.0]
        bbox_b = [800.0, 800.0, 900.0, 900.0]
        side_effects = [
            _analyze_result("f0.jpg", [
                _det(bbox=bbox_a),
                _det(bbox=bbox_b, class_name="mine_cylinder", class_id=4),
            ]),
            _analyze_result("f1.jpg", [
                _det(bbox=bbox_a),
                _det(bbox=bbox_b, class_name="mine_cylinder", class_id=4),
            ]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(2))
        assert result["total_raw_detections"]    == 4
        assert result["total_persistent_tracks"] == 2
        assert result["duplicates_merged"]       == 2

    def test_no_duplicates_when_each_frame_has_unique_objects(self):
        # 3 frames, each with a different-class object at different positions
        side_effects = [
            _analyze_result("f0.jpg", [_det(class_name="shipwreck",    class_id=2, bbox=[100.0, 100.0, 200.0, 200.0])]),
            _analyze_result("f1.jpg", [_det(class_name="ghost_net",    class_id=3, bbox=[300.0, 300.0, 400.0, 400.0])]),
            _analyze_result("f2.jpg", [_det(class_name="mine_cylinder", class_id=4, bbox=[500.0, 500.0, 600.0, 600.0])]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(3))
        assert result["duplicates_merged"] == 0


# ---------------------------------------------------------------------------
# Test 7: Empty detection frame
# ---------------------------------------------------------------------------

class TestEmptyDetectionFrame:

    def test_frame_with_no_detections_still_appears_in_results(self):
        side_effects = [
            _analyze_result("f0.jpg", []),
            _analyze_result("f1.jpg", []),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(2))
        assert len(result["frames"])      == 2
        assert result["total_frames"]     == 2
        assert result["processed_frames"] == 2
        assert result["total_raw_detections"] == 0

    def test_all_empty_frames_produce_no_tracks(self):
        side_effects = [_analyze_result(f"f{i}.jpg", []) for i in range(3)]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(3))
        assert result["total_persistent_tracks"] == 0
        assert result["tracks"] == []

    def test_empty_middle_frame_track_survives_with_max_age(self):
        # Detected in frame 0, missed in frame 1, detected again in frame 2
        bbox = [100.0, 100.0, 200.0, 200.0]
        side_effects = [
            _analyze_result("f0.jpg", [_det(bbox=bbox)]),
            _analyze_result("f1.jpg", []),
            _analyze_result("f2.jpg", [_det(bbox=bbox)]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(3), max_age=2)
        # Should be ONE persistent track (frame 1 miss tolerated)
        assert result["total_persistent_tracks"] == 1
        assert result["tracks"][0]["frames_seen"] == 2


# ---------------------------------------------------------------------------
# Test 8: Maximum 10 images accepted
# ---------------------------------------------------------------------------

class TestMaxBatchSize:

    def test_ten_frames_accepted(self):
        side_effects = [_analyze_result(f"f{i}.jpg", []) for i in range(10)]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(10))
        assert result["total_frames"] == 10

    def test_exactly_batch_max_files_accepted(self):
        n = BATCH_MAX_FILES
        side_effects = [_analyze_result(f"f{i}.jpg", []) for i in range(n)]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(n))
        assert result["total_frames"] == n


# ---------------------------------------------------------------------------
# Test 9: More than 10 images rejected
# ---------------------------------------------------------------------------

class TestBatchSizeTooLarge:

    def test_eleven_frames_raises_value_error(self):
        mock_analysis = MagicMock()
        svc = BatchAnalysisService(analysis_service=mock_analysis)
        with pytest.raises(ValueError, match="exceeds maximum"):
            svc.analyze_batch(_dummy_frames(BATCH_MAX_FILES + 1))

    def test_zero_frames_raises_value_error(self):
        mock_analysis = MagicMock()
        svc = BatchAnalysisService(analysis_service=mock_analysis)
        with pytest.raises(ValueError, match="at least one"):
            svc.analyze_batch([])


# ---------------------------------------------------------------------------
# Test 10: Frame order preserved
# ---------------------------------------------------------------------------

class TestFrameOrderPreserved:

    def test_analyze_called_in_frame_order(self):
        """Verify AnalysisService.analyze() is called once per frame, in order."""
        call_order = []

        def capturing_analyze(image_path, original_filename, sonar_metadata_dict=None):
            call_order.append(original_filename)
            return _analyze_result(original_filename, [])

        mock_analysis = MagicMock()
        mock_analysis.analyze.side_effect = capturing_analyze
        svc = BatchAnalysisService(analysis_service=mock_analysis)

        frames = [
            (Path("f3.jpg"), "frame_3.jpg"),
            (Path("f1.jpg"), "frame_1.jpg"),
            (Path("f0.jpg"), "frame_0.jpg"),
        ]
        svc.analyze_batch(frames)
        assert call_order == ["frame_3.jpg", "frame_1.jpg", "frame_0.jpg"]

    def test_output_frames_order_matches_input_order(self):
        filenames = ["zulu.jpg", "alpha.jpg", "mike.jpg"]
        side_effects = [_analyze_result(fn, []) for fn in filenames]
        svc, _ = _make_service(side_effects)
        frames = [(Path(fn), fn) for fn in filenames]
        result = svc.analyze_batch(frames)
        out_names = [f["original_filename"] for f in result["frames"]]
        assert out_names == filenames


# ---------------------------------------------------------------------------
# Test 11: Geolocation is not fabricated
# ---------------------------------------------------------------------------

class TestGeolocationNotFabricated:

    def test_geolocation_from_detection_preserved_verbatim(self):
        geo = {
            "coordinate_system": "local_sonar",
            "status":            "relative",
            "latitude":          None,
            "longitude":         None,
        }
        det = {
            "class_id":      2,
            "class_name":    "shipwreck",
            "confidence":    0.80,
            "bbox":          [100.0, 100.0, 200.0, 200.0],
            "filter_status": "PASS",
            "filter_reason": None,
            "risk_score":    0.75,
            "risk_level":    "HIGH",
            "geolocation":   geo,
        }
        svc, _ = _make_service([_analyze_result("f0.jpg", [det])])
        result = svc.analyze_batch(_dummy_frames(1))
        track = result["tracks"][0]
        bbox_entry = track["bbox_history"][0]
        assert bbox_entry["geolocation"] == geo

    def test_no_geolocation_in_detection_results_in_none_not_invented(self):
        det = _det()
        # Remove geolocation from detection to simulate a missing field
        det.pop("geolocation", None)
        svc, _ = _make_service([_analyze_result("f0.jpg", [det])])
        result = svc.analyze_batch(_dummy_frames(1))
        track = result["tracks"][0]
        bbox_entry = track["bbox_history"][0]
        # Should be None, not a fabricated coordinate dict
        assert bbox_entry["geolocation"] is None

    def test_track_level_geo_not_averaged_or_invented(self):
        """Track dict must NOT contain a 'latitude' or 'longitude' key
        that was invented by the tracker (only per-bbox-entry geos are stored)."""
        bbox = [100.0, 100.0, 200.0, 200.0]
        side_effects = [
            _analyze_result("f0.jpg", [_det(bbox=bbox)]),
            _analyze_result("f1.jpg", [_det(bbox=bbox)]),
        ]
        svc, _ = _make_service(side_effects)
        result = svc.analyze_batch(_dummy_frames(2))
        track = result["tracks"][0]
        # Fabricated top-level geo should not exist
        assert "latitude"  not in track
        assert "longitude" not in track


# ---------------------------------------------------------------------------
# Test: None analysis_service raises immediately
# ---------------------------------------------------------------------------

class TestInitValidation:

    def test_none_analysis_service_raises(self):
        with pytest.raises(ValueError, match="must not be None"):
            BatchAnalysisService(analysis_service=None)


# ---------------------------------------------------------------------------
# Test: Frame that errors does not abort remaining frames
# ---------------------------------------------------------------------------

class TestFrameError:

    def test_erroring_frame_recorded_with_error_status(self):
        def fail_on_second(image_path, original_filename, sonar_metadata_dict=None):
            if "frame_1" in original_filename:
                raise RuntimeError("Simulated YOLO failure")
            return _analyze_result(original_filename, [])

        mock_analysis = MagicMock()
        mock_analysis.analyze.side_effect = fail_on_second
        svc = BatchAnalysisService(analysis_service=mock_analysis)

        frames = [(Path(f"f{i}.jpg"), f"frame_{i}.jpg") for i in range(3)]
        result = svc.analyze_batch(frames)

        assert result["total_frames"]     == 3
        assert result["processed_frames"] == 2
        error_frame = result["frames"][1]
        assert "error" in error_frame["processing_status"]
        assert error_frame["detections"] == []
