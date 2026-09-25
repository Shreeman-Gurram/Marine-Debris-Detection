# SONARIS — Sonar Anomaly Recognition & Identification System

> **Smart India Hackathon 2026 Prototype**
> Team: Marine Debris Detection
> Problem Domain: Marine / Underwater Surveillance

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Solution Overview](#solution-overview)
- [Key USP — Persistent Anomaly Tracking](#key-usp--persistent-anomaly-tracking)
- [Feature Set](#feature-set)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start — Local Development](#quick-start--local-development)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [ML Model](#ml-model)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Security Notes](#security-notes)

---

## Problem Statement

Marine debris and submerged anomalies (shipwrecks, nets, unexploded ordnance, plastic accumulations) pose a severe threat to navigation safety, marine ecosystems, and coastal infrastructure. Traditional sonar surveys produce vast quantities of sequential frames that operators must review manually — a slow, error-prone process that frequently leads to the same object being logged multiple times across frames.

**SONARIS** addresses this with AI-powered detection combined with cross-frame object persistence tracking.

---

## Solution Overview

SONARIS is a full-stack web application that:

1. **Ingests** individual or batches of sonar image frames.
2. **Detects** underwater anomalies using a custom-trained YOLOv8 model.
3. **Tracks** the same anomaly across sequential sonar frames so repeated detections of the same tracked anomaly can be consolidated into a single persistent track.
4. **Reports** risk-scored results with annotated evidence images, persistent track summaries, and exportable survey history.

---

## Key USP — Persistent Anomaly Tracking

> *"SONARIS identifies the same underwater object across multiple consecutive sonar frames and avoids counting repeated detections as separate anomalies."*

| Stage | Detail |
|-------|--------|
| Frame-by-frame detection | YOLOv8 runs on every uploaded sonar frame independently |
| IoU-based association | Each new detection is matched against active tracks using Intersection-over-Union (threshold: 0.35) |
| Track lifetime management | A track survives up to 2 missed frames before being closed (MAX_AGE = 2) |
| Class-gated matching | Tracks only match detections of the same class |
| Deduplication | Multiple detections of the same object across N frames = 1 persistent anomaly |

**Validation result (smoke-test on real sonar images — not a general performance metric):**

```
Frames processed  : 4
Raw YOLO hits     : 12
Persistent tracks : 3
Merged detections : 9
```

---

## Feature Set

### Single Image Analysis
- Upload one sonar frame for instant YOLO inference
- Confidence-filtered detections with class labels
- Risk score (LOW / MEDIUM / HIGH / CRITICAL)
- Annotated evidence image generated server-side
- Stored to MongoDB as a document in the `analyses` collection
- PDF report download per survey

### Batch Analysis (up to 10 frames)
- Upload 1-10 sequential sonar frames in a single request
- Frames processed in exact upload order
- Per-frame detection results
- Cross-frame Persistent Anomaly Tracking via SonarTracker
- Batch stored to MongoDB `batches` collection
- Batch history and detail view in the UI

### Survey History & Statistics
- Paginated survey list
- Aggregate statistics dashboard
- Batch history with persistent track summaries
- Operator verification workflow (Confirmed / Rejected / Uncertain)

---

## Architecture

```
Browser (React 18 + Vite 6, port 5173)
   |
   | HTTP — /api proxied to :8000
   |
FastAPI Backend (port 8000)
   |
   |-- GET  /api/health                           (liveness probe)
   |-- POST /api/analyze                          (single frame)
   |-- POST /api/analyze/batch                    (1-10 frames)
   |-- GET  /api/evidence/{filename}              (annotated image)
   |-- GET  /api/surveys                          (history list)
   |-- GET  /api/surveys/stats                    (statistics)
   |-- GET  /api/surveys/{id}                     (single survey)
   |-- PUT  /api/surveys/{id}/verifications       (operator review)
   |-- GET  /api/surveys/{id}/report/pdf          (PDF download)
   |-- GET  /api/batches                          (batch history)
   |-- GET  /api/batches/{id}                     (batch detail)
   |
   Services:
     AnalysisService      — sonar preprocessing + YOLO inference
     BatchAnalysisService — orchestrates multi-frame workflow
     SonarTracker         — IoU-based persistent anomaly tracking
     ModelLoader          — lazy-loads / auto-downloads best_detector.pt
   |
   pymongo
   |
MongoDB Atlas
  Database:    sonaris
  Collections: analyses | batches
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 6, Vanilla CSS (light marine/ocean theme) |
| Frontend extras | react-router-dom, react-leaflet, recharts, lucide-react |
| Backend | Python 3.11, FastAPI, Uvicorn |
| ML Inference | Ultralytics YOLOv8, OpenCV |
| Database | MongoDB Atlas (pymongo) |
| Evidence generation | OpenCV image annotation |
| PDF reports | ReportLab |
| Testing | pytest (backend) |
| Deployment | Render (backend), Vercel (frontend) |

---

## Project Structure

```
prototype/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + all route handlers
│   │   ├── database/
│   │   │   └── mongodb.py           # MongoDB client, collections: analyses + batches
│   │   └── services/
│   │       ├── analysis_service.py  # Single-frame inference pipeline
│   │       ├── batch_service.py     # Batch orchestration (max 10 frames)
│   │       ├── tracking_service.py  # SonarTracker (persistent anomaly tracking)
│   │       └── model_loader.py      # YOLO model download & cache
│   ├── tests/
│   │   ├── test_tracking_service.py # 33 unit tests for SonarTracker
│   │   └── test_batch_service.py    # Batch pipeline tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── NewSurvey.jsx        # Single + batch upload modes
│   │   │   └── SurveyHistory.jsx    # History + batch history
│   │   ├── components/
│   │   │   ├── BatchUpload.jsx
│   │   │   └── BatchResult.jsx
│   │   ├── services/api.js          # Axios wrappers for all endpoints
│   │   └── styles.css               # Design system — light marine/ocean palette
│   ├── package.json
│   └── vite.config.js
├── ml/
│   ├── preprocessing/               # NLM denoise, CLAHE normalize, unsharp enhance
│   ├── detection/
│   ├── filtering/
│   ├── scoring/
│   └── geolocation/
├── models/                          # Model weights directory (gitignored)
├── test_data/                       # Sample sonar images (gitignored)
├── outputs/                         # Generated evidence images (gitignored)
├── render.yaml                      # Render deployment configuration
├── requirements.txt                 # Root-level pip requirements
├── .env.example                     # Template — copy to .env for local dev
└── .gitignore
```

---

## Quick Start — Local Development

### Prerequisites

| Requirement | Minimum Version |
|------------|-----------------|
| Python | 3.11 |
| Node.js | 18 |
| npm | 9 |
| MongoDB Atlas | Free tier cluster (M0) |

### 1. Clone the repository

```bash
git clone https://github.com/Shreeman-Gurram/Marine-Debris-Detection.git
cd Marine-Debris-Detection/prototype
```

### 2. Configure environment

```bash
cp .env.example .env
# Open .env and fill in:
#   MONGODB_URI        — your Atlas connection string
#   MODEL_DOWNLOAD_URL — direct URL to best_detector.pt
```

### 3. Backend setup

```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend auto-downloads `best_detector.pt` on first startup if `MODEL_DOWNLOAD_URL` (or `YOLO_MODEL_URL`) is set.

### 4. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

---

## Environment Variables

See `.env.example` for the full reference.

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | Yes | MongoDB Atlas connection string |
| `MODEL_DOWNLOAD_URL` | Yes (cloud) | Direct download URL to `best_detector.pt`. Alias `YOLO_MODEL_URL` also accepted. |
| `ALLOWED_ORIGINS` | Optional | Comma-separated CORS origins (defaults to localhost). Use `*` to allow all. |
| `EVIDENCE_DIR` | Optional | Evidence image storage path (defaults to `outputs/evidence/`) |
| `PORT` | Optional | HTTP port — provided automatically by Render via `$PORT` |
| `VITE_API_URL` | Optional | Backend URL for Vercel production builds |

> Never commit your `.env` file. It is listed in `.gitignore`.

---

## API Reference

All endpoints are prefixed with `/api`.

### Health

```
GET /api/health
Response: { "status": "ok", "service": "sonaris-backend", "model_available": true }
```

### Single Frame Analysis

```
POST /api/analyze
Content-Type: multipart/form-data

Form fields:
  file           (required) — sonar image .jpg/.jpeg/.png
  range_m        (optional) — sonar slant range in metres
  latitude       (optional) — WGS84 latitude
  longitude      (optional) — WGS84 longitude
  heading_deg    (optional) — vessel heading
  gps_accuracy_m (optional) — GPS accuracy in metres

Response:
{
  "analysis_id": "...",
  "detections": [...],
  "total_detections": 3,
  "risk_level": "HIGH",
  "risk_score": 0.78,
  "evidence_image": "..._evidence_xxxx.jpg"
}
```

### Batch Analysis

```
POST /api/analyze/batch
Content-Type: multipart/form-data

Form fields:
  files           (required) — 1 to 10 sonar image files (order preserved)
  slant_range_m   (optional)
  heading_deg     (optional)
  latitude        (optional)
  longitude       (optional)
  gps_accuracy_m  (optional)

Response:
{
  "batch_id": "...",
  "batch_db_id": "...",
  "total_frames": 4,
  "total_raw_detections": 12,
  "total_persistent_tracks": 3,
  "duplicates_merged": 9,
  "frames": [...],
  "tracks": [...]
}
```

### Survey History

```
GET /api/surveys?limit=20          — list recent analyses (analyses collection)
GET /api/surveys/stats             — aggregate statistics
GET /api/surveys/{id}              — single survey document
PUT /api/surveys/{id}/verifications — persist operator review decisions
GET /api/surveys/{id}/report/pdf   — download PDF report
```

### Batch History

```
GET /api/batches?limit=20          — list recent batches (batches collection)
GET /api/batches/{id}              — single batch document (by MongoDB ObjectId)
```

### Evidence Image

```
GET /api/evidence/{filename}       — serve annotated evidence image (JPEG)
```

---

## ML Model

- **Architecture:** YOLOv8 (Ultralytics)
- **Task:** Object detection on side-scan sonar (SSS) imagery
- **Weights file:** `best_detector.pt` — **not committed to Git** (gitignored, auto-downloaded at runtime)
- **Retrieval:** Set `MODEL_DOWNLOAD_URL` (or `YOLO_MODEL_URL`) in `.env`; the backend downloads weights on first startup.

### Detected Classes

| Class ID | Class Name |
|----------|-----------|
| 0 | crab_pot |
| 1 | submarine_pipeline |
| 2 | shipwreck |
| 3 | ghost_net |
| 4 | mine_cylinder |

### Sonar Preprocessing Pipeline

Each sonar image passes through the following steps before YOLO inference
(`ml/preprocessing/`):

1. **Load as grayscale** — file or numpy array input; convert BGR to grayscale
2. **NLM Denoising** — Non-Local Means (`cv2.fastNlMeansDenoising`) reduces sonar speckle while preserving target edges
3. **CLAHE Normalization** — Contrast Limited Adaptive Histogram Equalization enhances local contrast
4. **Unsharp Masking Enhancement** — sharpens fine sonar features after CLAHE
5. **Float32 scaling** — output normalized to `[0.0, 1.0]`
6. **BGR conversion** — for Ultralytics YOLO compatibility

---

## Running Tests

```bash
# From project root, with venv activated
pytest backend/tests/ -v
```

Expected: **91 tests passing**

| File | Coverage |
|------|---------|
| `test_tracking_service.py` | SonarTracker — 33 unit tests (IoU matching, track lifecycle, edge cases) |
| `test_batch_service.py` | Batch pipeline with mock detections |
| `test_analyze_api.py` | Single-frame API integration |

---

## Deployment

### Backend (Render)

`render.yaml` at the repo root configures a Render Web Service automatically.
Python version is pinned to **3.11.9** in `render.yaml`.

Set these in the Render dashboard:
- `MONGODB_URI`
- `MODEL_DOWNLOAD_URL`
- `ALLOWED_ORIGINS` (your Vercel frontend URL)

### Frontend (Vercel)

```bash
cd frontend
npm run build
# Deploy the generated dist/ folder to Vercel
# Set VITE_API_URL to your Render backend URL in Vercel environment variables
```

---

## Security Notes

- No credentials in source code — all secrets via environment variables.
- `.env` is gitignored; use `.env.example` as reference.
- Model weights (`models/`) gitignored — never committed.
- Generated outputs (`outputs/`) gitignored.
- Test images (`test_data/`) gitignored.
- CORS restricted via `ALLOWED_ORIGINS`; defaults to localhost only.
- Evidence image endpoint uses safe path handling to reject path traversal.
- No authentication implemented (prototype scope) — add API key middleware before production use.

---

*SONARIS — Built for ocean safety. Smart India Hackathon 2026.*
