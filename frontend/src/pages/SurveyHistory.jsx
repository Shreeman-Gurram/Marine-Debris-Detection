// src/pages/SurveyHistory.jsx
// Comprehensive Survey History for SONARIS Marine Intelligence Platform
import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Compass,
  FileCheck,
  FileImage,
  FileSearch,
  Filter,
  History,
  Layers,
  MapPin,
  Plus,
  RefreshCw,
  ScanLine,
  ShieldAlert,
} from "lucide-react";
import { Download } from "lucide-react";
import SectionHeader from "../components/SectionHeader";
import Badge from "../components/Badge";
import { getRecentSurveys, evidenceUrl, reportPdfUrl } from "../services/api";
import { formatAnomalyName, formatAlertDate } from "../utils/alerts";
import { RISK_TONE } from "../utils/constants";

const ITEMS_PER_PAGE = 10;

export default function SurveyHistory() {
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterMode, setFilterMode] = useState("ALL"); // "ALL" | "WITH_DETECTIONS" | "NO_DETECTIONS" | "GPS" | "LOCAL"
  const [currentPage, setCurrentPage] = useState(1);

  async function loadHistory() {
    try {
      setLoading(true);
      const data = await getRecentSurveys(100);
      setSurveys(data || []);
      setError(null);
    } catch (err) {
      console.error("Failed to load survey history:", err);
      setError(err.message || "Failed to retrieve survey history from database.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  // Summary Metrics computed from actual surveys
  const summary = useMemo(() => {
    const total = surveys.length;
    let withAnomalies = 0;
    let clean = 0;
    let totalAnomalies = 0;

    surveys.forEach((s) => {
      const count = s.detections?.length || s.total_detections || 0;
      if (count > 0) {
        withAnomalies++;
        totalAnomalies += count;
      } else {
        clean++;
      }
    });

    return {
      total,
      withAnomalies,
      clean,
      totalAnomalies,
    };
  }, [surveys]);

  // Client-side filtering & search
  const filteredSurveys = useMemo(() => {
    return surveys.filter((survey) => {
      const detections = survey.detections || [];
      const hasDetections = detections.length > 0;
      const hasGps = detections.some(
        (d) => d.geolocation?.latitude != null && d.geolocation?.longitude != null
      );

      // Filter Mode
      if (filterMode === "WITH_DETECTIONS" && !hasDetections) return false;
      if (filterMode === "NO_DETECTIONS" && hasDetections) return false;
      if (filterMode === "GPS" && !hasGps) return false;
      if (filterMode === "LOCAL" && hasGps) return false;

      // Text Search
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const filename = (survey.filename || "").toLowerCase();
        const id = (survey._id || "").toLowerCase();
        if (!filename.includes(query) && !id.includes(query)) return false;
      }

      return true;
    });
  }, [surveys, filterMode, searchQuery]);

  // Pagination calculation
  const totalPages = Math.ceil(filteredSurveys.length / ITEMS_PER_PAGE) || 1;
  const paginatedSurveys = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredSurveys.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredSurveys, currentPage]);

  function handleFilterChange(mode) {
    setFilterMode(mode);
    setCurrentPage(1);
  }

  function handleSearchChange(e) {
    setSearchQuery(e.target.value);
    setCurrentPage(1);
  }

  return (
    <div>
      {/* Top Header */}
      <div className="page-heading">
        <div>
          <span className="eyebrow">MISSION AUDIT LOG</span>
          <h1>SURVEY HISTORY</h1>
          <p>Review previous sonar surveys and detection results</p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            className="secondary-btn"
            onClick={loadHistory}
            disabled={loading}
            style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh History
          </button>
          <Link to="/surveys/new" className="primary-btn">
            <Plus size={16} /> New Survey
          </Link>
        </div>
      </div>

      {error && (
        <div
          style={{
            marginBottom: "20px",
            padding: "14px 18px",
            borderRadius: "10px",
            background: "rgba(243, 109, 122, 0.12)",
            border: "1px solid rgba(243, 109, 122, 0.3)",
            color: "#ff8b97",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <AlertTriangle size={18} />
          <span>Database connection notice: {error}</span>
        </div>
      )}

      {/* SUMMARY KPI STRIP */}
      <div className="kpi-summary-grid" style={{ marginBottom: "20px" }}>
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Total Surveys</span>
            <History size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">
            {summary.total}
            <span style={{ fontSize: "12px", color: "var(--muted)", fontWeight: 400 }}>missions</span>
          </div>
          <div className="kpi-sub">Archived survey frames</div>
        </div>

        <div className="kpi-card" style={{ borderColor: summary.withAnomalies > 0 ? "rgba(217, 131, 36, 0.4)" : "" }}>
          <div className="kpi-label">
            <span>Flagged Surveys</span>
            <ShieldAlert size={15} color="var(--amber)" />
          </div>
          <div className="kpi-value" style={{ color: summary.withAnomalies > 0 ? "var(--amber)" : "var(--text)" }}>
            {summary.withAnomalies}
          </div>
          <div className="kpi-sub">Surveys with detected contacts</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Clean Surveys</span>
            <CheckCircle2 size={15} color="var(--green)" />
          </div>
          <div className="kpi-value" style={{ color: "var(--green)" }}>
            {summary.clean}
          </div>
          <div className="kpi-sub">Clear sonar swath passes</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Total Anomalies</span>
            <Layers size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">
            {summary.totalAnomalies}
          </div>
          <div className="kpi-sub">Target contacts cataloged</div>
        </div>
      </div>

      {/* FILTER & SEARCH BAR */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          background: "var(--panel)",
          border: "1px solid var(--line)",
          borderRadius: "12px",
          padding: "10px 14px",
          marginBottom: "20px",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <div className="view-mode-pill" style={{ flexWrap: "wrap" }}>
          <button
            type="button"
            className={filterMode === "ALL" ? "active" : ""}
            onClick={() => handleFilterChange("ALL")}
          >
            All ({summary.total})
          </button>
          <button
            type="button"
            className={filterMode === "WITH_DETECTIONS" ? "active" : ""}
            onClick={() => handleFilterChange("WITH_DETECTIONS")}
          >
            With Detections ({summary.withAnomalies})
          </button>
          <button
            type="button"
            className={filterMode === "NO_DETECTIONS" ? "active" : ""}
            onClick={() => handleFilterChange("NO_DETECTIONS")}
          >
            No Detections ({summary.clean})
          </button>
          <button
            type="button"
            className={filterMode === "GPS" ? "active" : ""}
            onClick={() => handleFilterChange("GPS")}
          >
            GPS Available
          </button>
          <button
            type="button"
            className={filterMode === "LOCAL" ? "active" : ""}
            onClick={() => handleFilterChange("LOCAL")}
          >
            Local Sonar
          </button>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <input
            type="text"
            placeholder="Search survey by filename..."
            value={searchQuery}
            onChange={handleSearchChange}
            style={{
              background: "var(--panel-alt)",
              border: "1px solid var(--line)",
              borderRadius: "6px",
              padding: "6px 12px",
              color: "var(--text)",
              fontSize: "12px",
              minWidth: "240px",
            }}
          />
        </div>
      </div>

      {/* CONTENT LISTING */}
      {loading ? (
        <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--muted)" }}>
          <ScanLine size={36} color="var(--primary)" style={{ animation: "spin 2s linear infinite", marginBottom: "12px" }} />
          <p>Retrieving survey mission archives from MongoDB...</p>
        </div>
      ) : surveys.length === 0 ? (
        /* PROFESSIONAL EMPTY STATE */
        <div className="clean-scan-card" style={{ margin: "20px 0" }}>
          <FileSearch size={48} color="var(--primary)" style={{ margin: "0 auto 12px auto", opacity: 0.8 }} />
          <h3 style={{ color: "var(--text)", marginBottom: "6px" }}>No Survey Records</h3>
          <p style={{ fontSize: "13px", color: "var(--muted)", maxWidth: "440px", margin: "0 auto" }}>
            Upload a sonar survey to begin automated DRISHTI anomaly detection and threat assessment.
          </p>
          <div style={{ marginTop: "18px" }}>
            <Link to="/surveys/new" className="primary-btn">
              <Plus size={16} /> Upload First Survey
            </Link>
          </div>
        </div>
      ) : filteredSurveys.length === 0 ? (
        <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--muted)", background: "var(--panel)", borderRadius: "10px", border: "1px solid var(--line)" }}>
          <Filter size={32} style={{ opacity: 0.5, marginBottom: "8px" }} />
          <p>No survey records matching &ldquo;{searchQuery}&rdquo;.</p>
        </div>
      ) : (
        /* SURVEY HISTORY TABLE */
        <section className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "12px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--line)", color: "var(--muted)", background: "var(--panel-alt)" }}>
                  <th style={{ padding: "12px 14px" }}>SURVEY FILENAME</th>
                  <th style={{ padding: "12px 14px" }}>TIMESTAMP</th>
                  <th style={{ padding: "12px 14px" }}>DETECTIONS</th>
                  <th style={{ padding: "12px 14px" }}>PEAK PRIORITY</th>
                  <th style={{ padding: "12px 14px" }}>PEAK RISK</th>
                  <th style={{ padding: "12px 14px" }}>AVG CONFIDENCE</th>
                  <th style={{ padding: "12px 14px" }}>LOCATION STATUS</th>
                  <th style={{ padding: "12px 14px" }}>EVIDENCE</th>
                  <th style={{ padding: "12px 14px", textAlign: "right" }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {paginatedSurveys.map((survey) => {
                  const detections = survey.detections || [];
                  const detCount = detections.length;
                  const hasGps = detections.some(
                    (d) => d.geolocation?.latitude != null && d.geolocation?.longitude != null
                  );

                  // Calculate highest priority
                  const priorities = detections.map((d) => (d.risk_level || "LOW").toUpperCase());
                  let highestPri = "CLEAN";
                  if (detCount > 0) {
                    if (priorities.includes("CRITICAL")) highestPri = "CRITICAL";
                    else if (priorities.includes("HIGH")) highestPri = "HIGH";
                    else if (priorities.includes("MEDIUM")) highestPri = "MEDIUM";
                    else highestPri = "LOW";
                  }

                  // Calculate peak risk & avg confidence
                  const maxRisk = detCount > 0 ? Math.max(...detections.map((d) => d.risk_score || 0)) : 0;
                  const avgConf =
                    detCount > 0
                      ? detections.reduce((acc, d) => acc + (d.confidence || 0), 0) / detCount
                      : null;

                  return (
                    <tr
                      key={survey._id}
                      style={{
                        borderBottom: "1px solid var(--line)",
                        transition: "background 0.15s ease",
                      }}
                    >
                      {/* Survey Filename & Archive ID */}
                      <td style={{ padding: "14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <FileImage size={18} color="var(--primary)" style={{ flexShrink: 0 }} />
                          <div>
                            <strong style={{ color: "var(--text)", display: "block", fontSize: "13px" }}>
                              {survey.filename || "sonar_scan.jpg"}
                            </strong>
                            <code style={{ fontSize: "10px", color: "var(--muted)" }}>
                              {survey._id}
                            </code>
                          </div>
                        </div>
                      </td>

                      {/* Timestamp */}
                      <td style={{ padding: "14px", color: "var(--muted)" }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                          <Clock size={13} /> {formatAlertDate(survey.created_at)}
                        </span>
                      </td>

                      {/* Total Detections */}
                      <td style={{ padding: "14px" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            fontWeight: 600,
                            color: detCount > 0 ? "var(--text)" : "var(--green)",
                          }}
                        >
                          <span
                            style={{
                              width: "20px",
                              height: "20px",
                              borderRadius: "50%",
                              background: detCount > 0 ? "var(--panel-alt)" : "rgba(16, 185, 129, 0.15)",
                              display: "grid",
                              placeItems: "center",
                              fontSize: "11px",
                              color: detCount > 0 ? "var(--primary)" : "var(--green)",
                            }}
                          >
                            {detCount}
                          </span>
                          {detCount === 1 ? "contact" : "contacts"}
                        </span>
                      </td>

                      {/* Peak Priority */}
                      <td style={{ padding: "14px" }}>
                        <Badge tone={RISK_TONE[highestPri] || (detCount === 0 ? "success" : "neutral")}>
                          {highestPri}
                        </Badge>
                      </td>

                      {/* Highest Risk Score */}
                      <td style={{ padding: "14px", fontFamily: "monospace" }}>
                        <strong style={{ color: maxRisk >= 0.7 ? "var(--red)" : maxRisk >= 0.4 ? "var(--amber)" : "var(--text)" }}>
                          {detCount > 0 ? maxRisk.toFixed(2) : "0.00"}
                        </strong>
                      </td>

                      {/* Average Confidence */}
                      <td style={{ padding: "14px" }}>
                        {avgConf != null ? (
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span>{(avgConf * 100).toFixed(1)}%</span>
                            <div
                              style={{
                                width: "35px",
                                height: "4px",
                                background: "var(--line)",
                                borderRadius: "2px",
                                overflow: "hidden",
                              }}
                            >
                              <div
                                style={{
                                  width: `${Math.round(avgConf * 100)}%`,
                                  height: "100%",
                                  background: "var(--primary)",
                                }}
                              />
                            </div>
                          </div>
                        ) : (
                          <span style={{ color: "var(--muted)" }}>N/A</span>
                        )}
                      </td>

                      {/* Location Status */}
                      <td style={{ padding: "14px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            color: hasGps ? "var(--green)" : "var(--amber)",
                          }}
                        >
                          {hasGps ? (
                            <>
                              <MapPin size={13} /> WGS84 GNSS
                            </>
                          ) : (
                            <>
                              <Compass size={13} /> Local Sonar
                            </>
                          )}
                        </span>
                      </td>

                      {/* Evidence Availability */}
                      <td style={{ padding: "14px" }}>
                        {survey.evidence_image ? (
                          <span
                            style={{
                              fontSize: "11px",
                              color: "var(--green)",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                            }}
                          >
                            <FileCheck size={14} /> Available
                          </span>
                        ) : (
                          <span style={{ fontSize: "11px", color: "var(--muted)" }}>None</span>
                        )}
                      </td>

                      {/* View Analysis + PDF CTA */}
                      <td style={{ padding: "14px", textAlign: "right" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", justifyContent: "flex-end", flexWrap: "wrap" }}>
                          <Link
                            to={`/analysis/${survey._id}`}
                            className="primary-btn"
                            style={{
                              padding: "5px 12px",
                              fontSize: "11px",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "5px",
                            }}
                          >
                            View Analysis <ArrowUpRight size={13} />
                          </Link>
                          <a
                            href={reportPdfUrl(survey._id)}
                            target="_blank"
                            rel="noreferrer"
                            className="secondary-btn"
                            style={{
                              padding: "5px 10px",
                              fontSize: "11px",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "5px",
                            }}
                            title="Download PDF Report"
                          >
                            <Download size={12} /> PDF
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 16px",
                borderTop: "1px solid var(--line)",
                background: "var(--panel-alt)",
                fontSize: "12px",
                color: "var(--muted)",
              }}
            >
              <span>
                Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}–
                {Math.min(currentPage * ITEMS_PER_PAGE, filteredSurveys.length)} of{" "}
                {filteredSurveys.length} surveys
              </span>

              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  style={{ padding: "4px 8px", fontSize: "11px", display: "inline-flex", alignItems: "center", gap: "4px" }}
                >
                  <ChevronLeft size={14} /> Prev
                </button>
                <span style={{ color: "var(--text)", fontWeight: 600 }}>
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  style={{ padding: "4px 8px", fontSize: "11px", display: "inline-flex", alignItems: "center", gap: "4px" }}
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
