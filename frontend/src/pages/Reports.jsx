// src/pages/Reports.jsx
import { useEffect, useState } from "react";
import { Download, FileText, FileSpreadsheet, FileJson, Plus, FileSearch } from "lucide-react";
import { Link } from "react-router-dom";
import SectionHeader from "../components/SectionHeader";
import Badge from "../components/Badge";
import { getRecentSurveys, reportPdfUrl } from "../services/api";

export default function Reports() {
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getRecentSurveys(10)
      .then((data) => {
        if (mounted) setSurveys(data);
      })
      .catch((err) => console.error("Error fetching reports:", err))
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  function downloadJson(survey) {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(survey, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `${survey.filename || "survey"}_report.json`);
    dlAnchor.click();
  }

  function downloadCsv(survey) {
    const rows = [
      ["Class", "Confidence", "Risk Score", "Priority", "Range (m)", "Bearing (deg)", "Latitude", "Longitude", "Verification"],
    ];
    const verifMap = {};
    for (const v of (survey.verifications || [])) {
      verifMap[v.detection_index] = v.decision;
    }
    (survey.detections || []).forEach((det, idx) => {
      rows.push([
        det.class_name || "unknown",
        det.confidence != null ? det.confidence.toFixed(4) : "",
        det.risk_score != null ? det.risk_score.toFixed(4) : "",
        det.risk_level || "LOW",
        det.geolocation?.range_m != null ? det.geolocation.range_m.toFixed(2) : "",
        det.geolocation?.bearing_deg != null ? det.geolocation.bearing_deg.toFixed(1) : "",
        det.geolocation?.latitude != null ? det.geolocation.latitude.toFixed(6) : "",
        det.geolocation?.longitude != null ? det.geolocation.longitude.toFixed(6) : "",
        verifMap[idx] || "Pending",
      ]);
    });
    const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.join(",")).join("\n");
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", encodeURI(csvContent));
    dlAnchor.setAttribute("download", `${survey.filename || "survey"}_detections.csv`);
    dlAnchor.click();
  }

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">INTELLIGENCE EXPORT</span>
          <h1>Survey Reports</h1>
          <p>Export and download validated survey findings in JSON, CSV, and PDF formats</p>
        </div>
        <Link to="/surveys/new" className="primary-btn">
          <Plus size={18} /> New survey
        </Link>
      </div>

      <section className="panel">
        <SectionHeader
          title="Available Survey Reports"
          subtitle="Reports generated from processed MongoDB intelligence missions"
        />

        {loading ? (
          <p style={{ color: "var(--muted)", padding: "20px" }}>Loading available reports...</p>
        ) : surveys.length === 0 ? (
          <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--muted)" }}>
            <FileSearch size={34} style={{ margin: "0 auto 10px auto" }} />
            <h4>No reports available</h4>
            <p style={{ fontSize: "13px", marginTop: "4px" }}>
              Upload and analyze sonar imagery to generate automated mission reports.
            </p>
          </div>
        ) : (
          <div className="report-list">
            {surveys.map((survey) => (
              <div key={survey._id} style={{ display: "grid", gap: "10px", marginBottom: "14px" }}>
                {/* JSON Row */}
                <div className="report-row">
                  <div className="report-icon">
                    <FileJson size={22} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <strong>{survey.filename} — Raw JSON Intelligence</strong>
                    <p>
                      {survey.detections?.length || 0} detections · ID: {survey._id}
                    </p>
                  </div>
                  <Badge tone="success">JSON</Badge>
                  <button
                    type="button"
                    className="secondary-btn small"
                    onClick={() => downloadJson(survey)}
                  >
                    <Download size={16} /> Export JSON
                  </button>
                </div>

                {/* CSV Row */}
                <div className="report-row">
                  <div className="report-icon">
                    <FileSpreadsheet size={22} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <strong>{survey.filename} — Detection Table CSV</strong>
                    <p>Tabular export of detections, coordinates, risk scores and verifications</p>
                  </div>
                  <Badge tone="neutral">CSV</Badge>
                  <button
                    type="button"
                    className="secondary-btn small"
                    onClick={() => downloadCsv(survey)}
                  >
                    <Download size={16} /> Export CSV
                  </button>
                </div>

                {/* PDF Row */}
                <div className="report-row">
                  <div className="report-icon">
                    <FileText size={22} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <strong>{survey.filename} — Professional PDF Report</strong>
                    <p>Full A4 report with evidence image, detection table, geolocation and verification status</p>
                  </div>
                  <Badge tone="warning">PDF</Badge>
                  <a
                    href={reportPdfUrl(survey._id)}
                    target="_blank"
                    rel="noreferrer"
                    className="secondary-btn small"
                    style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                    title="Download PDF Report"
                  >
                    <Download size={16} /> Download PDF
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
