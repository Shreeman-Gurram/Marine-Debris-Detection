"""
backend/tests/test_batch_api.py
==================================
SONARIS Phase 2 — API-level tests for batch endpoints.

Uses FastAPI TestClient with mocked services so no real YOLO model,
no real MongoDB connection, and no real image files are needed.

Endpoints tested:
  POST /api/analyze/batch
  GET  /api/batches
  GET  /api/batches/{batch_id}
  POST /api/analyze            (regression — must still work)

Run with:
    python -m pytest backend/tests/test_batch_api.py -v
"""

from __future__ import annotations

import io
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app.  Lazy singletons (_service, _batch_service) are None
# at import time and are only populated on the first request — safe to import
# without a real model on disk.
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Shared fake data builders
# ---------------------------------------------------------------------------

def _fake_batch_result(n_frames: int = 2, n_tracks: int = 1) -> dict:
    return {
        "batch_id":                str(uuid.uuid4()),
        "type":                    "batch",
        "created_at":              "2026-01-01T00:00:00+00:00",
        "total_frames":            n_frames,
        "processed_frames":        n_frames,
        "total_raw_detections":    n_tracks * n_frames,
        "total_persistent_tracks": n_tracks,
        "duplicates_merged":       n_tracks * (n_frames - 1),
        "frames": [
            {
                "frame_index":       i,
                "original_filename": f"frame_{i}.jpg",
                "detections":        [],
                "evidence_filename": f"ev_{i}.jpg",
                "processing_status": "ok",
            }
            for i in range(n_frames)
        ],
        "tracks": [
            {
                "track_id":           f"track_fake_{j}",
                "class_id":           2,
                "class_name":         "shipwreck",
                "frames_seen":        n_frames,
                "first_frame":        0,
                "last_frame":         n_frames - 1,
                "max_confidence":     0.90,
                "avg_confidence":     0.85,
                "max_risk_score":     0.80,
                "avg_risk_score":     0.75,
                "highest_risk_level": "HIGH",
                "bbox_history":       [],
                "confidence_history": [],
                "risk_history":       [],
                "risk_score_history": [],
                "frame_indices":      list(range(n_frames)),
            }
            for j in range(n_tracks)
        ],
    }


def _fake_single_result() -> dict:
    return {
        "filename":         "test.jpg",
        "created_at":       "2026-01-01T00:00:00+00:00",
        "detections":       [],
        "total_detections": 0,
        "evidence_image":   "test_evidence_abc12345.jpg",
        "analysis_id":      "507f1f77bcf86cd799439011",
    }


def _jpg_bytes(tag: str = "A") -> bytes:
    """Return minimal bytes for a 'JPEG' upload (content doesn't matter since service is mocked)."""
    return f"FAKE_JPEG_{tag}".encode()


def _upload_files(n: int, ext: str = ".jpg") -> list:
    """Build a list of (field, (filename, bytes, mimetype)) tuples for TestClient."""
    return [
        ("files", (f"frame_{i}{ext}", io.BytesIO(_jpg_bytes(str(i))), "image/jpeg"))
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Test 1: POST /api/analyze/batch success
# ---------------------------------------------------------------------------

class TestBatchAnalyzeSuccess:

    def test_batch_returns_200(self):
        fake_result = _fake_batch_result()
        with patch("backend.app.main._get_batch_service") as mock_get_svc, \
             patch("backend.app.main.insert_batch_analysis", return_value="507f191e810c19729de860ea"):
            mock_svc = MagicMock()
            mock_svc.analyze_batch.return_value = fake_result
            mock_get_svc.return_value = mock_svc

            resp = client.post("/api/analyze/batch", files=_upload_files(2))
        assert resp.status_code == 200

    def test_batch_response_contains_required_keys(self):
        fake_result = _fake_batch_result()
        with patch("backend.app.main._get_batch_service") as mock_get_svc, \
             patch("backend.app.main.insert_batch_analysis", return_value="507f191e810c19729de860ea"):
            mock_svc = MagicMock()
            mock_svc.analyze_batch.return_value = fake_result
            mock_get_svc.return_value = mock_svc

            resp = client.post("/api/analyze/batch", files=_upload_files(2))

        body = resp.json()
        for key in ("batch_id", "type", "total_frames", "processed_frames",
                    "total_raw_detections", "total_persistent_tracks",
                    "duplicates_merged", "frames", "tracks"):
            assert key in body, f"Missing key: {key}"

    def test_batch_type_field_is_batch(self):
        fake_result = _fake_batch_result()
        with patch("backend.app.main._get_batch_service") as mock_get_svc, \
             patch("backend.app.main.insert_batch_analysis", return_value="fake_id"):
            mock_svc = MagicMock()
            mock_svc.analyze_batch.return_value = fake_result
            mock_get_svc.return_value = mock_svc
            resp = client.post("/api/analyze/batch", files=_upload_files(1))
        assert resp.json()["type"] == "batch"


# ---------------------------------------------------------------------------
# Test 2: Multiple uploaded files
# ---------------------------------------------------------------------------

class TestMultipleUploadedFiles:

    def test_five_files_accepted(self):
        fake_result = _fake_batch_result(n_frames=5)
        with patch("backend.app.main._get_batch_service") as mock_get_svc, \
             patch("backend.app.main.insert_batch_analysis", return_value="fake_id"):
            mock_svc = MagicMock()
            mock_svc.analyze_batch.return_value = fake_result
            mock_get_svc.return_value = mock_svc
            resp = client.post("/api/analyze/batch", files=_upload_files(5))
        assert resp.status_code == 200

    def test_analyze_batch_called_with_correct_frame_count(self):
        fake_result = _fake_batch_result(n_frames=3)
        with patch("backend.app.main._get_batch_service") as mock_get_svc, \
             patch("backend.app.main.insert_batch_analysis", return_value="fake_id"):
            mock_svc = MagicMock()
            mock_svc.analyze_batch.return_value = fake_result
            mock_get_svc.return_value = mock_svc
            client.post("/api/analyze/batch", files=_upload_files(3))
            call_args = mock_svc.analyze_batch.call_args
        # frames argument should have 3 tuples
        frames_arg = call_args[1].get("frames") or call_args[0][0]
        assert len(frames_arg) == 3


# ---------------------------------------------------------------------------
# Test 3: Zero files → 400
# ---------------------------------------------------------------------------

class TestZeroFiles:

    def test_no_files_returns_400(self):
        # Send request with empty files list — FastAPI will raise 422
        # because files is required. Either 400 or 422 is acceptable.
        resp = client.post("/api/analyze/batch")
        assert resp.status_code in (400, 422)

    def test_error_detail_present(self):
        resp = client.post("/api/analyze/batch")
        body = resp.json()
        assert "detail" in body


# ---------------------------------------------------------------------------
# Test 4: >10 files → 400
# ---------------------------------------------------------------------------

class TestTooManyFiles:

    def test_eleven_files_returns_400(self):
        resp = client.post("/api/analyze/batch", files=_upload_files(11))
        assert resp.status_code == 400

    def test_error_message_mentions_limit(self):
        resp = client.post("/api/analyze/batch", files=_upload_files(11))
        detail = resp.json().get("detail", "")
        assert "10" in detail or "maximum" in detail.lower() or "exceed" in detail.lower()


# ---------------------------------------------------------------------------
# Test 5: Invalid image type → 415
# ---------------------------------------------------------------------------

class TestInvalidImageType:

    def test_pdf_file_rejected(self):
        files = [("files", ("document.pdf", io.BytesIO(b"PDF"), "application/pdf"))]
        resp = client.post("/api/analyze/batch", files=files)
        assert resp.status_code == 415

    def test_txt_file_rejected(self):
        files = [("files", ("data.txt", io.BytesIO(b"text"), "text/plain"))]
        resp = client.post("/api/analyze/batch", files=files)
        assert resp.status_code == 415

    def test_valid_png_accepted(self):
        fake_result = _fake_batch_result(n_frames=1)
        files = [("files", ("frame.png", io.BytesIO(b"FAKE_PNG"), "image/png"))]
        with patch("backend.app.main._get_batch_service") as mock_get_svc, \
             patch("backend.app.main.insert_batch_analysis", return_value="fake_id"):
            mock_svc = MagicMock()
            mock_svc.analyze_batch.return_value = fake_result
            mock_get_svc.return_value = mock_svc
            resp = client.post("/api/analyze/batch", files=files)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 6: GET /api/batches/{batch_id}
# ---------------------------------------------------------------------------

class TestGetBatch:

    def test_valid_objectid_returns_200_when_found(self):
        fake_doc = {"_id": "507f191e810c19729de860ea", "batch_id": "abc", "type": "batch"}
        mock_col = MagicMock()
        mock_col.find_one.return_value = {"_id": MagicMock(__str__=lambda s: "507f191e810c19729de860ea"), "batch_id": "abc"}
        with patch("backend.app.main.get_batches_collection", return_value=mock_col):
            resp = client.get("/api/batches/507f191e810c19729de860ea")
        assert resp.status_code == 200

    def test_invalid_objectid_format_returns_400(self):
        resp = client.get("/api/batches/not_a_valid_objectid")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Test 7: Missing batch → 404
# ---------------------------------------------------------------------------

class TestBatchNotFound:

    def test_unknown_batch_returns_404(self):
        mock_col = MagicMock()
        mock_col.find_one.return_value = None
        with patch("backend.app.main.get_batches_collection", return_value=mock_col):
            resp = client.get("/api/batches/507f191e810c19729de860ea")
        assert resp.status_code == 404

    def test_404_detail_mentions_batch(self):
        mock_col = MagicMock()
        mock_col.find_one.return_value = None
        with patch("backend.app.main.get_batches_collection", return_value=mock_col):
            resp = client.get("/api/batches/507f191e810c19729de860ea")
        assert "507f191e810c19729de860ea" in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# Test 8: GET /api/batches
# ---------------------------------------------------------------------------

class TestListBatches:

    def test_list_batches_returns_200(self):
        mock_col = MagicMock()
        mock_col.find.return_value.sort.return_value.limit.return_value = []
        with patch("backend.app.main.get_batches_collection", return_value=mock_col):
            resp = client.get("/api/batches")
        assert resp.status_code == 200

    def test_list_batches_returns_list(self):
        mock_col = MagicMock()
        mock_col.find.return_value.sort.return_value.limit.return_value = []
        with patch("backend.app.main.get_batches_collection", return_value=mock_col):
            resp = client.get("/api/batches")
        assert isinstance(resp.json(), list)

    def test_list_batches_with_results(self):
        fake_doc = {
            "_id":                     MagicMock(__str__=lambda s: "507f191e810c19729de860ea"),
            "batch_id":                "abc-123",
            "type":                    "batch",
            "created_at":              "2026-01-01T00:00:00+00:00",
            "total_frames":            3,
            "processed_frames":        3,
            "total_raw_detections":    5,
            "total_persistent_tracks": 2,
            "duplicates_merged":       3,
        }
        mock_col = MagicMock()
        mock_col.find.return_value.sort.return_value.limit.return_value = [fake_doc]
        with patch("backend.app.main.get_batches_collection", return_value=mock_col):
            resp = client.get("/api/batches")
        body = resp.json()
        assert len(body) == 1
        assert body[0]["batch_id"] == "abc-123"

    def test_list_batches_limit_param_forwarded(self):
        mock_col = MagicMock()
        mock_col.find.return_value.sort.return_value.limit.return_value = []
        with patch("backend.app.main.get_batches_collection", return_value=mock_col):
            client.get("/api/batches?limit=5")
        # Verify .limit(5) was called
        mock_col.find.return_value.sort.return_value.limit.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# Test 9: Existing POST /api/analyze regression
# ---------------------------------------------------------------------------

class TestSingleAnalyzeRegression:

    def test_existing_analyze_endpoint_still_returns_200(self):
        fake_result = _fake_single_result()
        with patch("backend.app.main._get_service") as mock_get_svc, \
             patch("backend.app.main.insert_analysis", return_value="507f1f77bcf86cd799439011"):
            mock_svc = MagicMock()
            mock_svc.analyze.return_value = fake_result
            mock_get_svc.return_value = mock_svc

            files = [("file", ("test.jpg", io.BytesIO(_jpg_bytes()), "image/jpeg"))]
            resp = client.post("/api/analyze", files=files)
        assert resp.status_code == 200

    def test_existing_analyze_response_has_analysis_id(self):
        fake_result = _fake_single_result()
        with patch("backend.app.main._get_service") as mock_get_svc, \
             patch("backend.app.main.insert_analysis", return_value="507f1f77bcf86cd799439011"):
            mock_svc = MagicMock()
            mock_svc.analyze.return_value = fake_result
            mock_get_svc.return_value = mock_svc

            files = [("file", ("test.jpg", io.BytesIO(_jpg_bytes()), "image/jpeg"))]
            resp = client.post("/api/analyze", files=files)
        body = resp.json()
        assert "analysis_id" in body

    def test_existing_analyze_response_has_detections_key(self):
        fake_result = _fake_single_result()
        with patch("backend.app.main._get_service") as mock_get_svc, \
             patch("backend.app.main.insert_analysis", return_value="507f1f77bcf86cd799439011"):
            mock_svc = MagicMock()
            mock_svc.analyze.return_value = fake_result
            mock_get_svc.return_value = mock_svc

            files = [("file", ("test.jpg", io.BytesIO(_jpg_bytes()), "image/jpeg"))]
            resp = client.post("/api/analyze", files=files)
        assert "detections" in resp.json()

    def test_single_analyze_rejects_pdf(self):
        files = [("file", ("report.pdf", io.BytesIO(b"PDF"), "application/pdf"))]
        resp = client.post("/api/analyze", files=files)
        assert resp.status_code == 415

    def test_batch_endpoint_does_not_affect_single_analyze_route(self):
        """Verify the two routes are completely independent."""
        fake_batch = _fake_batch_result()
        fake_single = _fake_single_result()

        with patch("backend.app.main._get_batch_service") as mock_batch_svc_getter, \
             patch("backend.app.main._get_service") as mock_single_svc_getter, \
             patch("backend.app.main.insert_batch_analysis", return_value="batch_db_id"), \
             patch("backend.app.main.insert_analysis", return_value="single_db_id"):

            mock_batch = MagicMock()
            mock_batch.analyze_batch.return_value = fake_batch
            mock_batch_svc_getter.return_value = mock_batch

            mock_single = MagicMock()
            mock_single.analyze.return_value = fake_single
            mock_single_svc_getter.return_value = mock_single

            batch_resp  = client.post("/api/analyze/batch", files=_upload_files(2))
            single_resp = client.post(
                "/api/analyze",
                files=[("file", ("test.jpg", io.BytesIO(_jpg_bytes()), "image/jpeg"))],
            )

        assert batch_resp.status_code  == 200
        assert single_resp.status_code == 200
        assert batch_resp.json()["type"] == "batch"
        # Single result should NOT have a "type": "batch" field
        assert single_resp.json().get("type") != "batch"


# ---------------------------------------------------------------------------
# Test: Existing survey endpoints unaffected
# ---------------------------------------------------------------------------

class TestExistingSurveyEndpointsUnaffected:

    def test_health_endpoint_still_works(self):
        with patch("backend.app.main.is_model_available", return_value=True):
            resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"

    def test_surveys_list_endpoint_unaffected(self):
        mock_col = MagicMock()
        mock_col.find.return_value.sort.return_value.limit.return_value = []
        with patch("backend.app.main.get_analyses_collection", return_value=mock_col):
            resp = client.get("/api/surveys")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
