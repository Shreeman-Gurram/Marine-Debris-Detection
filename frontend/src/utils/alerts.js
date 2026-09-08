// src/utils/alerts.js
// Centralized utility for extracting, normalizing, and sorting alerts across Dashboard, Alerts, and Map pages.

export const PRIORITY_WEIGHTS = {
  CRITICAL: 4,
  HIGH: 3,
  MEDIUM: 2,
  LOW: 1,
};

export function formatAnomalyName(raw) {
  if (!raw) return "Acoustic Target";
  return raw
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatAlertDate(dateStr) {
  if (!dateStr) return "Recent Survey";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

/**
 * Transforms MongoDB survey documents into a flattened, normalized list of alerts.
 * @param {Array} surveys - List of survey documents from GET /api/surveys
 * @returns {Array} - Flattened array of alerts sorted by priority and threat risk.
 */
export function extractAlertsFromSurveys(surveys = []) {
  if (!Array.isArray(surveys)) return [];

  const alerts = [];

  surveys.forEach((survey) => {
    const surveyId = survey._id || survey.analysis_id || "unknown";
    const surveyFilename = survey.filename || "upload.jpg";
    const timestamp = survey.created_at || null;
    const evidenceImage = survey.evidence_image || null;
    const detections = survey.detections || [];

    detections.forEach((det, idx) => {
      const geo = det.geolocation || {};
      const hasGps = geo.latitude != null && geo.longitude != null;
      const riskLevel = (det.risk_level || "LOW").toUpperCase();

      alerts.push({
        id: `${surveyId}-${idx}`,
        key: `${surveyId}-${idx}`,
        detectionIndex: idx,
        surveyId,
        surveyFilename,
        timestamp,
        evidenceImage,
        className: det.class_name || "Unknown Target",
        class_name: det.class_name || "Unknown Target",
        confidence: det.confidence != null ? Number(det.confidence) : null,
        riskScore: det.risk_score != null ? Number(det.risk_score) : null,
        risk_score: det.risk_score != null ? Number(det.risk_score) : null,
        riskLevel,
        risk_level: riskLevel,
        filterStatus: det.filter_status || "PASS",
        filter_status: det.filter_status || "PASS",
        filterReason: det.filter_reason || "",
        bbox: det.bbox || null,
        geolocation: geo,
        hasGps,
        latitude: geo.latitude != null ? Number(geo.latitude) : null,
        longitude: geo.longitude != null ? Number(geo.longitude) : null,
        uncertainty_m: geo.uncertainty_m != null ? Number(geo.uncertainty_m) : null,
        range_m: geo.range_m != null ? Number(geo.range_m) : null,
        bearing_deg: geo.bearing_deg != null ? Number(geo.bearing_deg) : null,
        local_x_m: geo.local_x_m != null ? Number(geo.local_x_m) : null,
        local_y_m: geo.local_y_m != null ? Number(geo.local_y_m) : null,
        coordinateSystem: geo.coordinate_system || (hasGps ? "WGS84" : "local_sonar"),
      });
    });
  });

  // Sort by priority descending (CRITICAL > HIGH > MEDIUM > LOW), then by risk score descending
  alerts.sort((a, b) => {
    const wa = PRIORITY_WEIGHTS[a.riskLevel] || 0;
    const wb = PRIORITY_WEIGHTS[b.riskLevel] || 0;
    if (wb !== wa) return wb - wa;

    const ra = a.riskScore || 0;
    const rb = b.riskScore || 0;
    if (rb !== ra) return rb - ra;

    const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    return tb - ta;
  });

  return alerts;
}
