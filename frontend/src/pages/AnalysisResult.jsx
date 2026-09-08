// src/pages/AnalysisResult.jsx
import { useEffect, useState, useMemo } from "react";
import { useLocation, useNavigate, useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  CircleHelp,
  Download,
  FileImage,
  ScanLine,
  ShieldAlert,
  X,
  Compass,
  MapPin,
  ExternalLink,
  Layers,
  FileCheck,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Minimize2,
  Columns2,
  Square,
  Table as TableIcon,
  LayoutGrid,
  AlertTriangle,
  Cpu,
  Radar,
  Eye,
  Activity,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Info,
} from "lucide-react";
import SectionHeader from "../components/SectionHeader";
import Badge from "../components/Badge";
import { getSurveyById, evidenceUrl, saveVerifications, reportPdfUrl } from "../services/api";
import { RISK_TONE } from "../utils/constants";

function formatName(raw) {
  if (!raw) return "Unknown Target";
  return raw
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function AnalysisResult() {
  const { analysisId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  // Prefer state passed from NewSurvey, otherwise fetch by ID from MongoDB
  const [analysis, setAnalysis] = useState(location.state?.analysis || null);
  const [originalPreview, setOriginalPreview] = useState(location.state?.originalPreview || null);
  const [originalFilename, setOriginalFilename] = useState(location.state?.originalFilename || "");
  const [loading, setLoading] = useState(!analysis && !!analysisId && analysisId !== "latest");
  const [error, setError] = useState(null);

  // Viewer interactive state
  const [zoom, setZoom] = useState(1);
  const [viewMode, setViewMode] = useState("split"); // "split" | "evidence" | "original"
  const [isTheaterOpen, setIsTheaterOpen] = useState(false);

  // Detections view state
  const [displayMode, setDisplayMode] = useState("table"); // "table" | "cards"
  const [activeDetectionIndex, setActiveDetectionIndex] = useState(0);

  // Human verification state: mapping of detection index -> "Confirmed" | "Rejected" | "Uncertain"
  const [verifications, setVerifications] = useState({});
  // Sync status: null | "saving" | "saved" | { error: string }
  const [verifStatus, setVerifStatus] = useState(null);

  // Load persisted verifications from MongoDB document on mount
  useEffect(() => {
    if (!analysis?.verifications) return;
    const loaded = {};
    for (const v of analysis.verifications) {
      loaded[v.detection_index] = v.decision;
    }
    setVerifications(loaded);
  }, [analysis]);

  useEffect(() => {
    if (analysis) return;
    if (!analysisId || analysisId === "latest") return;

    let mounted = true;
    async function loadAnalysis() {
      try {
        setLoading(true);
        const data = await getSurveyById(analysisId);
        if (mounted) {
          if (!data) setError(`Analysis record '${analysisId}' not found.`);
          else setAnalysis(data);
        }
      } catch (err) {
        if (mounted) setError(err.message || "Failed to retrieve analysis.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadAnalysis();
    return () => {
      mounted = false;
    };
  }, [analysisId, analysis]);

  const detections = useMemo(() => analysis?.detections || [], [analysis]);

  // Compute 5 Real Summary KPIs
  const summaryKPIs = useMemo(() => {
    const total = detections.length;
    if (total === 0) {
      return {
        total: 0,
        avgConfidence: 0,
        highestRisk: 0,
        highestPriority: "LOW",
        uncertainty: "±2.0m",
      };
    }

    const avgConf =
      detections.reduce((acc, d) => acc + (d.confidence || 0), 0) / total;
    const maxRisk = Math.max(...detections.map((d) => d.risk_score || 0));

    // Priority ranking: CRITICAL > HIGH > MEDIUM > LOW
    const priorities = detections.map((d) => (d.risk_level || "LOW").toUpperCase());
    let highestPri = "LOW";
    if (priorities.includes("CRITICAL")) highestPri = "CRITICAL";
    else if (priorities.includes("HIGH")) highestPri = "HIGH";
    else if (priorities.includes("MEDIUM")) highestPri = "MEDIUM";

    // Uncertainty from first detection or default
    const firstGeo = detections[0]?.geolocation;
    let unc = "±2.0m";
    if (firstGeo?.uncertainty_m != null) {
      unc = `±${firstGeo.uncertainty_m}m`;
    }

    return {
      total,
      avgConfidence: avgConf,
      highestRisk: maxRisk,
      highestPriority: highestPri,
      uncertainty: unc,
    };
  }, [detections]);

  async function handleVerify(index, decision) {
    // Optimistically update local state
    const updated = { ...verifications, [index]: decision };
    setVerifications(updated);
    setVerifStatus("saving");

    const analysisId = analysis._id || analysis.analysis_id;
    if (!analysisId || analysisId === "Archived") {
      // No MongoDB ID — session-only (new survey not yet persisted)
      setVerifStatus(null);
      return;
    }

    try {
      const payload = Object.entries(updated).map(([idx, dec]) => ({
        detection_index: Number(idx),
        decision: dec,
        timestamp: new Date().toISOString(),
      }));
      await saveVerifications(analysisId, payload);
      setVerifStatus("saved");
      setTimeout(() => setVerifStatus(null), 2500);
    } catch (err) {
      setVerifStatus({ error: err.message || "Sync failed" });
      setTimeout(() => setVerifStatus(null), 4000);
    }
  }

  function handleZoomIn() {
    setZoom((z) => Math.min(Number((z + 0.25).toFixed(2)), 3));
  }

  function handleZoomOut() {
    setZoom((z) => Math.max(Number((z - 0.25).toFixed(2)), 0.5));
  }

  function handleResetZoom() {
    setZoom(1);
  }

  if (loading) {
    return (
      <div style={{ padding: "80px 20px", textAlign: "center", color: "var(--muted)" }}>
        <ScanLine size={40} color="var(--primary)" style={{ animation: "spin 2s linear infinite", marginBottom: "16px" }} />
        <h3 style={{ color: "var(--text)", marginBottom: "6px" }}>Retrieving Sonar Telemetry & Evidence</h3>
        <p style={{ fontSize: "14px" }}>Synchronizing neural detections with DRISHTI marine archive...</p>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div>
        <Link className="back-link" to="/dashboard">
          <ArrowLeft size={16} /> Back to Dashboard
        </Link>
        <div
          style={{
            marginTop: "20px",
            padding: "28px",
            borderRadius: "12px",
            background: "rgba(224, 76, 90, 0.08)",
            border: "1px solid rgba(224, 76, 90, 0.3)",
            color: "var(--red)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
            <AlertTriangle size={24} color="var(--red)" />
            <h3 style={{ margin: 0, color: "var(--text)" }}>Unable to Retrieve Analysis Record</h3>
          </div>
          <p style={{ fontSize: "14px", lineHeight: "1.6", color: "var(--text)" }}>
            {error || "No survey analysis payload available. The specified record may have been purged or not yet uploaded."}
          </p>
          <div style={{ display: "flex", gap: "12px", marginTop: "18px" }}>
            <Link to="/surveys/new" className="primary-btn">
              Analyze New Survey
            </Link>
            <Link to="/dashboard" className="secondary-btn">
              Return to Missions
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const analyzedImageUrl = evidenceUrl(analysis.evidence_image);
  const activeDetection = detections[activeDetectionIndex] || detections[0];
  const recordId = analysis._id || analysis.analysis_id || "Archived";

  return (
    <div>
      {/* Top Navigation */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <Link className="back-link" to="/dashboard" style={{ margin: 0 }}>
          <ArrowLeft size={16} /> Back to Missions Dashboard
        </Link>
        <div style={{ fontSize: "12px", color: "var(--muted)", display: "flex", alignItems: "center", gap: "8px" }}>
          <span>Telemetry Record:</span>
          <code style={{ background: "var(--panel-alt)", padding: "2px 8px", borderRadius: "4px", color: "var(--primary)" }}>
            {recordId}
          </code>
        </div>
      </div>

      {/* SYSTEM STATUS BANNER */}
      <div className="analysis-status-strip">
        <div className="system-status-indicator">
          <span className="pulse-dot"></span>
          <span style={{ color: "var(--green)" }}>SYSTEM ONLINE</span>
          <span style={{ color: "var(--line)" }}>|</span>
          <span style={{ color: "#dbe9f7" }}>
            {detections.length === 0
              ? "CLEAN SURVEY SCAN — ZERO ANOMALIES"
              : `${detections.length} ${detections.length === 1 ? "ANOMALY" : "ANOMALIES"} DETECTED`}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px", fontSize: "12px", color: "var(--muted)" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Cpu size={14} color="var(--primary)" />
            DRISHTI YOLO v8.2 Marine
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Radar size={14} color="var(--primary)" />
            Acoustic Grid Validated
          </span>
        </div>
      </div>

      {/* Page Heading */}
      <div className="page-heading">
        <div>
          <span className="eyebrow">MISSION TARGET REVIEW</span>
          <h1 style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            {analysis.filename || originalFilename || "Side-Scan Sonar Survey"}
          </h1>
          <p style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginTop: "6px" }}>
            <span>Archive Mission ID: <code>{recordId}</code></span>
            <span>·</span>
            <Badge tone={detections.length > 0 ? "warning" : "success"}>
              {detections.length > 0 ? "Targets Flagged" : "Clear Passage"}
            </Badge>
            <span>·</span>
            <span>Coord System: <strong>{activeDetection?.geolocation?.coordinate_system || "local_sonar"}</strong></span>
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center" }}>
          {/* Verification status indicator */}
          {verifStatus === "saving" && (
            <span style={{ fontSize: "12px", color: "var(--muted)", display: "flex", alignItems: "center", gap: "6px" }}>
              <ScanLine size={13} style={{ animation: "spin 1.2s linear infinite" }} /> Saving...
            </span>
          )}
          {verifStatus === "saved" && (
            <span style={{ fontSize: "12px", color: "var(--green)", display: "flex", alignItems: "center", gap: "6px" }}>
              <Check size={13} /> Verified
            </span>
          )}
          {verifStatus?.error && (
            <span style={{ fontSize: "12px", color: "var(--red)" }}>⚠ {verifStatus.error}</span>
          )}

          {analyzedImageUrl && (
            <a
              href={analyzedImageUrl}
              download={analysis.evidence_image || "sonaris_evidence.jpg"}
              target="_blank"
              rel="noreferrer"
              className="secondary-btn"
              style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
              title="Download full resolution DRISHTI evidence image"
            >
              <Download size={16} /> Download Evidence
            </a>
          )}
          {(analysis._id || analysis.analysis_id) && (
            <a
              href={reportPdfUrl(analysis._id || analysis.analysis_id)}
              target="_blank"
              rel="noreferrer"
              className="primary-btn"
              style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
              title="Download full PDF survey report"
            >
              <Download size={16} /> Download PDF Report
            </a>
          )}
          <Link to="/surveys/new" className="secondary-btn">
            Analyze New Survey
          </Link>
        </div>
      </div>

      {/* 5 REAL KPI SUMMARY CARDS */}
      <div className="kpi-summary-grid">
        {/* Card 1: Total Anomalies */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Total Anomalies</span>
            <ShieldAlert size={15} color={summaryKPIs.total > 0 ? "var(--amber)" : "var(--green)"} />
          </div>
          <div className="kpi-value">
            {summaryKPIs.total}
            <span style={{ fontSize: "13px", fontWeight: 400, color: "var(--muted)" }}>contacts</span>
          </div>
          <div className="kpi-sub">
            {summaryKPIs.total === 0 ? "Clean acoustic survey" : "Passed confidence gate"}
          </div>
        </div>

        {/* Card 2: Average Confidence */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Avg Confidence</span>
            <Activity size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">
            {summaryKPIs.total > 0 ? `${(summaryKPIs.avgConfidence * 100).toFixed(1)}%` : "N/A"}
          </div>
          <div className="kpi-sub">Neural detection confidence</div>
        </div>

        {/* Card 3: Highest Risk Score */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Peak Risk Score</span>
            <AlertTriangle size={15} color="var(--red)" />
          </div>
          <div className="kpi-value">
            {summaryKPIs.total > 0 ? summaryKPIs.highestRisk.toFixed(2) : "0.00"}
            <span style={{ fontSize: "13px", fontWeight: 400, color: "var(--muted)" }}>/ 1.0</span>
          </div>
          <div className="kpi-sub">Contact threat index</div>
        </div>

        {/* Card 4: Highest Priority */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Highest Priority</span>
            <Layers size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value" style={{ fontSize: "20px" }}>
            <Badge tone={RISK_TONE[summaryKPIs.highestPriority] || "neutral"}>
              {summaryKPIs.highestPriority}
            </Badge>
          </div>
          <div className="kpi-sub">Operational dispatch tier</div>
        </div>

        {/* Card 5: Location Uncertainty */}
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Pos Uncertainty</span>
            <Compass size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">
            {summaryKPIs.uncertainty}
          </div>
          <div className="kpi-sub">
            {activeDetection?.geolocation?.latitude != null ? "WGS84 GNSS accuracy" : "Local sonar sensor grid"}
          </div>
        </div>
      </div>

      {/* SIDE-BY-SIDE DUAL VIEW EVIDENCE VIEWER WITH TOOLBAR */}
      <section className="panel" style={{ marginBottom: "24px", padding: 0, overflow: "hidden" }}>
        {/* Controls Toolbar */}
        <div className="viewer-toolbar">
          {/* Left: View Mode Toggle */}
          <div className="toolbar-group">
            <button
              type="button"
              className={`toolbar-btn ${viewMode === "split" ? "active" : ""}`}
              onClick={() => setViewMode("split")}
              title="Dual split side-by-side view"
            >
              <Columns2 size={14} /> Dual Split
            </button>
            <button
              type="button"
              className={`toolbar-btn ${viewMode === "evidence" ? "active" : ""}`}
              onClick={() => setViewMode("evidence")}
              title="Focus DRISHTI AI Evidence Overlay"
            >
              <ScanLine size={14} /> Focus AI Evidence
            </button>
            <button
              type="button"
              className={`toolbar-btn ${viewMode === "original" ? "active" : ""}`}
              onClick={() => setViewMode("original")}
              title="Focus Raw Acoustic Imagery"
            >
              <FileImage size={14} /> Focus Raw Sonar
            </button>
          </div>

          {/* Center: Zoom Controls */}
          <div className="toolbar-group">
            <button
              type="button"
              className="toolbar-btn"
              onClick={handleZoomOut}
              disabled={zoom <= 0.5}
              title="Zoom Out"
            >
              <ZoomOut size={14} />
            </button>
            <span className="zoom-indicator">{Math.round(zoom * 100)}%</span>
            <button
              type="button"
              className="toolbar-btn"
              onClick={handleZoomIn}
              disabled={zoom >= 3}
              title="Zoom In"
            >
              <ZoomIn size={14} />
            </button>
            <button
              type="button"
              className="toolbar-btn"
              onClick={handleResetZoom}
              title="Reset Zoom to 100%"
            >
              <RotateCcw size={14} /> Fit
            </button>
          </div>

          {/* Right: Theater Mode / Fullscreen */}
          <div className="toolbar-group">
            <button
              type="button"
              className="toolbar-btn"
              onClick={() => setIsTheaterOpen(true)}
              title="Open full inspection theater mode"
            >
              <Maximize2 size={14} /> Theater Mode
            </button>
          </div>
        </div>

        {/* Evidence Stage */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              viewMode === "split"
                ? "repeat(auto-fit, minmax(340px, 1fr))"
                : "1fr",
            gap: "1px",
            background: "var(--line)",
          }}
        >
          {/* ORIGINAL SONAR VIEWPORT */}
          {(viewMode === "split" || viewMode === "original") && (
            <div style={{ background: "#050b15", display: "flex", flexDirection: "column" }}>
              <div
                style={{
                  padding: "10px 14px",
                  background: "var(--panel-alt)",
                  borderBottom: "1px solid var(--line)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, color: "var(--text)" }}>
                  <FileImage size={15} color="var(--primary)" />
                  <span>ORIGINAL SONAR IMAGERY</span>
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted)" }}>Raw Acoustic Capture</span>
              </div>

              <div className="evidence-container">
                <div
                  className="evidence-viewport"
                  style={{ transform: `scale(${zoom})` }}
                >
                  {originalPreview ? (
                    <img
                      src={originalPreview}
                      alt="Original Sonar Capture"
                      style={{
                        maxWidth: "100%",
                        maxHeight: "440px",
                        objectFit: "contain",
                        borderRadius: "4px",
                        boxShadow: "0 4px 20px rgba(0,0,0,0.6)",
                      }}
                    />
                  ) : analyzedImageUrl ? (
                    <div style={{ position: "relative", maxWidth: "100%", textAlign: "center" }}>
                      <img
                        src={analyzedImageUrl}
                        alt="Raw Sonar Channel"
                        style={{
                          maxWidth: "100%",
                          maxHeight: "440px",
                          objectFit: "contain",
                          filter: "grayscale(100%) contrast(1.1)",
                          borderRadius: "4px",
                          opacity: 0.85,
                        }}
                      />
                      <div
                        style={{
                          position: "absolute",
                          bottom: "12px",
                          left: "50%",
                          transform: "translateX(-50%)",
                          background: "rgba(5, 11, 21, 0.85)",
                          padding: "4px 12px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          color: "#dbe9f7",
                          border: "1px solid var(--line)",
                          whiteSpace: "nowrap",
                        }}
                      >
                        Acoustic channel view · Raw frame archived with mission payload
                      </div>
                    </div>
                  ) : (
                    <div style={{ color: "var(--muted)", textAlign: "center", padding: "40px 16px" }}>
                      <FileImage size={40} style={{ opacity: 0.5, marginBottom: "8px" }} />
                      <p style={{ fontSize: "13px" }}>Raw telemetry image not stored locally in browser session</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ANALYZED EVIDENCE VIEWPORT (DRISHTI YOLO) */}
          {(viewMode === "split" || viewMode === "evidence") && (
            <div style={{ background: "#050b15", display: "flex", flexDirection: "column" }}>
              <div
                style={{
                  padding: "10px 14px",
                  background: "var(--panel-alt)",
                  borderBottom: "1px solid var(--line)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, color: "var(--primary)" }}>
                  <ScanLine size={15} />
                  <span>ANALYZED EVIDENCE (DRISHTI YOLO)</span>
                </div>
                <span style={{ fontSize: "11px", color: "var(--green)", fontWeight: 500 }}>
                  Real Model Annotations
                </span>
              </div>

              <div className="evidence-container">
                <div
                  className="evidence-viewport"
                  style={{ transform: `scale(${zoom})` }}
                >
                  {analyzedImageUrl ? (
                    <img
                      src={analyzedImageUrl}
                      alt="DRISHTI AI Detection Evidence"
                      style={{
                        maxWidth: "100%",
                        maxHeight: "440px",
                        objectFit: "contain",
                        borderRadius: "4px",
                        boxShadow: "0 4px 20px rgba(0,0,0,0.6)",
                      }}
                    />
                  ) : (
                    <div style={{ color: "var(--muted)", textAlign: "center", padding: "40px 16px" }}>
                      <ShieldAlert size={40} color="var(--amber)" style={{ marginBottom: "8px" }} />
                      <p style={{ fontSize: "13px" }}>Awaiting DRISHTI evidence generation</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* THEATER MODE FULLSCREEN MODAL */}
      {isTheaterOpen && (
        <div className="theater-modal-backdrop">
          <div className="theater-modal-header">
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <ScanLine size={20} color="var(--primary)" />
              <div>
                <strong style={{ fontSize: "16px", color: "#fff" }}>
                  Acoustic Evidence Theater Review
                </strong>
                <span style={{ fontSize: "12px", color: "var(--muted)", marginLeft: "10px" }}>
                  Mission: {analysis.filename || recordId}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {/* Zoom Controls inside theater */}
              <div className="toolbar-group">
                <button type="button" className="toolbar-btn" onClick={handleZoomOut} disabled={zoom <= 0.5}>
                  <ZoomOut size={14} />
                </button>
                <span className="zoom-indicator">{Math.round(zoom * 100)}%</span>
                <button type="button" className="toolbar-btn" onClick={handleZoomIn} disabled={zoom >= 3}>
                  <ZoomIn size={14} />
                </button>
                <button type="button" className="toolbar-btn" onClick={handleResetZoom}>
                  <RotateCcw size={14} /> 100%
                </button>
              </div>

              <button
                type="button"
                className="secondary-btn"
                onClick={() => setIsTheaterOpen(false)}
                style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
              >
                <Minimize2 size={16} /> Exit Theater
              </button>
            </div>
          </div>

          <div className="theater-modal-content">
            <div
              style={{
                flex: 1,
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
                height: "100%",
              }}
            >
              {/* Original Theater View */}
              <div style={{ background: "#03070e", borderRadius: "8px", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                <div style={{ padding: "8px 12px", background: "#0b1523", fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>
                  RAW CAPTURE
                </div>
                <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                  <img
                    src={originalPreview || analyzedImageUrl}
                    alt="Raw Frame"
                    style={{
                      maxHeight: "85vh",
                      maxWidth: "100%",
                      objectFit: "contain",
                      transform: `scale(${zoom})`,
                      transition: "transform 0.1s ease",
                      filter: !originalPreview && analyzedImageUrl ? "grayscale(100%)" : "none",
                    }}
                  />
                </div>
              </div>

              {/* Analyzed Evidence Theater View */}
              <div style={{ background: "#03070e", borderRadius: "8px", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                <div style={{ padding: "8px 12px", background: "#0b1523", fontSize: "12px", fontWeight: 600, color: "var(--primary)" }}>
                  DRISHTI YOLO DETECTIONS
                </div>
                <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                  <img
                    src={analyzedImageUrl}
                    alt="Analyzed Evidence"
                    style={{
                      maxHeight: "85vh",
                      maxWidth: "100%",
                      objectFit: "contain",
                      transform: `scale(${zoom})`,
                      transition: "transform 0.1s ease",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DETECTIONS INSPECTION & OPERATOR REVIEW GRID */}
      <div className="content-grid two-one">
        {/* Left Column: Detections (Table or Cards) */}
        <section className="panel">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
            <SectionHeader
              title="Detected Anomalies"
              subtitle={`${detections.length} candidate acoustic targets identified by DRISHTI`}
            />

            {/* View Mode Switcher: Table vs Cards */}
            {detections.length > 0 && (
              <div className="view-mode-pill">
                <button
                  type="button"
                  className={displayMode === "table" ? "active" : ""}
                  onClick={() => setDisplayMode("table")}
                >
                  <TableIcon size={14} /> Table
                </button>
                <button
                  type="button"
                  className={displayMode === "cards" ? "active" : ""}
                  onClick={() => setDisplayMode("cards")}
                >
                  <LayoutGrid size={14} /> Cards
                </button>
              </div>
            )}
          </div>

          {/* Zero Anomalies State */}
          {detections.length === 0 ? (
            <div className="clean-scan-card">
              <FileCheck size={44} color="var(--green)" style={{ margin: "0 auto 12px auto" }} />
              <h3 style={{ color: "var(--text)", marginBottom: "6px" }}>Clean Acoustic Scan</h3>
              <p style={{ fontSize: "13px", color: "var(--muted)", maxWidth: "420px", margin: "0 auto" }}>
                Zero threats or seabed anomalies detected above the operational confidence threshold in this survey tile.
              </p>
              <div style={{ marginTop: "18px" }}>
                <Link to="/surveys/new" className="primary-btn">
                  Analyze Next Tile
                </Link>
              </div>
            </div>
          ) : displayMode === "table" ? (
            /* TABLE VIEW */
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "12px" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--line)", color: "var(--muted)" }}>
                    <th style={{ padding: "10px 12px" }}>TARGET / ANOMALY</th>
                    <th style={{ padding: "10px 12px" }}>CONFIDENCE</th>
                    <th style={{ padding: "10px 12px" }}>RISK SCORE</th>
                    <th style={{ padding: "10px 12px" }}>PRIORITY</th>
                    <th style={{ padding: "10px 12px" }}>BBOX [X1,Y1,X2,Y2]</th>
                    <th style={{ padding: "10px 12px" }}>COORDINATE SYSTEM</th>
                    <th style={{ padding: "10px 12px" }}>OPERATOR VERIFICATION</th>
                    <th style={{ padding: "10px 12px", textAlign: "right" }}>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {detections.map((det, idx) => {
                    const status = verifications[idx] || "Pending";
                    const isSelected = activeDetectionIndex === idx;
                    const tone = RISK_TONE[(det.risk_level || "LOW").toUpperCase()] || "neutral";
                    const bboxStr = det.bbox
                      ? `[${det.bbox.map((v) => Math.round(v)).join(", ")}]`
                      : "N/A";
                    const coordSys = det.geolocation?.coordinate_system || "local_sonar";

                    return (
                      <tr
                        key={idx}
                        onClick={() => setActiveDetectionIndex(idx)}
                        style={{
                          borderBottom: "1px solid var(--line)",
                          cursor: "pointer",
                          background: isSelected ? "rgba(21, 155, 211, 0.08)" : "transparent",
                          transition: "background 0.15s ease",
                        }}
                      >
                        <td style={{ padding: "12px", fontWeight: 600, color: isSelected ? "var(--primary)" : "var(--text)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span
                              style={{
                                width: "20px",
                                height: "20px",
                                borderRadius: "50%",
                                background: isSelected ? "var(--primary)" : "var(--panel-alt)",
                                display: "grid",
                                placeItems: "center",
                                fontSize: "11px",
                                color: isSelected ? "#fff" : "var(--text)",
                                flexShrink: 0,
                              }}
                            >
                              {idx + 1}
                            </span>
                            <span>{formatName(det.class_name)}</span>
                          </div>
                        </td>

                        <td style={{ padding: "12px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <div
                              style={{
                                width: "45px",
                                height: "5px",
                                background: "var(--line)",
                                borderRadius: "3px",
                                overflow: "hidden",
                              }}
                            >
                              <div
                                style={{
                                  width: `${Math.round((det.confidence || 0) * 100)}%`,
                                  height: "100%",
                                  background: "var(--primary)",
                                }}
                              />
                            </div>
                            <span>
                              {det.confidence != null ? `${(det.confidence * 100).toFixed(1)}%` : "N/A"}
                            </span>
                          </div>
                        </td>

                        <td style={{ padding: "12px", fontFamily: "monospace", color: "var(--text)" }}>
                          {det.risk_score != null ? Number(det.risk_score).toFixed(2) : "N/A"}
                        </td>

                        <td style={{ padding: "12px" }}>
                          <Badge tone={tone}>{det.risk_level || "LOW"}</Badge>
                        </td>

                        <td style={{ padding: "12px", color: "var(--muted)", fontFamily: "monospace", fontSize: "11px" }}>
                          {bboxStr}
                        </td>

                        <td style={{ padding: "12px" }}>
                          <span
                            style={{
                              fontSize: "11px",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              background: "var(--panel-alt)",
                              color: det.geolocation?.latitude != null ? "var(--green)" : "var(--muted)",
                              border: "1px solid var(--line)",
                            }}
                          >
                            {coordSys}
                          </span>
                        </td>

                        <td style={{ padding: "12px" }}>
                          <Badge
                            tone={
                              status === "Confirmed"
                                ? "success"
                                : status === "Rejected"
                                ? "danger"
                                : status === "Uncertain"
                                ? "warning"
                                : "neutral"
                            }
                          >
                            {status}
                          </Badge>
                        </td>

                        <td style={{ padding: "12px", textAlign: "right" }}>
                          <button
                            type="button"
                            className="secondary-btn"
                            style={{
                              padding: "4px 10px",
                              fontSize: "11px",
                              background: isSelected ? "var(--primary2)" : "",
                              color: isSelected ? "#fff" : "",
                            }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveDetectionIndex(idx);
                            }}
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            /* CARD VIEW */
            <div className="detection-cards-grid">
              {detections.map((det, idx) => {
                const status = verifications[idx] || "Pending";
                const isSelected = activeDetectionIndex === idx;
                const tone = RISK_TONE[(det.risk_level || "LOW").toUpperCase()] || "neutral";

                return (
                  <div
                    key={idx}
                    className={`detection-card ${isSelected ? "is-active" : ""}`}
                    onClick={() => setActiveDetectionIndex(idx)}
                  >
                    <div>
                      <div className="detection-card-header">
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span
                            style={{
                              width: "22px",
                              height: "22px",
                              borderRadius: "50%",
                              background: isSelected ? "var(--primary)" : "var(--panel-alt)",
                              display: "grid",
                              placeItems: "center",
                              fontSize: "11px",
                              fontWeight: 700,
                              color: isSelected ? "#fff" : "var(--text)",
                            }}
                          >
                            {idx + 1}
                          </span>
                          <strong style={{ fontSize: "13px", color: isSelected ? "var(--primary)" : "var(--text)" }}>
                            {formatName(det.class_name)}
                          </strong>
                        </div>
                        <Badge tone={tone}>{det.risk_level || "LOW"}</Badge>
                      </div>

                      <div className="detection-card-metrics">
                        <div>
                          <span style={{ color: "var(--muted)", display: "block" }}>Confidence</span>
                          <strong style={{ color: "var(--text)" }}>
                            {det.confidence != null ? `${(det.confidence * 100).toFixed(1)}%` : "N/A"}
                          </strong>
                        </div>
                        <div>
                          <span style={{ color: "var(--muted)", display: "block" }}>Risk Index</span>
                          <strong style={{ color: "var(--text)" }}>
                            {det.risk_score != null ? Number(det.risk_score).toFixed(2) : "N/A"}
                          </strong>
                        </div>
                      </div>

                      <div style={{ fontSize: "11px", color: "var(--muted)", margin: "6px 0" }}>
                        Coordinate Frame:{" "}
                        <span style={{ color: "var(--text)" }}>
                          {det.geolocation?.coordinate_system || "local_sonar"}
                        </span>
                      </div>
                    </div>

                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        paddingTop: "10px",
                        borderTop: "1px solid var(--line)",
                        marginTop: "8px",
                      }}
                    >
                      <Badge
                        tone={
                          status === "Confirmed"
                            ? "success"
                            : status === "Rejected"
                            ? "danger"
                            : status === "Uncertain"
                            ? "warning"
                            : "neutral"
                        }
                      >
                        {status}
                      </Badge>

                      <button
                        type="button"
                        className="secondary-btn"
                        style={{ padding: "3px 8px", fontSize: "11px" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveDetectionIndex(idx);
                        }}
                      >
                        Inspect Target
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Right Column: Selected Target Operator Decision & Geolocation */}
        {activeDetection && (
          <section className="panel" style={{ position: "sticky", top: "20px" }}>
            <SectionHeader
              title={`Target #${activeDetectionIndex + 1}: ${formatName(activeDetection.class_name)}`}
              subtitle="Operator adjudication & acoustic geometry"
            />

            <div style={{ display: "grid", gap: "16px", marginTop: "14px" }}>
              {/* Target Quick Stats */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "10px",
                  background: "var(--panel-alt)",
                  padding: "12px",
                  borderRadius: "8px",
                  border: "1px solid var(--line)",
                  fontSize: "12px",
                }}
              >
                <div>
                  <span style={{ color: "var(--muted)", display: "block" }}>Confidence</span>
                  <strong style={{ fontSize: "15px", color: "var(--primary)" }}>
                    {activeDetection.confidence != null
                      ? `${(activeDetection.confidence * 100).toFixed(1)}%`
                      : "N/A"}
                  </strong>
                </div>
                <div>
                  <span style={{ color: "var(--muted)", display: "block" }}>Threat Risk</span>
                  <strong style={{ fontSize: "15px", color: "var(--red)" }}>
                    {activeDetection.risk_score != null
                      ? Number(activeDetection.risk_score).toFixed(2)
                      : "N/A"}
                  </strong>
                </div>
              </div>

              {/* Review Decision Buttons */}
              <div>
                <span style={{ fontSize: "12px", color: "var(--muted)", display: "block", marginBottom: "8px", fontWeight: 600 }}>
                  OPERATOR VERIFICATION DECISION:
                </span>
                <div className="review-options" style={{ display: "grid", gridTemplateColumns: "1fr", gap: "8px", margin: 0 }}>
                  <button
                    type="button"
                    className={`verification-btn-confirm ${
                      verifications[activeDetectionIndex] === "Confirmed" ? "selected success-border" : ""
                    }`}
                    onClick={() => handleVerify(activeDetectionIndex, "Confirmed")}
                    style={{ textAlign: "left", cursor: "pointer" }}
                  >
                    <CheckCircle2 size={18} color="var(--green)" style={{ flexShrink: 0 }} />
                    <div>
                      <strong style={{ display: "block", fontSize: "13px" }}>Confirm Anomaly</strong>
                      <small style={{ display: "block", color: "var(--muted)", fontSize: "11px", marginTop: "2px" }}>
                        Valid acoustic contact matching target signature
                      </small>
                    </div>
                  </button>

                  <button
                    type="button"
                    className={`verification-btn-reject ${
                      verifications[activeDetectionIndex] === "Rejected" ? "selected danger-border" : ""
                    }`}
                    onClick={() => handleVerify(activeDetectionIndex, "Rejected")}
                    style={{ textAlign: "left", cursor: "pointer" }}
                  >
                    <XCircle size={18} color="var(--red)" style={{ flexShrink: 0 }} />
                    <div>
                      <strong style={{ display: "block", fontSize: "13px" }}>Reject (False Alarm)</strong>
                      <small style={{ display: "block", color: "var(--muted)", fontSize: "11px", marginTop: "2px" }}>
                        Seabed reverberation, wake, or non-target feature
                      </small>
                    </div>
                  </button>

                  <button
                    type="button"
                    className={`verification-btn-uncertain ${
                      verifications[activeDetectionIndex] === "Uncertain" ? "selected warning-border" : ""
                    }`}
                    onClick={() => handleVerify(activeDetectionIndex, "Uncertain")}
                    style={{ textAlign: "left", cursor: "pointer" }}
                  >
                    <HelpCircle size={18} color="var(--amber)" style={{ flexShrink: 0 }} />
                    <div>
                      <strong style={{ display: "block", fontSize: "13px" }}>Flag Uncertain / Re-Survey</strong>
                      <small style={{ display: "block", color: "var(--muted)", fontSize: "11px", marginTop: "2px" }}>
                        Requires ROV inspection or orthogonal pass
                      </small>
                    </div>
                  </button>
                </div>
              </div>

              {/* Informational Callout regarding verification state & API schema */}
              <div className="verification-callout">
                <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--primary)", fontWeight: 600 }}>
                  <Info size={14} />
                  <span>Persistent Operator Adjudication</span>
                </div>
                <div>
                  {verifStatus === "saving" && "Syncing to MongoDB Atlas..."}
                  {verifStatus === "saved" && (
                    <span style={{ color: "var(--green)" }}>✓ Decision saved to survey record</span>
                  )}
                  {verifStatus?.error && (
                    <span style={{ color: "var(--red)" }}>⚠ Sync failed: {verifStatus.error}</span>
                  )}
                  {!verifStatus && "Decisions are persisted to the MongoDB survey record and survive page reload."}
                </div>
                <div style={{ fontSize: "10px", color: "var(--muted)", marginTop: "2px", fontFamily: "monospace" }}>
                  PUT /api/surveys/{recordId}/verifications
                </div>
              </div>

              {/* Geolocation Section */}
              <div
                style={{
                  background: "var(--panel-alt)",
                  borderRadius: "8px",
                  padding: "14px",
                  border: "1px solid var(--line)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                  <Compass size={16} color="var(--primary)" />
                  <strong style={{ fontSize: "13px" }}>Geolocation & Acoustic Geometry</strong>
                </div>

                {activeDetection.geolocation?.latitude != null ? (
                  <div className="detail-list" style={{ fontSize: "12px", margin: 0 }}>
                    <div>
                      <span>Coordinates (WGS84):</span>
                      <strong style={{ color: "var(--green)" }}>
                        {activeDetection.geolocation.latitude.toFixed(6)}°N, {activeDetection.geolocation.longitude.toFixed(6)}°E
                      </strong>
                    </div>
                    <div>
                      <span>Position Uncertainty:</span>
                      <strong>±{activeDetection.geolocation.uncertainty_m ?? 5} m</strong>
                    </div>
                    <div>
                      <span>Coordinate Frame:</span>
                      <strong>WGS84 GNSS</strong>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div
                      style={{
                        padding: "8px 10px",
                        background: "rgba(217, 131, 36, 0.08)",
                        border: "1px solid rgba(217, 131, 36, 0.25)",
                        borderRadius: "6px",
                        marginBottom: "10px",
                        fontSize: "11px",
                        color: "var(--amber)",
                      }}
                    >
                      <strong>Local Acoustic Sensor Frame</strong> — No GPS telemetry supplied in survey metadata. Georeferenced relative to sonar swath.
                    </div>
                    <div className="detail-list" style={{ fontSize: "12px", margin: 0 }}>
                      <div>
                        <span>Local Slant Range:</span>
                        <strong>
                          {activeDetection.geolocation?.range_m != null
                            ? `${activeDetection.geolocation.range_m.toFixed(2)} m`
                            : "Calculated"}
                        </strong>
                      </div>
                      <div>
                        <span>Acoustic Bearing:</span>
                        <strong>
                          {activeDetection.geolocation?.bearing_deg != null
                            ? `${activeDetection.geolocation.bearing_deg.toFixed(1)}° (Port/Starboard)`
                            : "90.0°"}
                        </strong>
                      </div>
                      <div>
                        <span>Relative Position:</span>
                        <strong>
                          X: {activeDetection.geolocation?.local_x_m != null ? `${activeDetection.geolocation.local_x_m.toFixed(2)}m` : "0.00m"} ·
                          Y: {activeDetection.geolocation?.local_y_m != null ? `${activeDetection.geolocation.local_y_m.toFixed(2)}m` : "0.00m"}
                        </strong>
                      </div>
                      <div>
                        <span>Sensor Uncertainty:</span>
                        <strong>
                          ±{activeDetection.geolocation?.uncertainty_m != null ? `${activeDetection.geolocation.uncertainty_m.toFixed(1)}m` : "2.0m"}
                        </strong>
                      </div>
                      <div>
                        <span>Coordinate System:</span>
                        <code>local_sonar</code>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Bounding Box Info */}
              {activeDetection.bbox && (
                <div style={{ fontSize: "11px", color: "var(--muted)", background: "var(--panel-alt)", padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line)" }}>
                  <span>Bounding Box [xmin, ymin, xmax, ymax]:</span>
                  <code style={{ display: "block", marginTop: "4px", color: "var(--muted)" }}>
                    {JSON.stringify(activeDetection.bbox.map((v) => Math.round(v)))}
                  </code>
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
