// src/pages/Dashboard.jsx
import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Plus,
  Waves,
  ScanLine,
  Clock,
  Compass,
  FileSearch,
} from "lucide-react";
import { Link } from "react-router-dom";
import StatCard from "../components/StatCard";
import SectionHeader from "../components/SectionHeader";
import Badge from "../components/Badge";
import EmptyState from "../components/EmptyState";
import { getDashboardStats, getRecentSurveys, evidenceUrl } from "../services/api";
import { RISK_DOT, RISK_TONE } from "../utils/constants";
import { extractAlertsFromSurveys, formatAnomalyName } from "../utils/alerts";

function formatClassName(raw) {
  if (!raw) return "Anomaly";
  return raw
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(dateStr) {
  if (!dateStr) return "Just now";
  try {
    const d = new Date(dateStr);
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

function getHighestPriority(detections = []) {
  if (!detections.length) return "NONE";
  const levels = detections.map((d) => (d.risk_level || "LOW").toUpperCase());
  if (levels.includes("CRITICAL")) return "CRITICAL";
  if (levels.includes("HIGH")) return "HIGH";
  if (levels.includes("MEDIUM")) return "MEDIUM";
  return "LOW";
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function loadData() {
      try {
        setLoading(true);
        const [statsData, surveysData] = await Promise.all([
          getDashboardStats(),
          getRecentSurveys(20),
        ]);
        if (mounted) {
          setStats(statsData);
          setSurveys(surveysData);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          console.error("Failed to load dashboard data:", err);
          setError(err.message || "Failed to load dashboard data");
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--muted)" }}>
        <ScanLine size={32} style={{ animation: "spin 2s linear infinite", marginBottom: "12px" }} />
        <p>Connecting to SONARIS intelligence database...</p>
      </div>
    );
  }

  const recentSurvey = surveys.length > 0 ? surveys[0] : null;

  // Build unified real priority queue from recent surveys
  const priorityQueue = extractAlertsFromSurveys(surveys);

  return (
    <div>
      {/* Top Page Heading */}
      <div className="page-heading">
        <div>
          <span className="eyebrow">OPERATIONAL DASHBOARD</span>
          <h1>Marine Intelligence Platform</h1>
          <p>Real-time Side-Scan Sonar anomaly detection & threat assessment</p>
        </div>
        <Link className="primary-btn" to="/surveys/new">
          <Plus size={18} /> New survey
        </Link>
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
          <span>Notice: {error} (Check backend connection)</span>
        </div>
      )}

      {/* Summary Stats Cards */}
      <div className="stats-grid">
        <StatCard
          icon={Waves}
          label="Total surveys"
          value={stats ? stats.total_surveys : 0}
          detail="MongoDB archive"
          tone="blue"
        />
        <StatCard
          icon={AlertTriangle}
          label="Detected anomalies"
          value={stats ? stats.total_anomalies : 0}
          detail="Across all missions"
          tone="amber"
        />
        <StatCard
          icon={Activity}
          label="High priority"
          value={stats ? stats.high_priority : 0}
          detail="Requires verification"
          tone="red"
        />
        <StatCard
          icon={CheckCircle2}
          label="Reviewed status"
          value={stats ? `${stats.reviewed}` : "0"}
          detail="Human validated"
          tone="green"
        />
      </div>

      {/* Content Grid */}
      <div className="content-grid two-one">
        {/* Recent Survey Panel */}
        <section className="panel">
          <SectionHeader
            title="Recent survey"
            subtitle="Latest processed mission"
            action={
              recentSurvey ? (
                <Link className="text-link" to={`/analysis/${recentSurvey._id}`}>
                  View analysis <ArrowUpRight size={15} />
                </Link>
              ) : null
            }
          />

          {!recentSurvey ? (
            <div style={{ padding: "30px 10px" }}>
              <EmptyState
                title="No surveys analyzed yet"
                text="Upload side-scan sonar imagery to begin automated DRISHTI anomaly detection."
              />
              <div style={{ textAlign: "center", marginTop: "16px" }}>
                <Link to="/surveys/new" className="primary-btn" style={{ display: "inline-flex" }}>
                  <Plus size={16} /> Start First Survey
                </Link>
              </div>
            </div>
          ) : (
            <div>
              {/* Evidence image preview if available */}
              {recentSurvey.evidence_image && (
                <div
                  style={{
                    position: "relative",
                    borderRadius: "10px",
                    overflow: "hidden",
                    border: "1px solid var(--line)",
                    marginBottom: "16px",
                    background: "#050b14",
                    maxHeight: "240px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <img
                    src={evidenceUrl(recentSurvey.evidence_image)}
                    alt="Latest Sonar Analysis"
                    style={{
                      width: "100%",
                      height: "auto",
                      maxHeight: "240px",
                      objectFit: "contain",
                      display: "block",
                    }}
                  />
                  <div
                    style={{
                      position: "absolute",
                      bottom: "10px",
                      left: "10px",
                      background: "rgba(7, 59, 92, 0.88)",
                      backdropFilter: "blur(6px)",
                      border: "1px solid rgba(255, 255, 255, 0.2)",
                      borderRadius: "6px",
                      padding: "4px 10px",
                      fontSize: "11px",
                      color: "#ffffff",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <ScanLine size={13} />
                    <span>Analyzed Evidence Image</span>
                  </div>
                </div>
              )}

              <div className="survey-row">
                <div className="survey-thumb">
                  <Waves size={26} />
                </div>
                <div className="survey-main">
                  <div className="row-between">
                    <strong>{recentSurvey.filename}</strong>
                    <Badge tone={RISK_TONE[getHighestPriority(recentSurvey.detections)] || "success"}>
                      {getHighestPriority(recentSurvey.detections)} PRIORITY
                    </Badge>
                  </div>
                  <p style={{ display: "flex", alignItems: "center", gap: "14px", marginTop: "4px" }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                      <Clock size={13} /> {formatDate(recentSurvey.created_at)}
                    </span>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                      <Compass size={13} />
                      {recentSurvey.detections?.[0]?.geolocation?.latitude != null
                        ? `${recentSurvey.detections[0].geolocation.latitude.toFixed(4)}°N, ${recentSurvey.detections[0].geolocation.longitude.toFixed(4)}°E`
                        : "Geolocation unavailable (Local sonar)"}
                    </span>
                  </p>
                  <div className="progress" style={{ marginTop: "12px" }}>
                    <span style={{ width: "100%" }} />
                  </div>
                  <small style={{ display: "block", marginTop: "6px" }}>
                    Analysis complete · {recentSurvey.total_detections ?? recentSurvey.detections?.length ?? 0} anomalies detected
                  </small>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Priority Queue Panel */}
        <section className="panel">
          <SectionHeader
            title="Priority queue"
            subtitle="Anomalies requiring attention"
          />

          {priorityQueue.length === 0 ? (
            <div style={{ padding: "30px 10px" }}>
              <div className="empty-state">
                <FileSearch size={32} />
                <h3 style={{ fontSize: "15px", marginTop: "10px" }}>No anomalies flagged</h3>
                <p style={{ fontSize: "12px", color: "var(--muted)" }}>
                  No active detections requiring human review at this time.
                </p>
              </div>
            </div>
          ) : (
            <div className="priority-list">
              {priorityQueue.map((item) => {
                const tone = RISK_TONE[(item.risk_level || "LOW").toUpperCase()] || "neutral";
                const dotClass = RISK_DOT[(item.risk_level || "LOW").toUpperCase()] || "low";
                const confPercent = Math.round((item.confidence || 0) * 100);

                return (
                  <Link
                    to={`/analysis/${item.surveyId}`}
                    className="priority-item"
                    key={item.key}
                  >
                    <span className={`priority-dot ${dotClass}`} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <strong>{formatName(item.class_name)}</strong>
                        <Badge tone={tone}>
                          {item.risk_level || "LOW"}
                        </Badge>
                      </div>
                      <small style={{ color: "var(--muted)", marginTop: "2px", display: "block" }}>
                        {confPercent}% confidence · Risk score: {item.risk_score != null ? Number(item.risk_score).toFixed(2) : "N/A"}
                      </small>
                      <small style={{ color: "var(--muted)", fontSize: "11px", display: "block" }}>
                        {item.geolocation?.status === "relative"
                          ? `Local: ${item.geolocation?.range_m?.toFixed(1)}m @ ${item.geolocation?.bearing_deg?.toFixed(0)}°`
                          : item.geolocation?.latitude != null
                          ? `GPS: ${item.geolocation.latitude.toFixed(4)}, ${item.geolocation.longitude.toFixed(4)}`
                          : "Geolocation unavailable"}
                      </small>
                    </div>
                    <ArrowUpRight size={16} />
                  </Link>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function formatName(raw) {
  if (!raw) return "Anomaly";
  return raw
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
