# SONARIS — Sonar Anomaly Recognition & Identification System

> **Smart India Hackathon 2025 Prototype**
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
3. **Tracks** the same anomaly across sequential sonar frames so each real-world object is counted exactly once.
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

**Demo numbers (smoke-tested):**

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
- Stored to MongoDB as a survey document

### Batch Analysis (up to 10 frames)
- Upload 2-10 sequential sonar frames in a single request
- Frames processed in exact upload order
- Per-frame detection results
- Cross-frame Persistent Anomaly Tracking via SonarTracker
- Batch stored to MongoDB batches collection
- Batch history and detail view in the UI

### Survey History & Statistics
- Paginated survey list with filters
- Aggregate statistics dashboard
- Batch history with persistent track summaries

---

## Architecture

```
Browser (React + Vite, port 5173)
   |
   | HTTP — /api proxied to :8000
   |
FastAPI Backend (port 8000)
   |
   |-- POST /api/analyze          (single frame)
   |-- POST /api/analyze/batch    (2-10 frames)
   |-- GET  /api/surveys          (history)
   |-- GET  /api/surveys/stats    (statistics)
   |-- GET  /api/batches          (batch history)
   |-- GET  /api/batches/{id}     (batch detail)
   |-- GET  /api/evidence/{file}  (annotated image)
   |
   Services:
     AnalysisService     — sonar preprocessing + YOLO inference
     BatchAnalysisService — orchestrates multi-frame workflow
     SonarTracker        — IoU-based persistent anomaly tracking
     ModelLoader         — lazy-loads best_detector.pt
   |
   pymongo
   |
MongoDB Atlas (collections: surveys | batches)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 5, Vanilla CSS |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| ML Inference | Ultralytics YOLOv8, OpenCV |
| Database | MongoDB Atlas (pymongo) |
| Evidence generation | OpenCV image annotation |
| Testing | pytest (backend) |
| Deployment | Render (backend), Vercel (frontend) |

---

## Project Structure

```
prototype/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + all route handlers
│   │   ├── database/                # MongoDB client & collection helpers
│   │   └── services/
│   │       ├── analysis_service.py  # Single-frame inference pipeline
│   │       ├── batch_service.py     # Batch orchestration
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
│   │   └── styles.css               # Full design system (dark marine theme)
│   ├── package.json
│   └── vite.config.js
├── ml/                              # ML experimentation notebooks / scripts
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

| Requirement | Version |
|------------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |
| MongoDB Atlas | Free tier cluster (M0) |

### 1. Clone the repository

```bash
git clone https://github.com/<your-org>/Marine-Debris-Detection.git
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

The backend auto-downloads `best_detector.pt` on first startup if `MODEL_DOWNLOAD_URL` is set.

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
| `MODEL_DOWNLOAD_URL` | Yes (cloud) | Direct URL to `best_detector.pt` |
| `ALLOWED_ORIGINS` | Optional | CORS origins (defaults to localhost) |
| `EVIDENCE_DIR` | Optional | Evidence image storage path |
| `PORT` | Optional | HTTP port (default: 8000) |
| `VITE_API_URL` | Optional | Backend URL for Vercel builds |

> Never commit your `.env` file. It is listed in `.gitignore`.

---

## API Reference

### Single Frame Analysis

```
POST /api/analyze
Content-Type: multipart/form-data

Body:  file: <sonar image>

Response:
{
  "survey_id": "...",
  "detections": [...],
  "risk_level": "HIGH",
  "risk_score": 0.78,
  "evidence_filename": "..._evidence_xxxx.jpg"
}
```

### Batch Analysis

```
POST /api/analyze/batch
Content-Type: multipart/form-data

Body:  files: <2-10 sonar images>  (order preserved)

Response:
{
  "batch_id": "...",
  "total_frames": 4,
  "total_raw_detections": 12,
  "persistent_tracks": 3,
  "merged_detections": 9,
  "frames": [...],
  "tracks": [...]
}
```

### Other Endpoints

```
GET /api/batches/{batch_id}   — Retrieve a stored batch result
GET /api/surveys?limit=20     — Survey history
GET /api/surveys/stats        — Aggregate statistics
GET /api/evidence/{filename}  — Annotated evidence image
```

---

## ML Model

- **Architecture:** YOLOv8 (Ultralytics)
- **Task:** Object detection on sonar imagery
- **Weights:** `best_detector.pt` — gitignored, auto-downloaded on startup
- **Sonar Preprocessing Pipeline:**
  1. Grayscale normalization
  2. CLAHE contrast enhancement
  3. Gaussian noise reduction
  4. Resize to model input size
  5. BGR conversion for Ultralytics compatibility

To inspect class names after downloading:

```bash
python -c "from ultralytics import YOLO; m=YOLO('models/best_detector.pt'); print(m.names)"
```

---

## Running Tests

```bash
# From project root, with venv activated
pytest backend/tests/ -v
```

Expected: **91 tests passing**

| File | Coverage |
|------|---------|
| `test_tracking_service.py` | SonarTracker — 33 unit tests |
| `test_batch_service.py` | Batch pipeline |
| `test_analyze_api.py` | Single-frame API integration |

---

## Deployment

### Backend (Render)

`render.yaml` at the repo root configures a Render Web Service automatically.

Set these in the Render dashboard:
- `MONGODB_URI`
- `MODEL_DOWNLOAD_URL`

### Frontend (Vercel)

```bash
cd frontend
npm run build
# Deploy dist/ to Vercel
# Set VITE_API_URL to your Render backend URL
```

---

## Security Notes

- No credentials in source code — all secrets via environment variables.
- `.env` is gitignored; use `.env.example` as reference.
- Model weights (`models/`) gitignored — never committed.
- Generated outputs (`outputs/`) gitignored.
- Test images (`test_data/`) gitignored.
- CORS restricted via `ALLOWED_ORIGINS`.
- No authentication implemented (prototype scope) — add API key middleware before production use.

---

*SONARIS — Built for ocean safety. Smart India Hackathon 2025.*
