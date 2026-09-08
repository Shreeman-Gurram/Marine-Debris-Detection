// src/services/api.js
// Real SONARIS API integration — no mock data.
// In development: defaults to relative /api (proxied by Vite to http://localhost:8000)
// In production: configured via VITE_API_URL environment variable (e.g. https://sonaris-api.onrender.com)

const _RAW_API_URL = (import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");
const BASE = _RAW_API_URL ? `${_RAW_API_URL}/api` : "/api";

// ---------------------------------------------------------------------------
// Analyze
// ---------------------------------------------------------------------------

/**
 * Upload a sonar image and run the full SONARIS pipeline.
 * @param {File} file - The sonar image file selected by the operator.
 * @param {Object} [meta] - Optional sonar metadata { range_m, latitude, longitude, heading_deg }
 * @returns {Promise<Object>} - API response with detections, evidence_image, analysis_id
 */
export async function analyzeSonar(file, meta = {}) {
  const form = new FormData();
  form.append("file", file);
  if (meta.range_m != null)     form.append("range_m",        meta.range_m);
  if (meta.latitude != null)    form.append("latitude",       meta.latitude);
  if (meta.longitude != null)   form.append("longitude",      meta.longitude);
  if (meta.heading_deg != null) form.append("heading_deg",    meta.heading_deg);

  const res = await fetch(`${BASE}/analyze`, { method: "POST", body: form });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Dashboard stats — derived from MongoDB analyses collection
// ---------------------------------------------------------------------------

/**
 * Fetch dashboard summary stats from MongoDB-backed history.
 * Returns zeroes (not fake data) when no analyses exist.
 */
export async function getDashboardStats() {
  const res = await fetch(`${BASE}/surveys/stats`);
  if (!res.ok) throw new Error(`Stats fetch failed: HTTP ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Survey history
// ---------------------------------------------------------------------------

/**
 * Fetch the N most recent analyses from MongoDB.
 */
export async function getRecentSurveys(limit = 10) {
  const res = await fetch(`${BASE}/surveys?limit=${limit}`);
  if (!res.ok) throw new Error(`Surveys fetch failed: HTTP ${res.status}`);
  return res.json();
}

/**
 * Fetch a single analysis document by its MongoDB ObjectId string.
 */
export async function getSurveyById(id) {
  const res = await fetch(`${BASE}/surveys/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Survey fetch failed: HTTP ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Evidence images
// ---------------------------------------------------------------------------

/** Returns the full URL for a named evidence image. */
export function evidenceUrl(filename) {
  if (!filename) return null;
  return `${BASE}/evidence/${encodeURIComponent(filename)}`;
}

// ---------------------------------------------------------------------------
// Operator verifications — persistent
// ---------------------------------------------------------------------------

/**
 * Persist operator verification decisions for a survey.
 * Sends a list of { detection_index, decision, operator?, notes?, timestamp? }
 * to PUT /api/surveys/{analysis_id}/verifications.
 *
 * @param {string} analysisId   - MongoDB ObjectId string
 * @param {Array}  verifications - Array of verification objects
 * @returns {Promise<Object>}   - { status, analysis_id, verifications_stored }
 */
export async function saveVerifications(analysisId, verifications) {
  const res = await fetch(`${BASE}/surveys/${analysisId}/verifications`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ verifications }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// PDF report
// ---------------------------------------------------------------------------

/**
 * Returns the direct URL to download the PDF report for a survey.
 * The browser will trigger a file download when navigated to this URL.
 */
export function reportPdfUrl(analysisId) {
  return `${BASE}/surveys/${analysisId}/report/pdf`;
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
export async function healthCheck() {
  const res = await fetch(`${BASE}/health`);
  return res.ok;
}
