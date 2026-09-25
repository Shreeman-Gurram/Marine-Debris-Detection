"""
backend/tests/smoke_test_batch_real.py
SONARIS Phase 2 - Real-World Batch Smoke Test
ASCII-only output for Windows console compatibility.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def sep(): print("-" * 65)
def section(t): print("\n" + "=" * 65); print("  " + t); print("=" * 65)
def ok(msg): print("  [PASS] " + msg)
def fail(msg): print("  [FAIL] " + msg)
def info(msg): print("  " + msg)
def warn(msg): print("  [WARN] " + msg)

ALL_PASS = [True]   # mutable flag

def check(label, cond, detail=""):
    if cond:
        print(f"  [PASS] {label}" + (f"  ({detail})" if detail else ""))
    else:
        print(f"  [FAIL] {label}" + (f"  ({detail})" if detail else ""))
        ALL_PASS[0] = False
    return cond

# ---------------------------------------------------------------------------
section("SONARIS Phase 2 - Real-World Batch Smoke Test")
info(f"Project root: {PROJECT_ROOT}")

from backend.app.services.model_loader import ensure_model_available
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.batch_service import BatchAnalysisService
from backend.app.database.mongodb import (
    insert_batch_analysis, get_batches_collection, MongoUnavailableError,
)
from bson import ObjectId

# ---------------------------------------------------------------------------
section("Step 1 - Locate Test Images")
TEST_DATA = PROJECT_ROOT / "test_data"
jpgs = sorted(TEST_DATA.glob("*.jpg"))
info(f"Available JPGs: {[p.name for p in jpgs]}")

frames = [(p, p.name) for p in jpgs[:5]]
info(f"Selected {len(frames)} frame(s): {[f[1] for f in frames]}")
check("At least 2 frames selected", len(frames) >= 2, f"{len(frames)} frames")

# ---------------------------------------------------------------------------
section("Step 2 - Load Real YOLO Model")
t0 = time.time()
model_path = ensure_model_available()
info(f"model_path = {model_path}")
check("Model file exists on disk", model_path.exists())

analysis_svc = AnalysisService(model_path=model_path)
batch_svc    = BatchAnalysisService(analysis_service=analysis_svc)
info(f"Model loaded in {time.time()-t0:.2f}s")
ok("AnalysisService and BatchAnalysisService instantiated")

# ---------------------------------------------------------------------------
section("Step 3 - Run Real Batch Pipeline")
info(f"Processing {len(frames)} frames...")
t1 = time.time()
result = batch_svc.analyze_batch(frames=frames, sonar_metadata_dict=None)
elapsed = time.time() - t1
info(f"Batch completed in {elapsed:.2f}s")

# ---------------------------------------------------------------------------
section("Step 4 - Per-Frame Detection Report")
prev_idx = -1
for fr in result["frames"]:
    fi        = fr["frame_index"]
    fname     = fr["original_filename"]
    status    = fr["processing_status"]
    dets      = fr["detections"]
    pass_dets = [d for d in dets if d.get("filter_status") == "PASS"]
    evid      = fr.get("evidence_filename") or "(none)"
    sep()
    info(f"Frame {fi}: {fname}")
    info(f"  status          = {status}")
    info(f"  all_detections  = {len(dets)}")
    info(f"  PASS_detections = {len(pass_dets)}")
    info(f"  evidence_image  = {evid}")
    for d in pass_dets:
        info(f"    [{d['class_name']:25s}] conf={d['confidence']:.4f}  "
             f"risk={d['risk_level']:8s}  bbox={d['bbox']}")
    if not pass_dets:
        warn("No PASS detections in this frame")

    check(f"Frame {fi} order is sequential", fi > prev_idx, f"{prev_idx}->{fi}")
    check(f"Frame {fi} processed ok", status == "ok", status)
    check(f"Frame {fi} has evidence", evid != "(none)", evid)
    prev_idx = fi

# ---------------------------------------------------------------------------
section("Step 5 - Batch Summary")
info(f"batch_id                = {result['batch_id']}")
info(f"type                    = {result['type']}")
info(f"total_frames            = {result['total_frames']}")
info(f"processed_frames        = {result['processed_frames']}")
info(f"total_raw_detections    = {result['total_raw_detections']}")
info(f"total_persistent_tracks = {result['total_persistent_tracks']}")
info(f"duplicates_merged       = {result['duplicates_merged']}")

check("All frames processed", result["processed_frames"] == result["total_frames"])
check("type == 'batch'", result["type"] == "batch")
check("batch_id is non-empty", bool(result.get("batch_id")))

# ---------------------------------------------------------------------------
section("Step 6 - Persistent Anomaly Tracking Report")
tracks = result.get("tracks", [])
info(f"Total persistent tracks: {len(tracks)}")
sep()

if tracks:
    for t in tracks:
        info(f"  track_id       = {t['track_id']}")
        info(f"  class_name     = {t['class_name']}")
        info(f"  frames_seen    = {t['frames_seen']}")
        info(f"  frame_indices  = {t['frame_indices']}")
        info(f"  max_confidence = {t['max_confidence']}")
        info(f"  max_risk       = {t['highest_risk_level']}")
        for bh in t.get("bbox_history", []):
            geo = bh.get("geolocation") or {}
            lat = geo.get("latitude")
            lon = geo.get("longitude")
            coord_sys = geo.get("coordinate_system", "N/A")
            geo_status = geo.get("status", "N/A")
            if lat is not None and lon is not None:
                info(f"    frame={bh['frame_index']} bbox={bh['bbox']} geo=WGS84 lat={lat:.6f} lon={lon:.6f}")
            else:
                info(f"    frame={bh['frame_index']} bbox={bh['bbox']} geo={coord_sys}/{geo_status} lat=None lon=None (not fabricated)")
        sep()

    multi = [t for t in tracks if t["frames_seen"] > 1]
    if multi:
        ok(f"TRACKING DEMONSTRATED: {len(multi)} track(s) persist across multiple frames.")
        for t in multi:
            info(f"  '{t['class_name']}' seen in {t['frames_seen']} frames "
                 f"(frames {t['first_frame']}-{t['last_frame']}), "
                 f"{result['duplicates_merged']} duplicate(s) merged.")
    else:
        warn(
            "Tracking could not be demonstrated because the real images did not "
            "contain sufficiently overlapping detections across consecutive frames. "
            f"All {len(tracks)} detection(s) are present but none persisted across "
            "frames at the current IoU threshold (0.35)."
        )
else:
    warn("No persistent tracks - no PASS detections returned across frames.")

# ---------------------------------------------------------------------------
section("Step 7 - MongoDB Persistence")
batch_db_id = None
mongo_ok = False
try:
    batch_db_id = insert_batch_analysis(result)
    ok(f"Batch inserted into 'batches' collection. _id = {batch_db_id}")
    mongo_ok = True
except MongoUnavailableError as e:
    fail(f"MongoDB unavailable: {e}")
except Exception as e:
    fail(f"MongoDB insert failed: {e}")
check("Batch document inserted into MongoDB batches collection", mongo_ok)

# ---------------------------------------------------------------------------
section("Step 8 - Retrieve Batch from MongoDB (GET /api/batches/{id})")
retrieve_ok = False
if mongo_ok and batch_db_id:
    try:
        col = get_batches_collection()
        doc = col.find_one({"_id": ObjectId(batch_db_id)})
        if doc:
            id_match = doc.get("batch_id") == result["batch_id"]
            info(f"Document retrieved. batch_id_match={id_match} total_frames={doc.get('total_frames')} type={doc.get('type')}")
            retrieve_ok = True
        else:
            fail(f"Document not found for _id={batch_db_id}")
    except Exception as e:
        fail(f"Retrieval error: {e}")
else:
    warn("Skipped - MongoDB insert did not succeed")
check("Batch retrievable from MongoDB by _id", retrieve_ok)

# ---------------------------------------------------------------------------
section("Step 9 - Single-Image Regression Check")
single_ok = False
single_result = None
try:
    single_result = analysis_svc.analyze(
        image_path=frames[0][0],
        original_filename=frames[0][1],
        sonar_metadata_dict=None,
    )
    info(f"filename         = {single_result['filename']}")
    info(f"total_detections = {single_result['total_detections']}")
    info(f"evidence_image   = {single_result.get('evidence_image', '(none)')}")
    single_ok = True
except Exception as e:
    fail(f"Single-image analysis failed: {e}")

check("Single-image pipeline works independently", single_ok)
check(
    "Single-image result has no type='batch'",
    (single_result or {}).get("type") != "batch",
)

# ---------------------------------------------------------------------------
section("Step 10 - Evidence Image Disk Check")
EVDIR = PROJECT_ROOT / "outputs" / "evidence"
ev_filenames = [fr.get("evidence_filename") for fr in result["frames"] if fr.get("evidence_filename")]
info(f"Evidence images listed in batch result: {len(ev_filenames)}")
for ev in ev_filenames:
    path = EVDIR / ev
    exists = path.exists()
    check(f"Evidence file exists: {ev}", exists)

# ---------------------------------------------------------------------------
section("FINAL SMOKE TEST REPORT")
info(f"Images used          : {', '.join(f[1] for f in frames)}")
info(f"Frames processed     : {result['processed_frames']} / {result['total_frames']}")
info(f"Total raw detections : {result['total_raw_detections']}")
info(f"Persistent tracks    : {result['total_persistent_tracks']}")
info(f"Duplicates merged    : {result['duplicates_merged']}")
info(f"batch_id             : {result['batch_id']}")
info(f"MongoDB _id          : {batch_db_id or 'N/A'}")
info(f"Elapsed              : {elapsed:.2f}s")
sep()
if ALL_PASS[0]:
    print("  ALL CHECKS PASSED - Phase 2 smoke test SUCCESSFUL.")
else:
    print("  SOME CHECKS FAILED - see details above.")
sep()
sys.exit(0 if ALL_PASS[0] else 1)
