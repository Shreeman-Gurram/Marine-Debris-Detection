// src/pages/Alerts.jsx
// Priority Alerts Operational Feed for SONARIS Marine Intelligence
import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Compass,
  FileImage,
  Filter,
  Layers,
  MapPin,
  Radar,
  ScanLine,
  ShieldAlert,
  SlidersHorizontal,
  Waves,
  RefreshCw,
} from "lucide-react";
import SectionHeader from "../components/SectionHeader";
import Badge from "../components/Badge";
import { getRecentSurveys, evidenceUrl } from "../services/api";
import { extractAlertsFromSurveys, formatAnomalyName, formatAlertDate } from "../utils/alerts";
import { RISK_TONE } from "../utils/constants";

export default function Alerts() {
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterPriority, setFilterPriority] = useState("ALL"); // "ALL" | "HIGH" | "MEDIUM" | "LOW" | "GPS" | "LOCAL"
  const [searchQuery, setSearchQuery] = useState("");

  async function loadAlerts() {
    try {
      setLoading(true);
      const data = await getRecentSurveys(50);
      setSurveys(data || []);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch surveys for alerts:", err);
      setError(err.message || "Failed to load priority alerts from database.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAlerts();
  }, []);

  const allAlerts = useMemo(() => extractAlertsFromSurveys(surveys), [surveys]);

  // Dynamic summary counters calculated from real data
  const stats = useMemo(() => {
    let high = 0;
    let medium = 0;
    let low = 0;

    allAlerts.forEach((a) => {
      if (a.riskLevel === "CRITICAL" || a.riskLevel === "HIGH") high++;
      else if (a.riskLevel === "MEDIUM") medium++;
      else low++;
    });

    return {
      total: allAlerts.length,
      high,
      medium,
      low,
    };
  }, [allAlerts]);

  // Filtered alerts
  const filteredAlerts = useMemo(() => {
    return allAlerts.filter((alert) => {
      // Priority filter
      if (filterPriority === "HIGH" && !(alert.riskLevel === "HIGH" || alert.riskLevel === "CRITICAL")) return false;
      if (filterPriority === "MEDIUM" && alert.riskLevel !== "MEDIUM") return false;
      if (filterPriority === "LOW" && alert.riskLevel !== "LOW") return false;
      if (filterPriority === "GPS" && !alert.hasGps) return false;
      if (filterPriority === "LOCAL" && alert.hasGps) return false;

      // Text search
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesName = alert.className.toLowerCase().includes(query);
        const matchesFile = alert.surveyFilename.toLowerCase().includes(query);
        if (!matchesName && !matchesFile) return false;
      }

      return true;
    });
  }, [allAlerts, filterPriority, searchQuery]);

  return (
    <div>
      {/* Top Header */}
      <div className="page-heading">
        <div>
          <span className="eyebrow">PRIORITY RADAR & THREAT SURVEILLANCE</span>
          <h1>Priority Alerts</h1>
          <p>Consolidated operational stream of candidate contacts and seabed anomalies</p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            className="secondary-btn"
            onClick={loadAlerts}
            disabled={loading}
            style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh Feed
          </button>
          <Link to="/map" className="secondary-btn" style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
            <Compass size={15} /> Geospatial Map
          </Link>
          <Link to="/surveys/new" className="primary-btn">
            New Survey
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
          <span>Notice: {error}</span>
        </div>
      )}

      {/* SUMMARY STATS STRIP */}
      <div className="kpi-summary-grid" style={{ marginBottom: "20px" }}>
        {/* Total Alerts */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Total Alerts</span>
            <Radar size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">
            {stats.total}
            <span style={{ fontSize: "12px", color: "var(--muted)", fontWeight: 400 }}>contacts</span>
          </div>
          <div className="kpi-sub">Flagged seabed anomalies</div>
        </div>

        {/* High Priority */}
        <div className="kpi-card kpi-card-high" style={{ borderColor: stats.high > 0 ? "rgba(224, 76, 90, 0.4)" : "" }}>
          <div className="kpi-label">
            <span>High Priority</span>
            <ShieldAlert size={15} color="var(--red)" />
          </div>
          <div className="kpi-value" style={{ color: stats.high > 0 ? "var(--red)" : "var(--text)" }}>
            {stats.high}
          </div>
          <div className="kpi-sub">Critical threat / obstacle</div>
        </div>

        {/* Medium Priority */}
        <div className="kpi-card" style={{ borderColor: stats.medium > 0 ? "rgba(217, 131, 36, 0.4)" : "" }}>
          <div className="kpi-label">
            <span>Medium Priority</span>
            <AlertTriangle size={15} color="var(--amber)" />
          </div>
          <div className="kpi-value" style={{ color: stats.medium > 0 ? "var(--amber)" : "var(--text)" }}>
            {stats.medium}
          </div>
          <div className="kpi-sub">Acoustic contact requiring audit</div>
        </div>

        {/* Low Priority */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Low Priority</span>
            <Layers size={15} color="var(--green)" />
          </div>
          <div className="kpi-value">
            {stats.low}
          </div>
          <div className="kpi-sub">Routine seabed features</div>
        </div>
      </div>

      {/* FILTER & SEARCH STRIP */}
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
            className={filterPriority === "ALL" ? "active" : ""}
            onClick={() => setFilterPriority("ALL")}
          >
            All ({stats.total})
          </button>
          <button
            type="button"
            className={filterPriority === "HIGH" ? "active" : ""}
            onClick={() => setFilterPriority("HIGH")}
          >
            High ({stats.high})
          </button>
          <button
            type="button"
            className={filterPriority === "MEDIUM" ? "active" : ""}
            onClick={() => setFilterPriority("MEDIUM")}
          >
            Medium ({stats.medium})
          </button>
          <button
            type="button"
            className={filterPriority === "LOW" ? "active" : ""}
            onClick={() => setFilterPriority("LOW")}
          >
            Low ({stats.low})
          </button>
          <button
            type="button"
            className={filterPriority === "GPS" ? "active" : ""}
            onClick={() => setFilterPriority("GPS")}
          >
            GPS Plotted
          </button>
          <button
            type="button"
            className={filterPriority === "LOCAL" ? "active" : ""}
            onClick={() => setFilterPriority("LOCAL")}
          >
            Local Sonar
          </button>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <input
            type="text"
            placeholder="Search anomaly class or file..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              background: "var(--panel-alt)",
              border: "1px solid var(--line)",
              borderRadius: "6px",
              padding: "6px 12px",
              color: "var(--text)",
              fontSize: "12px",
              minWidth: "220px",
            }}
          />
        </div>
      </div>

      {/* ALERTS FEED CONTAINER */}
      {loading ? (
        <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--muted)" }}>
          <ScanLine size={36} color="var(--primary)" style={{ animation: "spin 2s linear infinite", marginBottom: "12px" }} />
          <p>Scanning intelligence database for active priority alerts...</p>
        </div>
      ) : allAlerts.length === 0 ? (
        /* CLEAN STATE: ZERO ACTIVE ANOMALIES */
        <div className="clean-scan-card" style={{ margin: "20px 0" }}>
          <CheckCircle2 size={48} color="var(--green)" style={{ margin: "0 auto 12px auto" }} />
          <h3 style={{ color: "var(--text)", marginBottom: "6px" }}>🟢 No Active Anomalies</h3>
          <p style={{ fontSize: "13px", color: "var(--muted)", maxWidth: "440px", margin: "0 auto" }}>
            The operational mission queue is clear. No seabed threats or acoustic anomalies are currently awaiting investigation.
          </p>
          <div style={{ marginTop: "18px" }}>
            <Link to="/surveys/new" className="primary-btn">
              Upload New Sonar Survey
            </Link>
          </div>
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--muted)", background: "var(--panel)", borderRadius: "10px", border: "1px solid var(--line)" }}>
          <Filter size={32} style={{ opacity: 0.5, marginBottom: "8px" }} />
          <p>No alerts matching the selected filter criteria.</p>
        </div>
      ) : (
        /* ALERTS LIST */
        <div style={{ display: "grid", gap: "14px" }}>
          {filteredAlerts.map((alert) => {
            const tone = RISK_TONE[alert.riskLevel] || "neutral";
            const isHigh = alert.riskLevel === "CRITICAL" || alert.riskLevel === "HIGH";
            const isMedium = alert.riskLevel === "MEDIUM";
            const borderColor = isHigh
              ? "rgba(224, 76, 90, 0.4)"
              : isMedium
              ? "rgba(217, 131, 36, 0.4)"
              : "var(--line)";

            return (
              <div
                key={alert.id}
                className="panel"
                style={{
                  borderLeft: `4px solid ${
                    isHigh ? "var(--red)" : isMedium ? "var(--amber)" : "var(--primary)"
                  }`,
                  borderColor: borderColor,
                  padding: "16px 20px",
                  transition: "transform 0.15s ease, border-color 0.15s ease",
                  background: "var(--panel)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: "16px",
                  }}
                >
                  {/* Left: Info Block */}
                  <div style={{ flex: 1, minWidth: "280px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                      <h3 style={{ margin: 0, fontSize: "16px", color: "var(--text)" }}>
                        {formatAnomalyName(alert.className)}
                      </h3>
                      <Badge tone={tone}>{alert.riskLevel} PRIORITY</Badge>
                      <span
                        style={{
                          fontSize: "11px",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          background: "var(--panel-alt)",
                          color: "var(--muted)",
                          border: "1px solid var(--line)",
                        }}
                      >
                        {alert.filterStatus || "GATE_PASS"}
                      </span>
                    </div>

                    {/* Metadata Subtitle */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "14px",
                        fontSize: "12px",
                        color: "var(--muted)",
                        marginTop: "6px",
                        flexWrap: "wrap",
                      }}
                    >
                      <span>Survey: <code style={{ color: "var(--text)" }}>{alert.surveyFilename}</code></span>
                      <span>·</span>
                      <span>Logged: {formatAlertDate(alert.timestamp)}</span>
                      <span>·</span>
                      <span>Mission ID: <code>{alert.surveyId}</code></span>
                    </div>

                    {/* Metrics Strip */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                        gap: "10px",
                        margin: "12px 0",
                        background: "var(--panel-alt)",
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "1px solid var(--line)",
                        fontSize: "12px",
                      }}
                    >
                      <div>
                        <span style={{ color: "var(--muted)", display: "block" }}>Confidence</span>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
                          <strong style={{ color: "var(--primary)" }}>
                            {alert.confidence != null ? `${(alert.confidence * 100).toFixed(1)}%` : "N/A"}
                          </strong>
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
                                width: `${Math.round((alert.confidence || 0) * 100)}%`,
                                height: "100%",
                                background: "var(--primary)",
                              }}
                            />
                          </div>
                        </div>
                      </div>

                      <div>
                        <span style={{ color: "var(--muted)", display: "block" }}>Risk Threat</span>
                        <strong style={{ color: isHigh ? "var(--red)" : isMedium ? "var(--amber)" : "var(--text)" }}>
                          {alert.riskScore != null ? Number(alert.riskScore).toFixed(2) : "0.00"}
                          <span style={{ fontSize: "10px", color: "var(--muted)", fontWeight: 400 }}> / 1.0</span>
                        </strong>
                      </div>

                      <div>
                        <span style={{ color: "var(--muted)", display: "block" }}>Bounding Box</span>
                        <code style={{ fontSize: "11px", color: "var(--muted)" }}>
                          {alert.bbox ? `[${alert.bbox.map((v) => Math.round(v)).join(", ")}]` : "N/A"}
                        </code>
                      </div>
                    </div>

                    {/* Geolocation Telemetry */}
                    <div
                      style={{
                        padding: "8px 12px",
                        borderRadius: "6px",
                        background: alert.hasGps ? "rgba(16, 185, 129, 0.08)" : "rgba(217, 131, 36, 0.08)",
                        border: `1px solid ${alert.hasGps ? "rgba(16, 185, 129, 0.25)" : "rgba(217, 131, 36, 0.25)"}`,
                        fontSize: "12px",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        flexWrap: "wrap",
                      }}
                    >
                      {alert.hasGps ? (
                        <>
                          <MapPin size={15} color="var(--green)" />
                          <span style={{ color: "var(--green)", fontWeight: 600 }}>WGS84 Coordinates:</span>
                          <strong style={{ color: "var(--text)" }}>
                            {alert.latitude.toFixed(6)}°N, {alert.longitude.toFixed(6)}°E
                          </strong>
                          {alert.uncertainty_m != null && (
                            <span style={{ color: "var(--muted)" }}>
                              (Uncertainty: ±{alert.uncertainty_m.toFixed(1)}m)
                            </span>
                          )}
                        </>
                      ) : (
                        <>
                          <Compass size={15} color="var(--amber)" />
                          <span style={{ color: "var(--amber)", fontWeight: 600 }}>
                            ⚠️ Geolocation unavailable (Local Sonar Frame):
                          </span>
                          <span style={{ color: "var(--text)" }}>
                            Local X: <strong>{alert.local_x_m != null ? `${alert.local_x_m.toFixed(2)}m` : "0m"}</strong>,{" "}
                            Y: <strong>{alert.local_y_m != null ? `${alert.local_y_m.toFixed(2)}m` : "0m"}</strong> ·{" "}
                            Range: <strong>{alert.range_m != null ? `${alert.range_m.toFixed(2)}m` : "N/A"}</strong> ·{" "}
                            Bearing: <strong>{alert.bearing_deg != null ? `${alert.bearing_deg.toFixed(1)}°` : "90°"}</strong>
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Right: Evidence Thumbnail & Action */}
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "flex-end",
                      gap: "12px",
                      flexShrink: 0,
                    }}
                  >
                    {alert.evidenceImage && (
                      <div
                        style={{
                          width: "120px",
                          height: "75px",
                          borderRadius: "6px",
                          overflow: "hidden",
                          border: "1px solid var(--line)",
                          background: "#050b14",
                          position: "relative",
                        }}
                      >
                        <img
                          src={evidenceUrl(alert.evidenceImage)}
                          alt="Evidence Thumbnail"
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        />
                        <span
                          style={{
                            position: "absolute",
                            bottom: "2px",
                            right: "4px",
                            fontSize: "9px",
                            background: "rgba(0,0,0,0.7)",
                            padding: "1px 4px",
                            borderRadius: "3px",
                            color: "var(--primary)",
                          }}
                        >
                          DRISHTI
                        </span>
                      </div>
                    )}

                    <Link
                      to={`/analysis/${alert.surveyId}`}
                      className="primary-btn"
                      style={{
                        padding: "8px 14px",
                        fontSize: "12px",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      View Analysis <ArrowUpRight size={14} />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
