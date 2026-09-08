"""
backend/app/main.py
====================
SONARIS Backend — FastAPI Application

Routes:
  GET  /api/health                              — liveness probe
  POST /api/analyze                             — sonar anomaly detection pipeline
  GET  /api/evidence/{filename}                 — serve generated evidence images
  GET  /api/surveys                             — list recent analyses from MongoDB
  GET  /api/surveys/stats                       — dashboard summary stats
  GET  /api/surveys/{analysis_id}               — fetch one analysis by id
  PUT  /api/surveys/{analysis_id}/verifications — persist operator decisions
  GET  /api/surveys/{analysis_id}/report/pdf    — generate + download PDF report
"""

from __future__ import annotations

import io
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .services.analysis_service import AnalysisService, EVIDENCE_DIR
from .database.mongodb import (
    insert_analysis,
    get_analyses_collection,
    MongoUnavailableError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("sonaris.api")

# ---------------------------------------------------------------------------
# Project root — walk up from __file__ to find the dir containing models/
# ---------------------------------------------------------------------------
def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "models" / "best_detector.pt").exists():
            return parent
    return here.parent.parent.parent


_PROJECT_ROOT = _find_project_root()
_MODEL_PATH   = _PROJECT_ROOT / "models" / "best_detector.pt"

app = FastAPI(
    title="SONARIS Backend",
    description="AI-powered Side-Scan Sonar (SSS) anomaly detection system",
    version="0.4.0",
)

# Allow Vite dev server (port 5173) to call the API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Lazy model service — loaded once on first request
# ---------------------------------------------------------------------------
_service: Optional[AnalysisService] = None


def _get_service() -> AnalysisService:
    global _service
    if _service is None:
        if not _MODEL_PATH.exists():
            raise RuntimeError(
                f"YOLO model not found: {_MODEL_PATH}. "
                "Ensure models/best_detector.pt exists in the project root."
            )
        _service = AnalysisService(model_path=_MODEL_PATH)
    return _service


# ---------------------------------------------------------------------------
# Helper: serialize MongoDB document for JSON response
# ---------------------------------------------------------------------------
def _serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    return out


# ---------------------------------------------------------------------------
# Routes — health
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """Liveness probe."""
    return {"status": "ok", "service": "sonaris-backend"}


# ---------------------------------------------------------------------------
# Routes — evidence images
# ---------------------------------------------------------------------------

@app.get("/api/evidence/{filename}", response_class=FileResponse,
         summary="Retrieve a generated evidence image")
async def get_evidence_image(filename: str) -> FileResponse:
    """
    Serve an annotated evidence image by filename.
    Safe path handling: only files directly inside outputs/evidence/ are served.
    """
    safe_name = Path(filename).name
    if safe_name != filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400,
                            detail="Invalid filename. Only bare filenames accepted.")
    evidence_path = EVIDENCE_DIR / safe_name
    try:
        resolved = evidence_path.resolve()
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal rejected.")

    if not resolved.exists():
        raise HTTPException(status_code=404,
                            detail=f"Evidence image '{safe_name}' not found.")

    return FileResponse(path=str(resolved), media_type="image/jpeg",
                        filename=safe_name)


# ---------------------------------------------------------------------------
# Routes — survey history (MongoDB-backed)
# ---------------------------------------------------------------------------

@app.get("/api/surveys/stats", summary="Dashboard summary stats")
async def get_survey_stats():
    """
    Return real statistics from the analyses collection.
    Returns zeroes when no analyses exist — never fabricates data.
    """
    try:
        col = get_analyses_collection()
        total = col.count_documents({})
        if total == 0:
            return {
                "total_surveys":     0,
                "total_anomalies":   0,
                "high_priority":     0,
                "reviewed":          0,
            }

        pipeline = [
            {"$unwind": {"path": "$detections", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": None,
                "total_anomalies": {"$sum": {"$cond": [{"$ifNull": ["$detections", False]}, 1, 0]}},
                "high_priority":   {"$sum": {
                    "$cond": [
                        {"$in": [{"$ifNull": ["$detections.risk_level", ""]}, ["HIGH", "CRITICAL"]]}, 1, 0
                    ]
                }},
            }},
        ]
        agg = list(col.aggregate(pipeline))
        agg_row = agg[0] if agg else {}

        # Count surveys that have at least one verified detection
        reviewed = col.count_documents({"verifications": {"$exists": True, "$not": {"$size": 0}}})

        return {
            "total_surveys":   total,
            "total_anomalies": agg_row.get("total_anomalies", 0),
            "high_priority":   agg_row.get("high_priority", 0),
            "reviewed":        reviewed,
        }
    except MongoUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Stats aggregation error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Stats failed: {exc}")


@app.get("/api/surveys", summary="List recent analyses")
async def list_surveys(limit: int = 20):
    """
    Return the most recent analyses from MongoDB.
    """
    try:
        col = get_analyses_collection()
        docs = list(col.find({}).sort("created_at", -1).limit(limit))
        return [_serialize_doc(d) for d in docs]
    except MongoUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("List surveys error: %s", exc)
        raise HTTPException(status_code=500, detail=f"List failed: {exc}")


@app.get("/api/surveys/{analysis_id}", summary="Fetch one analysis by ID")
async def get_survey(analysis_id: str):
    """
    Fetch a single analysis document by its MongoDB ObjectId string.
    """
    try:
        oid = ObjectId(analysis_id)
    except Exception:
        raise HTTPException(status_code=400,
                            detail=f"Invalid analysis_id format: '{analysis_id}'")
    try:
        col = get_analyses_collection()
        doc = col.find_one({"_id": oid})
        if doc is None:
            raise HTTPException(status_code=404,
                                detail=f"Analysis '{analysis_id}' not found.")
        return _serialize_doc(doc)
    except HTTPException:
        raise
    except MongoUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Get survey error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Fetch failed: {exc}")


# ---------------------------------------------------------------------------
# Routes — operator verification (persistent)
# ---------------------------------------------------------------------------

@app.put("/api/surveys/{analysis_id}/verifications",
         summary="Persist operator verification decisions")
async def put_verifications(
    analysis_id: str,
    payload: Dict[str, Any] = Body(...),
):
    """
    Upsert operator verification decisions into the survey document.

    Expected body:
        {
          "verifications": [
            { "detection_index": 0, "decision": "Confirmed", "operator": "...",
              "notes": "...", "timestamp": "..." },
            ...
          ]
        }

    If a verification already exists for the same detection_index it is replaced.
    """
    try:
        oid = ObjectId(analysis_id)
    except Exception:
        raise HTTPException(status_code=400,
                            detail=f"Invalid analysis_id: '{analysis_id}'")

    verifications = payload.get("verifications")
    if not isinstance(verifications, list):
        raise HTTPException(status_code=422,
                            detail="Body must contain a 'verifications' list.")

    allowed_decisions = {"Confirmed", "Rejected", "Uncertain"}
    for v in verifications:
        if v.get("decision") not in allowed_decisions:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid decision '{v.get('decision')}'. "
                       f"Allowed: {sorted(allowed_decisions)}",
            )

    try:
        col = get_analyses_collection()
        doc = col.find_one({"_id": oid}, {"verifications": 1})
        if doc is None:
            raise HTTPException(status_code=404,
                                detail=f"Analysis '{analysis_id}' not found.")

        # Build merged verification map keyed by detection_index
        existing_map: Dict[int, Any] = {}
        for v in (doc.get("verifications") or []):
            existing_map[v["detection_index"]] = v

        for v in verifications:
            idx = int(v["detection_index"])
            entry = {
                "detection_index": idx,
                "decision":        v["decision"],
                "operator":        v.get("operator", "Operator"),
                "notes":           v.get("notes", ""),
                "timestamp":       v.get("timestamp", datetime.now(timezone.utc).isoformat()),
            }
            existing_map[idx] = entry

        merged = list(existing_map.values())
        col.update_one(
            {"_id": oid},
            {"$set": {"verifications": merged, "verified_at": datetime.now(timezone.utc).isoformat()}},
        )
        logger.info("Verifications updated. analysis_id=%s  count=%d", analysis_id, len(merged))
        return {"status": "ok", "analysis_id": analysis_id, "verifications_stored": len(merged)}

    except HTTPException:
        raise
    except MongoUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Verification update error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Verification update failed: {exc}")


# ---------------------------------------------------------------------------
# Routes — PDF report
# ---------------------------------------------------------------------------

def _build_pdf_report(doc: dict) -> bytes:
    """Generate a professional PDF report for one survey using ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    buf = io.BytesIO()

    # ---- colour palette (light marine theme) ----
    NAVY   = colors.HexColor("#073B5C")
    OCEAN  = colors.HexColor("#159BD3")
    PANEL  = colors.HexColor("#EAF6FB")
    MUTED  = colors.HexColor("#7A8FA6")
    RED    = colors.HexColor("#E04C5A")
    GREEN  = colors.HexColor("#1E9E6B")
    AMBER  = colors.HexColor("#D98324")
    WHITE  = colors.white
    BLACK  = colors.HexColor("#1A2B3C")

    RISK_COLORS = {
        "CRITICAL": RED,
        "HIGH":     RED,
        "MEDIUM":   AMBER,
        "LOW":      GREEN,
    }

    doc_obj = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=15*mm, bottomMargin=20*mm,
    )
    W = A4[0] - 36*mm  # usable width

    styles = getSampleStyleSheet()
    H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18,
                         textColor=NAVY, spaceAfter=4)
    H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12,
                         textColor=NAVY, spaceBefore=12, spaceAfter=4)
    BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9,
                           textColor=BLACK, leading=13)
    SMALL = ParagraphStyle("small", fontName="Helvetica", fontSize=8,
                            textColor=MUTED, leading=11)
    MONO = ParagraphStyle("mono", fontName="Courier", fontSize=8,
                           textColor=BLACK, leading=11)
    LABEL = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=8,
                            textColor=MUTED, spaceAfter=1)

    story = []

    # ---- Header banner ----
    header_data = [[
        Paragraph("<font color='#073B5C'><b>SONARIS</b></font>", H1),
        Paragraph("<font color='#7A8FA6'>Marine Sonar Intelligence Platform</font>",
                  ParagraphStyle("rh", fontName="Helvetica", fontSize=9,
                                  textColor=MUTED, alignment=TA_RIGHT)),
    ]]
    header_tbl = Table(header_data, colWidths=[W*0.6, W*0.4])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0), (-1,-1), PANEL),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Survey Analysis Report", H1))
    story.append(HRFlowable(width=W, color=OCEAN, thickness=1.5, spaceAfter=4*mm))

    # ---- Survey Info ----
    story.append(Paragraph("Survey Information", H2))
    analysis_id = doc.get("analysis_id") or str(doc.get("_id", "N/A"))
    created_at  = doc.get("created_at", "N/A")
    filename    = doc.get("filename") or doc.get("original_filename", "N/A")
    total_det   = doc.get("total_detections", 0)

    info_rows = [
        ["Analysis ID",  analysis_id],
        ["Survey File",  filename],
        ["Date / Time",  created_at],
        ["Total Detections", str(total_det)],
    ]
    info_data = [[Paragraph(f"<b>{r[0]}</b>", BODY), Paragraph(str(r[1]), MONO)]
                 for r in info_rows]
    info_tbl = Table(info_data, colWidths=[W*0.3, W*0.7])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), PANEL),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [PANEL, WHITE]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D0E8F2")),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5*mm))

    # ---- Geolocation ----
    story.append(Paragraph("Geolocation", H2))
    detections = doc.get("detections") or []
    first_geo  = detections[0].get("geolocation") if detections else None

    if first_geo and first_geo.get("latitude") is not None:
        lat = first_geo["latitude"]
        lon = first_geo["longitude"]
        unc = first_geo.get("uncertainty_m", "N/A")
        geo_text = (f"WGS84 GNSS — Lat: {lat:.6f}°N  Lon: {lon:.6f}°E  "
                    f"Uncertainty: ±{unc} m")
        story.append(Paragraph(geo_text, BODY))
    else:
        story.append(Paragraph(
            "Geolocation unavailable / local_sonar — No WGS84 GPS coordinates were "
            "supplied in the survey metadata. Positions reported relative to the "
            "sonar swath acoustic frame of reference.", BODY))

    story.append(Spacer(1, 5*mm))

    # ---- Evidence image ----
    evidence_filename = doc.get("evidence_image")
    if evidence_filename:
        evidence_path = EVIDENCE_DIR / Path(evidence_filename).name
        if evidence_path.exists():
            story.append(Paragraph("DRISHTI Evidence Image", H2))
            max_w = W
            max_h = 80*mm
            try:
                rl_img = RLImage(str(evidence_path), width=max_w, height=max_h,
                                 kind="bound")
                story.append(rl_img)
                story.append(Spacer(1, 3*mm))
            except Exception as img_exc:
                logger.warning("Could not embed evidence image: %s", img_exc)

    # ---- Detection table ----
    story.append(Paragraph("Detection Summary", H2))

    if not detections:
        story.append(Paragraph("No anomalies detected above the confidence threshold.", BODY))
    else:
        col_widths = [8*mm, W*0.22, W*0.12, W*0.12, W*0.13, W*0.18, W*0.15]
        thead = [Paragraph(h, ParagraphStyle("th", fontName="Helvetica-Bold",
                                              fontSize=7.5, textColor=WHITE))
                 for h in ["#", "Target / Anomaly", "Confidence", "Risk Score",
                            "Priority", "Coord System", "Verification"]]
        det_rows = [thead]

        verif_map: Dict[int, str] = {}
        for v in (doc.get("verifications") or []):
            verif_map[v["detection_index"]] = v["decision"]

        for i, det in enumerate(detections):
            risk  = (det.get("risk_level") or "LOW").upper()
            verif = verif_map.get(i, "Pending")
            coord = (det.get("geolocation") or {}).get("coordinate_system", "local_sonar")
            conf  = f"{det['confidence']*100:.1f}%" if det.get("confidence") else "N/A"
            rscore = f"{det['risk_score']:.2f}" if det.get("risk_score") is not None else "N/A"
            det_rows.append([
                Paragraph(str(i+1), MONO),
                Paragraph(det.get("class_name", "Unknown").replace("_", " ").title(), BODY),
                Paragraph(conf, MONO),
                Paragraph(rscore, MONO),
                Paragraph(risk, ParagraphStyle("risk", fontName="Helvetica-Bold",
                                               fontSize=8,
                                               textColor=RISK_COLORS.get(risk, BLACK))),
                Paragraph(coord, SMALL),
                Paragraph(verif, BODY),
            ])

        det_tbl = Table(det_rows, colWidths=col_widths, repeatRows=1)
        det_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), NAVY),
            ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, PANEL]),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#D0E8F2")),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 5),
            ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ]))
        story.append(det_tbl)

    story.append(Spacer(1, 8*mm))

    # ---- Footer ----
    story.append(HRFlowable(width=W, color=OCEAN, thickness=0.8, spaceBefore=4*mm))
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    footer_data = [[
        Paragraph(f"Generated: {now_str}", SMALL),
        Paragraph("SONARIS Marine Intelligence — CONFIDENTIAL",
                  ParagraphStyle("fc", fontName="Helvetica-Oblique", fontSize=8,
                                  textColor=MUTED, alignment=TA_CENTER)),
        Paragraph(f"Survey ID: {analysis_id}", ParagraphStyle(
            "fr", fontName="Courier", fontSize=7, textColor=MUTED, alignment=TA_RIGHT)),
    ]]
    footer_tbl = Table(footer_data, colWidths=[W*0.33, W*0.34, W*0.33])
    footer_tbl.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(footer_tbl)

    doc_obj.build(story)
    return buf.getvalue()


@app.get("/api/surveys/{analysis_id}/report/pdf",
         summary="Download PDF report for one survey")
async def get_survey_report_pdf(analysis_id: str):
    """
    Generate and stream a professional PDF report for the specified survey.
    All values are sourced from the real MongoDB document — no fabricated data.
    """
    try:
        oid = ObjectId(analysis_id)
    except Exception:
        raise HTTPException(status_code=400,
                            detail=f"Invalid analysis_id: '{analysis_id}'")
    try:
        col  = get_analyses_collection()
        doc  = col.find_one({"_id": oid})
        if doc is None:
            raise HTTPException(status_code=404,
                                detail=f"Analysis '{analysis_id}' not found.")
        doc["_id"] = str(doc["_id"])
        doc["analysis_id"] = doc["_id"]
    except HTTPException:
        raise
    except MongoUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("PDF report fetch error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Fetch failed: {exc}")

    try:
        pdf_bytes = _build_pdf_report(doc)
    except Exception as exc:
        logger.exception("PDF generation error: %s", exc)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    filename = f"SONARIS_Report_{analysis_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Routes — analyze
# ---------------------------------------------------------------------------

@app.post("/api/analyze", summary="Analyse a sonar image")
async def analyze_sonar_image(
    file: UploadFile = File(..., description="Sonar image file (.jpg or .png)"),
    range_m: Optional[float] = Form(default=None),
    latitude: Optional[float] = Form(default=None),
    longitude: Optional[float] = Form(default=None),
    heading_deg: Optional[float] = Form(default=None),
    gps_accuracy_m: Optional[float] = Form(default=None),
) -> JSONResponse:
    """
    Run the full SONARIS pipeline on an uploaded sonar image.
    Persists result to MongoDB Atlas. Returns analysis_id and evidence_image.
    """
    allowed_suffixes = {".jpg", ".jpeg", ".png"}
    original_filename = file.filename or "upload.jpg"
    suffix = Path(original_filename).suffix.lower()
    if suffix not in allowed_suffixes:
        raise HTTPException(status_code=415,
                            detail=f"Unsupported format '{suffix}'. Accepted: {sorted(allowed_suffixes)}")

    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix,
                                         prefix="sonaris_upload_") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}")
    finally:
        await file.close()

    sonar_meta: Optional[Dict[str, Any]] = None
    if any(v is not None for v in (range_m, latitude, longitude, heading_deg, gps_accuracy_m)):
        sonar_meta = {}
        if range_m        is not None: sonar_meta["range_m"]        = range_m
        if latitude       is not None: sonar_meta["latitude"]       = latitude
        if longitude      is not None: sonar_meta["longitude"]      = longitude
        if heading_deg    is not None: sonar_meta["heading_deg"]    = heading_deg
        if gps_accuracy_m is not None: sonar_meta["gps_accuracy_m"] = gps_accuracy_m

    try:
        service = _get_service()
        result = service.analyze(
            image_path=tmp_path,
            original_filename=original_filename,
            sonar_metadata_dict=sonar_meta,
        )
    except Exception as exc:
        logger.exception("Pipeline error for '%s': %s", original_filename, exc)
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {exc}")
    finally:
        if tmp_path is not None:
            try: tmp_path.unlink(missing_ok=True)
            except Exception: pass

    try:
        analysis_id = insert_analysis(result)
        result["analysis_id"] = analysis_id
        logger.info("Analysis persisted. id=%s  file=%s  detections=%d",
                    analysis_id, original_filename, result["total_detections"])
    except MongoUnavailableError as exc:
        logger.error("MongoDB unavailable: %s", exc)
        raise HTTPException(status_code=503,
                            detail=f"Database unavailable: {exc}")
    except RuntimeError as exc:
        logger.error("MongoDB insert failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Database insert failed: {exc}")

    return JSONResponse(content=result)
