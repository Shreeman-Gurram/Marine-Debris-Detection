// src/pages/Analytics.jsx
// Analytics & Operational Intelligence Dashboard for SONARIS
// Powered by Recharts & real MongoDB survey records
import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  CartesianGrid,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Compass,
  FileSearch,
  History,
  Info,
  Layers,
  PieChart as PieIcon,
  Radar,
  RefreshCw,
  ScanLine,
  ShieldAlert,
  TrendingUp,
  Waves,
} from "lucide-react";
import SectionHeader from "../components/SectionHeader";
import Badge from "../components/Badge";
import { getRecentSurveys } from "../services/api";
import { extractAlertsFromSurveys, formatAnomalyName } from "../utils/alerts";
import { RISK_TONE } from "../utils/constants";

// Known detector taxonomy
const DETECTOR_CLASSES = [
  "submarine_pipeline",
  "shipwreck",
  "ghost_net",
  "mine_cylinder",
  "crab_pot",
];

// Custom Recharts Modern Light Tooltip
function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div
        style={{
          background: "rgba(255, 255, 255, 0.98)",
          border: "1px solid var(--line)",
          borderRadius: "8px",
          padding: "8px 12px",
          color: "var(--text)",
          fontSize: "12px",
          boxShadow: "var(--shadow-md)",
        }}
      >
        <div style={{ fontWeight: 600, marginBottom: "4px", color: "var(--primary)" }}>
          {label}
        </div>
        {payload.map((item, idx) => (
          <div key={idx} style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <span style={{ color: "var(--muted)" }}>{item.name}:</span>
            <strong style={{ color: item.color || "var(--text)" }}>{item.value}</strong>
          </div>
        ))}
      </div>
    );
  }
  return null;
}

export default function Analytics() {
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadAnalyticsData() {
    try {
      setLoading(true);
      const data = await getRecentSurveys(100);
      setSurveys(data || []);
      setError(null);
    } catch (err) {
      console.error("Failed to load analytics surveys:", err);
      setError(err.message || "Failed to load operational analytics data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAnalyticsData();
  }, []);

  const allAlerts = useMemo(() => extractAlertsFromSurveys(surveys), [surveys]);

  // 6 Top KPI Metrics calculated strictly from real data
  const kpis = useMemo(() => {
    const totalSurveys = surveys.length;
    const totalAnomalies = allAlerts.length;

    let high = 0;
    let medium = 0;
    let low = 0;
    let confSum = 0;
    let maxRisk = 0;

    allAlerts.forEach((a) => {
      if (a.riskLevel === "CRITICAL" || a.riskLevel === "HIGH") high++;
      else if (a.riskLevel === "MEDIUM") medium++;
      else low++;

      if (a.confidence != null) confSum += a.confidence;
      if (a.riskScore != null && a.riskScore > maxRisk) maxRisk = a.riskScore;
    });

    const avgConfidence = totalAnomalies > 0 ? (confSum / totalAnomalies) * 100 : 0;

    return {
      totalSurveys,
      totalAnomalies,
      high,
      medium,
      low,
      avgConfidence,
      maxRisk,
    };
  }, [surveys, allAlerts]);

  // Chart A: Detection Class Distribution
  const classData = useMemo(() => {
    const counts = {};
    DETECTOR_CLASSES.forEach((c) => (counts[c] = 0));

    allAlerts.forEach((a) => {
      const c = a.className;
      counts[c] = (counts[c] || 0) + 1;
    });

    return Object.keys(counts).map((key) => ({
      name: formatAnomalyName(key),
      count: counts[key],
    }));
  }, [allAlerts]);

  // Chart B: Priority Distribution (Donut / Pie)
  const priorityData = useMemo(() => {
    return [
      { name: "High", value: kpis.high, color: "#f36d7a" },
      { name: "Medium", value: kpis.medium, color: "#f4b84b" },
      { name: "Low", value: kpis.low, color: "#49b7ff" },
    ].filter((item) => item.value > 0 || kpis.totalAnomalies === 0);
  }, [kpis]);

  // Chart C: Confidence Ranges (0-20%, 20-40%, 40-60%, 60-80%, 80-100%)
  const confidenceData = useMemo(() => {
    const bins = [
      { range: "0–20%", count: 0 },
      { range: "20–40%", count: 0 },
      { range: "40–60%", count: 0 },
      { range: "60–80%", count: 0 },
      { range: "80–100%", count: 0 },
    ];

    allAlerts.forEach((a) => {
      const c = (a.confidence || 0) * 100;
      if (c <= 20) bins[0].count++;
      else if (c <= 40) bins[1].count++;
      else if (c <= 60) bins[2].count++;
      else if (c <= 80) bins[3].count++;
      else bins[4].count++;
    });

    return bins;
  }, [allAlerts]);

  // Chart D: Risk Score Spectrum (0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
  const riskData = useMemo(() => {
    const bins = [
      { range: "0.0–0.2", count: 0 },
      { range: "0.2–0.4", count: 0 },
      { range: "0.4–0.6", count: 0 },
      { range: "0.6–0.8", count: 0 },
      { range: "0.8–1.0", count: 0 },
    ];

    allAlerts.forEach((a) => {
      const r = a.riskScore || 0;
      if (r <= 0.2) bins[0].count++;
      else if (r <= 0.4) bins[1].count++;
      else if (r <= 0.6) bins[2].count++;
      else if (r <= 0.8) bins[3].count++;
      else bins[4].count++;
    });

    return bins;
  }, [allAlerts]);

  // Chart E: Survey Activity over Time
  const activityData = useMemo(() => {
    if (surveys.length === 0) return [];

    const grouped = {};
    surveys.forEach((s) => {
      const dateKey = s.created_at
        ? new Date(s.created_at).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })
        : "Initial";

      if (!grouped[dateKey]) {
        grouped[dateKey] = { date: dateKey, surveys: 0, anomalies: 0 };
      }
      grouped[dateKey].surveys++;
      grouped[dateKey].anomalies += s.detections?.length || s.total_detections || 0;
    });

    return Object.values(grouped);
  }, [surveys]);

  // Operational Insights derived strictly from real data
  const insights = useMemo(() => {
    if (allAlerts.length === 0) {
      return ["Insufficient survey history for trend analysis."];
    }

    const items = [];

    // Most frequent class
    const counts = {};
    allAlerts.forEach((a) => {
      counts[a.className] = (counts[a.className] || 0) + 1;
    });
    let topClass = "";
    let topCount = 0;
    Object.entries(counts).forEach(([k, v]) => {
      if (v > topCount) {
        topCount = v;
        topClass = k;
      }
    });
    if (topClass) {
      items.push(`Most frequent anomaly: ${formatAnomalyName(topClass)} (${topCount} occurrences)`);
    }

    // Peak risk
    items.push(`Highest observed threat risk: ${kpis.maxRisk.toFixed(2)} / 1.0`);

    // Avg confidence
    items.push(`Average neural detection confidence: ${kpis.avgConfidence.toFixed(1)}%`);

    // Survey coverage
    const flaggedSurveys = surveys.filter((s) => (s.detections?.length || 0) > 0).length;
    items.push(`${flaggedSurveys} of ${surveys.length} surveys contain confirmed acoustic anomalies`);

    // Geolocation breakdown
    const gpsCount = allAlerts.filter((a) => a.hasGps).length;
    const localCount = allAlerts.length - gpsCount;
    if (gpsCount > 0) {
      items.push(`${gpsCount} contacts localized via WGS84 GNSS coordinates`);
    }
    if (localCount > 0) {
      items.push(`${localCount} contacts georeferenced relative to local sonar swath`);
    }

    return items;
  }, [allAlerts, surveys, kpis]);

  return (
    <div>
      {/* Top Header */}
      <div className="page-heading">
        <div>
          <span className="eyebrow">MISSION INTELLIGENCE & TELEMETRY</span>
          <h1>ANALYTICS & OPERATIONAL METRICS</h1>
          <p>Aggregate anomaly metrics, threat distributions, and acoustic detection telemetry</p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            className="secondary-btn"
            onClick={loadAnalyticsData}
            disabled={loading}
            style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh Analytics
          </button>
          <Link to="/history" className="secondary-btn" style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
            <History size={15} /> Survey History
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

      {/* 6 TOP KPI CARDS */}
      <div className="kpi-summary-grid" style={{ marginBottom: "24px" }}>
        {/* 1. Total Surveys */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Total Surveys</span>
            <Waves size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">
            {kpis.totalSurveys}
            <span style={{ fontSize: "12px", color: "var(--muted)", fontWeight: 400 }}>processed</span>
          </div>
          <div className="kpi-sub">Archived survey missions</div>
        </div>

        {/* 2. Total Anomalies */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Total Anomalies</span>
            <Radar size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">
            {kpis.totalAnomalies}
            <span style={{ fontSize: "12px", color: "var(--muted)", fontWeight: 400 }}>contacts</span>
          </div>
          <div className="kpi-sub">Target contacts detected</div>
        </div>

        {/* 3. High Priority */}
        <div className="kpi-card kpi-card-high" style={{ borderColor: kpis.high > 0 ? "rgba(224, 76, 90, 0.4)" : "" }}>
          <div className="kpi-label">
            <span>High Priority</span>
            <ShieldAlert size={15} color="var(--red)" />
          </div>
          <div className="kpi-value" style={{ color: kpis.high > 0 ? "var(--red)" : "var(--text)" }}>
            {kpis.high}
          </div>
          <div className="kpi-sub">Critical threat contacts</div>
        </div>

        {/* 4. Medium Priority */}
        <div className="kpi-card" style={{ borderColor: kpis.medium > 0 ? "rgba(217, 131, 36, 0.4)" : "" }}>
          <div className="kpi-label">
            <span>Medium Priority</span>
            <AlertTriangle size={15} color="var(--amber)" />
          </div>
          <div className="kpi-value" style={{ color: kpis.medium > 0 ? "var(--amber)" : "var(--text)" }}>
            {kpis.medium}
          </div>
          <div className="kpi-sub">Acoustic targets requiring review</div>
        </div>

        {/* 5. Low Priority */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Low Priority</span>
            <Layers size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">
            {kpis.low}
          </div>
          <div className="kpi-sub">Routine seabed features</div>
        </div>

        {/* 6. Average Confidence */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Avg Confidence</span>
            <Activity size={15} color="var(--green)" />
          </div>
          <div className="kpi-value" style={{ color: "var(--green)" }}>
            {kpis.avgConfidence > 0 ? `${kpis.avgConfidence.toFixed(1)}%` : "N/A"}
          </div>
          <div className="kpi-sub">Neural network certainty</div>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--muted)" }}>
          <ScanLine size={36} color="var(--primary)" style={{ animation: "spin 2s linear infinite", marginBottom: "12px" }} />
          <p>Compiling acoustic analytics and threat distributions...</p>
        </div>
      ) : kpis.totalSurveys === 0 ? (
        <div className="clean-scan-card" style={{ margin: "20px 0" }}>
          <FileSearch size={48} color="var(--primary)" style={{ margin: "0 auto 12px auto", opacity: 0.8 }} />
          <h3 style={{ color: "var(--text)", marginBottom: "6px" }}>No Analytics Data Available</h3>
          <p style={{ fontSize: "13px", color: "var(--muted)", maxWidth: "440px", margin: "0 auto" }}>
            Upload and analyze side-scan sonar surveys to populate neural detection distributions and operational telemetry.
          </p>
          <div style={{ marginTop: "18px" }}>
            <Link to="/surveys/new" className="primary-btn">
              Upload Survey
            </Link>
          </div>
        </div>
      ) : (
        <>
          {/* CHARTS GRID — ROW 1 */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "20px", marginBottom: "20px" }}>
            {/* Chart A: Detection Class Distribution */}
            <section className="panel">
              <SectionHeader
                title="Target Class Taxonomy"
                subtitle="Detections by classified seabed anomaly type"
              />
              <div style={{ height: "260px", marginTop: "12px" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={classData} margin={{ top: 10, right: 10, left: -10, bottom: 25 }}>
                    <CartesianGrid stroke="#1a2b40" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="name"
                      stroke="#8fa0b8"
                      fontSize={10}
                      angle={-20}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis stroke="#8fa0b8" fontSize={11} allowDecimals={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="count" name="Detections" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* Chart B: Priority Distribution */}
            <section className="panel">
              <SectionHeader
                title="Priority Tier Allocation"
                subtitle="Threat level classification ratio"
              />
              <div style={{ height: "260px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                {kpis.totalAnomalies === 0 ? (
                  <div style={{ color: "var(--muted)", textAlign: "center" }}>
                    <CheckCircle2 size={32} color="var(--green)" style={{ margin: "0 auto 8px auto" }} />
                    <p style={{ fontSize: "13px" }}>No anomalies flagged across surveys</p>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={priorityData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {priorityData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} stroke="#08111f" strokeWidth={2} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
              {/* Legend strip */}
              <div style={{ display: "flex", justifyContent: "center", gap: "16px", fontSize: "12px", color: "var(--muted)", borderTop: "1px solid var(--line)", paddingTop: "10px" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#f36d7a" }} />
                  High ({kpis.high})
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#f4b84b" }} />
                  Medium ({kpis.medium})
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#49b7ff" }} />
                  Low ({kpis.low})
                </span>
              </div>
            </section>
          </div>

          {/* CHARTS GRID — ROW 2 */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "20px", marginBottom: "20px" }}>
            {/* Chart C: Confidence Distribution */}
            <section className="panel">
              <SectionHeader
                title="Confidence Spectrum"
                subtitle="Neural network detection certainty grouping"
              />
              <div style={{ height: "240px", marginTop: "12px" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={confidenceData} margin={{ top: 10, right: 10, left: -10, bottom: 10 }}>
                    <CartesianGrid stroke="#1a2b40" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="range" stroke="#8fa0b8" fontSize={11} />
                    <YAxis stroke="#8fa0b8" fontSize={11} allowDecimals={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="count" name="Detections" fill="#35d39a" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* Chart D: Risk Score Distribution */}
            <section className="panel">
              <SectionHeader
                title="Threat Risk Spectrum"
                subtitle="Calculated obstacle threat index bracket"
              />
              <div style={{ height: "240px", marginTop: "12px" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={riskData} margin={{ top: 10, right: 10, left: -10, bottom: 10 }}>
                    <CartesianGrid stroke="#1a2b40" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="range" stroke="#8fa0b8" fontSize={11} />
                    <YAxis stroke="#8fa0b8" fontSize={11} allowDecimals={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="count" name="Detections" fill="#f4b84b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>

          {/* CHARTS GRID — ROW 3: Activity Timeline */}
          <section className="panel" style={{ marginBottom: "20px" }}>
            <SectionHeader
              title="Survey & Contact Activity Timeline"
              subtitle="Temporal distribution of acoustic survey passes and detections"
            />
            <div style={{ height: "240px", marginTop: "12px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={activityData} margin={{ top: 10, right: 15, left: -10, bottom: 10 }}>
                  <defs>
                    <linearGradient id="colorSurveys" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="var(--primary)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorAnomalies" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--red)" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="var(--red)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#1a2b40" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" stroke="#8fa0b8" fontSize={11} />
                  <YAxis stroke="#8fa0b8" fontSize={11} allowDecimals={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="surveys"
                    name="Surveys"
                    stroke="var(--primary)"
                    fillOpacity={1}
                    fill="url(#colorSurveys)"
                  />
                  <Area
                    type="monotone"
                    dataKey="anomalies"
                    name="Anomalies"
                    stroke="var(--red)"
                    fillOpacity={1}
                    fill="url(#colorAnomalies)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* OPERATIONAL INSIGHTS PANEL */}
          <section className="panel">
            <SectionHeader
              title="Operational Insights & Telemetry Audit"
              subtitle="Automated intelligence derived strictly from real survey records"
            />

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px", marginTop: "14px" }}>
              {insights.map((text, idx) => (
                <div
                  key={idx}
                  style={{
                    background: "var(--panel-alt)",
                    border: "1px solid var(--line)",
                    borderRadius: "8px",
                    padding: "12px 14px",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "10px",
                    fontSize: "12px",
                  }}
                >
                  <TrendingUp size={16} color="var(--primary)" style={{ flexShrink: 0, marginTop: "2px" }} />
                  <span style={{ color: "var(--text)", lineHeight: "1.5" }}>{text}</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
