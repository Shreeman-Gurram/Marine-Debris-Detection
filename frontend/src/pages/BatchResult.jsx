// src/pages/BatchResult.jsx
// SONARIS Persistent Anomaly Tracking & Batch Analysis Results
import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Layers,
  ScanLine,
  ShieldAlert,
  ChevronRight,
  Clock,
  Compass,
  MapPin,
  CheckCircle2,
  FileImage,
  ExternalLink,
  Info,
  Maximize2,
  Eye,
  Activity,
  AlertTriangle,
  X,
  Target,
  GitMerge,
  Filter,
} from "lucide-react";
import SectionHeader from "../components/SectionHeader";
import Badge from "../components/Badge";
import { getBatch, evidenceUrl } from "../services/api";
import { RISK_TONE } from "../utils/constants";

function formatClassName(name) {
  if (!name) return "Unknown Anomaly";
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function BatchResult() {
  const { batchId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  // Prefer state passed from NewSurvey, otherwise fetch by ID from MongoDB
  const [batch, setBatch] = useState(location.state?.batch || null);
  const [loading, setLoading] = useState(!batch && !!batchId);
  const [error, setError] = useState(null);

  // Selected track for detail drawer
  const [selectedTrack, setSelectedTrack] = useState(null);

  // Active frame filter for timeline / viewer
  const [activeFrameIndex, setActiveFrameIndex] = useState(null);

  useEffect(() => {
    if (batch) return;
    if (!batchId) return;

    async function fetchBatchData() {
      try {
        setLoading(true);
        const data = await getBatch(batchId);
        if (!data) {
          setError(`Batch "${batchId}" not found in database archives.`);
        } else {
          setBatch(data);
        }
      } catch (err) {
        console.error("Failed to load batch result:", err);
        setError(err.message || "Failed to retrieve batch intelligence from database.");
      } finally {
        setLoading(false);
      }
    }

    fetchBatchData();
  }, [batchId, batch]);

  // If a track is selected, keep it updated if batch changes
  useEffect(() => {
    if (batch?.tracks && batch.tracks.length > 0 && !selectedTrack) {
      // Don't auto-open drawer, but make first track available
    }
  }, [batch, selectedTrack]);

  if (loading) {
    return (
      <div style={{ padding: "80px 20px", textAlign: "center" }}>
        <ScanLine
          size={42}
          color="var(--primary)"
          style={{ animation: "spin 2s linear infinite", margin: "0 auto 16px auto" }}
        />
        <h2 style={{ fontSize: "20px", margin: "0 0 8px 0" }}>Retrieving Batch Analysis</h2>
        <p style={{ color: "var(--muted)", fontSize: "14px" }}>
          Querying MongoDB archives for persistent anomaly tracking session...
        </p>
      </div>
    );
  }

  if (error || !batch) {
    return (
      <div style={{ maxWidth: "800px", margin: "40px auto", padding: "0 20px" }}>
        <Link to="/surveys/new" className="back-link">
          <ArrowLeft size={16} /> Return to Mission Planning
        </Link>
        <div
          className="panel"
          style={{
            padding: "40px 30px",
            textAlign: "center",
            border: "1px solid var(--red-border)",
            background: "var(--red-light)",
          }}
        >
          <AlertTriangle size={36} color="var(--red)" style={{ margin: "0 auto 14px auto" }} />
          <h2 style={{ fontSize: "18px", color: "var(--red-text)", margin: "0 0 8px 0" }}>
            Batch Retrieval Failed
          </h2>
          <p style={{ color: "var(--red-text)", fontSize: "13.5px", margin: "0 0 20px 0" }}>
            {error || "Unable to display batch data."}
          </p>
          <button
            type="button"
            className="secondary-btn"
            onClick={() => navigate("/surveys/new")}
          >
            Create New Mission
          </button>
        </div>
      </div>
    );
  }

  // Real backend metrics
  const totalFrames = batch.total_frames ?? (batch.frames?.length || 0);
  const processedFrames = batch.processed_frames ?? totalFrames;
  const totalRawDetections = batch.total_raw_detections ?? 0;
  const totalPersistentTracks = batch.total_persistent_tracks ?? (batch.tracks?.length || 0);
  const duplicatesMerged = batch.duplicates_merged ?? 0;
  const tracks = batch.tracks || [];
  const frames = batch.frames || [];
  const formattedDate = batch.created_at
    ? new Date(batch.created_at).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Recent Mission";

  return (
    <div>
      {/* Top Breadcrumb & Heading */}
      <div style={{ marginBottom: "16px" }}>
        <Link to="/surveys/new" className="back-link">
          <ArrowLeft size={15} /> Back to New Survey
        </Link>
        <div className="page-heading" style={{ marginBottom: "20px" }}>
          <div>
            <span className="eyebrow">BATCH INTELLIGENCE DOSSIER</span>
            <h1>Batch Analysis Results</h1>
            <p>
              Persistent anomaly trajectory & multi-frame acoustic correlation · {formattedDate}
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span
              style={{
                fontSize: "12px",
                fontFamily: "monospace",
                background: "var(--panel)",
                border: "1px solid var(--line)",
                padding: "6px 12px",
                borderRadius: "6px",
                color: "var(--muted)",
              }}
            >
              Batch ID: {batch.batch_id?.slice(0, 13)}...
            </span>
            <Link to="/history" className="secondary-btn small">
              Survey History
            </Link>
          </div>
        </div>
      </div>

      {/* TOP KPI ROW (Strictly real backend data) */}
      <div className="kpi-summary-grid" style={{ marginBottom: "24px" }}>
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Frames Processed</span>
            <FileImage size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">{processedFrames} / {totalFrames}</div>
          <div className="kpi-sub">Sequential sonar swath frames</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Raw YOLO Detections</span>
            <Target size={15} color="var(--amber)" />
          </div>
          <div className="kpi-value" style={{ color: totalRawDetections > 0 ? "var(--amber-text)" : undefined }}>
            {totalRawDetections}
          </div>
          <div className="kpi-sub">Individual frame-level contacts</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Persistent Anomalies</span>
            <Layers size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value" style={{ color: "var(--primary2)" }}>
            {totalPersistentTracks}
          </div>
          <div className="kpi-sub">Distinct acoustic targets tracked</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Repeated Detections Merged</span>
            <GitMerge size={15} color="var(--green)" />
          </div>
          <div className="kpi-value" style={{ color: "var(--green)" }}>
            {duplicatesMerged}
          </div>
          <div className="kpi-sub">Redundant swath duplicates unified</div>
        </div>
      </div>

      {/* USP VALUE PROPOSITION COMPARISON BOX (Judge Communication) */}
      <div
        className="panel"
        style={{
          background: "linear-gradient(135deg, rgba(21, 155, 211, 0.06) 0%, rgba(11, 131, 198, 0.02) 100%)",
          borderColor: "rgba(21, 155, 211, 0.25)",
          padding: "18px 22px",
          marginBottom: "24px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
          <div
            style={{
              width: "28px",
              height: "28px",
              borderRadius: "8px",
              background: "var(--primary-gradient)",
              display: "grid",
              placeItems: "center",
              color: "#fff",
              flexShrink: 0,
            }}
          >
            <Layers size={16} />
          </div>
          <div>
            <strong style={{ fontSize: "14px", color: "var(--text-dark)" }}>
              SONARIS Core Innovation: Multi-Frame Acoustic Continuity
            </strong>
            <span style={{ display: "block", fontSize: "12px", color: "var(--muted)" }}>
              Detections appearing across consecutive sonar frames are correlated using spatial IoU tracking to eliminate duplicate anomaly counts.
            </span>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "12px",
            marginTop: "14px",
            paddingTop: "14px",
            borderTop: "1px solid rgba(21, 155, 211, 0.15)",
          }}
        >
          <div style={{ background: "#ffffff", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--line)" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--muted)", textTransform: "uppercase" }}>
              Raw YOLO Detections
            </span>
            <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--text)" }}>
              = individual bounding boxes generated independently per sonar frame ({totalRawDetections} total)
            </p>
          </div>

          <div style={{ background: "#ffffff", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--line)" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase" }}>
              Persistent Anomalies
            </span>
            <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--text)" }}>
              = unified persistent objects identified across consecutive survey frames ({totalPersistentTracks} tracks)
            </p>
          </div>

          <div style={{ background: "#ffffff", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--line)" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--green-text)", textTransform: "uppercase" }}>
              Repeated Detections Merged
            </span>
            <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--text)" }}>
              = duplicate frame contacts combined into existing tracks ({duplicatesMerged} merged)
            </p>
          </div>
        </div>
      </div>

      {/* CHRONOLOGICAL FRAME TIMELINE */}
      <section className="panel" style={{ marginBottom: "24px" }}>
        <SectionHeader
          title="Chronological Frame Timeline"
          subtitle="Sequential sonar coverage across survey passes"
        />

        <div
          style={{
            display: "flex",
            gap: "12px",
            overflowX: "auto",
            paddingBottom: "10px",
            alignItems: "stretch",
          }}
        >
          {frames.map((frame, idx) => {
            const frameIndex = frame.frame_index ?? idx;
            const passDetections = (frame.detections || []).filter((d) => d.filter_status !== "FAIL");
            const detCount = passDetections.length;
            const isSelected = activeFrameIndex === frameIndex;

            // Find tracks active in this frame
            const activeTracks = tracks.filter((t) =>
              (t.frame_indices || []).includes(frameIndex)
            );

            return (
              <div
                key={frameIndex}
                onClick={() => setActiveFrameIndex(isSelected ? null : frameIndex)}
                style={{
                  minWidth: "200px",
                  maxWidth: "240px",
                  background: isSelected ? "var(--primary-light)" : "var(--panel)",
                  border: `1.5px solid ${isSelected ? "var(--primary)" : "var(--line)"}`,
                  borderRadius: "10px",
                  padding: "12px 14px",
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  transition: "all 0.15s ease",
                  flexShrink: 0,
                  position: "relative",
                  boxShadow: isSelected ? "0 4px 12px rgba(21, 155, 211, 0.18)" : "var(--card-shadow)",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                    <span
                      style={{
                        fontFamily: "Space Grotesk, sans-serif",
                        fontWeight: "700",
                        fontSize: "12px",
                        color: isSelected ? "var(--primary)" : "var(--text-dark)",
                      }}
                    >
                      Frame {String(frameIndex + 1).padStart(2, "0")}
                    </span>
                    {frame.processing_status === "ok" ? (
                      <span
                        style={{
                          fontSize: "10.5px",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: detCount > 0 ? "var(--amber-light)" : "var(--green-light)",
                          color: detCount > 0 ? "var(--amber-text)" : "var(--green-text)",
                          fontWeight: "600",
                        }}
                      >
                        {detCount} {detCount === 1 ? "det" : "dets"}
                      </span>
                    ) : (
                      <span
                        style={{
                          fontSize: "10.5px",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: "var(--red-light)",
                          color: "var(--red-text)",
                          fontWeight: "600",
                        }}
                      >
                        Error
                      </span>
                    )}
                  </div>

                  <strong
                    style={{
                      display: "block",
                      fontSize: "12px",
                      color: "var(--text-dark)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      marginBottom: "8px",
                    }}
                    title={frame.original_filename}
                  >
                    {frame.original_filename}
                  </strong>

                  {/* Thumbnail if evidence exists */}
                  {frame.evidence_filename && (
                    <div
                      style={{
                        width: "100%",
                        height: "70px",
                        borderRadius: "6px",
                        overflow: "hidden",
                        background: "#040912",
                        marginBottom: "8px",
                      }}
                    >
                      <img
                        src={evidenceUrl(frame.evidence_filename)}
                        alt={`Evidence frame ${frameIndex + 1}`}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        loading="lazy"
                      />
                    </div>
                  )}

                  {/* Detected Classes */}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "6px" }}>
                    {passDetections.map((d, dIdx) => (
                      <span
                        key={dIdx}
                        style={{
                          fontSize: "10px",
                          background: "var(--panel2)",
                          color: "var(--muted)",
                          padding: "2px 6px",
                          borderRadius: "4px",
                        }}
                      >
                        {formatClassName(d.class_name)}
                      </span>
                    ))}
                    {passDetections.length === 0 && (
                      <span style={{ fontSize: "11px", color: "var(--muted)", fontStyle: "italic" }}>
                        Clean sonar swath
                      </span>
                    )}
                  </div>
                </div>

                {/* Persistent Track continuity badge */}
                {activeTracks.length > 0 && (
                  <div
                    style={{
                      marginTop: "10px",
                      paddingTop: "8px",
                      borderTop: "1px dashed var(--line)",
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "4px",
                    }}
                  >
                    {activeTracks.map((trk) => (
                      <span
                        key={trk.track_id}
                        style={{
                          fontSize: "10px",
                          fontWeight: "700",
                          fontFamily: "Space Grotesk, sans-serif",
                          background: "var(--primary-gradient)",
                          color: "#fff",
                          padding: "2px 6px",
                          borderRadius: "4px",
                        }}
                      >
                        {trk.track_id}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* MAIN VISUAL SECTION: PERSISTENT ANOMALY TRACKING */}
      <section className="panel" style={{ marginBottom: "24px" }}>
        <SectionHeader
          title="Persistent Anomaly Tracking"
          subtitle="Detections appearing across consecutive sonar frames are grouped into persistent anomalies."
        />

        {totalPersistentTracks === 0 ? (
          /* NO ANOMALIES DETECTED IN THIS BATCH */
          <div className="clean-scan-card">
            <CheckCircle2 size={42} color="var(--green)" style={{ margin: "0 auto 12px auto" }} />
            <h3 style={{ fontSize: "18px", color: "var(--text-dark)", margin: "0 0 6px 0" }}>
              No anomalies detected in this batch.
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "13.5px", maxWidth: "520px", margin: "0 auto" }}>
              All {processedFrames} sequential sonar frames were evaluated through DRISHTI YOLO and false-positive filters with zero qualifying target contacts.
            </p>
          </div>
        ) : (
          <div>
            <div style={{ display: "grid", gap: "14px" }}>
              {tracks.map((track) => {
                const tone = RISK_TONE[track.highest_risk_level] || "info";
                const isSelected = selectedTrack?.track_id === track.track_id;
                const framesList = (track.frame_indices || []).map((idx) => idx + 1);

                return (
                  <div
                    key={track.track_id}
                    onClick={() => setSelectedTrack(isSelected ? null : track)}
                    style={{
                      background: isSelected ? "var(--panel-tint)" : "var(--panel)",
                      border: `1.5px solid ${isSelected ? "var(--primary)" : "var(--line)"}`,
                      borderRadius: "12px",
                      padding: "16px 20px",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      flexWrap: "wrap",
                      gap: "16px",
                      boxShadow: isSelected ? "0 4px 14px rgba(21, 155, 211, 0.15)" : "var(--card-shadow)",
                      transition: "all 0.18s ease",
                    }}
                  >
                    {/* Left: Track ID & Class */}
                    <div style={{ display: "flex", alignItems: "center", gap: "16px", minWidth: "220px" }}>
                      <div
                        style={{
                          width: "42px",
                          height: "42px",
                          borderRadius: "10px",
                          background: "var(--panel2)",
                          border: "1px solid var(--line)",
                          display: "grid",
                          placeItems: "center",
                          color: "var(--primary2)",
                          flexShrink: 0,
                        }}
                      >
                        <Layers size={20} />
                      </div>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <strong
                            style={{
                              fontFamily: "Space Grotesk, sans-serif",
                              fontSize: "15px",
                              color: "var(--text-dark)",
                            }}
                          >
                            {track.track_id}
                          </strong>
                          <Badge tone={tone}>
                            {track.highest_risk_level || "MEDIUM"}
                          </Badge>
                        </div>
                        <span style={{ fontSize: "13px", color: "var(--muted)", fontWeight: "500" }}>
                          {formatClassName(track.class_name)}
                        </span>
                      </div>
                    </div>

                    {/* Middle: Sequence Continuity & Frames Seen */}
                    <div style={{ display: "flex", alignItems: "center", gap: "24px", flexWrap: "wrap" }}>
                      <div>
                        <span
                          style={{
                            display: "block",
                            fontSize: "11px",
                            textTransform: "uppercase",
                            letterSpacing: "0.5px",
                            color: "var(--muted)",
                            fontWeight: "600",
                          }}
                        >
                          Frames Seen
                        </span>
                        <strong style={{ fontSize: "13.5px", color: "var(--text-dark)" }}>
                          {track.frames_seen} {track.frames_seen === 1 ? "frame" : "frames"}{" "}
                          <span style={{ color: "var(--muted)", fontWeight: "400", fontSize: "12px" }}>
                            (Frames: {framesList.join(", ")})
                          </span>
                        </strong>
                      </div>

                      <div>
                        <span
                          style={{
                            display: "block",
                            fontSize: "11px",
                            textTransform: "uppercase",
                            letterSpacing: "0.5px",
                            color: "var(--muted)",
                            fontWeight: "600",
                          }}
                        >
                          Max Confidence
                        </span>
                        <strong style={{ fontSize: "13.5px", color: "var(--text-dark)" }}>
                          {track.max_confidence != null ? `${(track.max_confidence * 100).toFixed(1)}%` : "N/A"}
                        </strong>
                      </div>

                      <div>
                        <span
                          style={{
                            display: "block",
                            fontSize: "11px",
                            textTransform: "uppercase",
                            letterSpacing: "0.5px",
                            color: "var(--muted)",
                            fontWeight: "600",
                          }}
                        >
                          Acoustic Span
                        </span>
                        <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                          Frame {track.first_frame + 1} → Frame {track.last_frame + 1}
                        </span>
                      </div>
                    </div>

                    {/* Right: Expand details trigger */}
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: "600",
                          color: "var(--primary)",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        {isSelected ? "Hide Frame History" : "View Frame History"}
                        <ChevronRight
                          size={16}
                          style={{
                            transform: isSelected ? "rotate(90deg)" : "none",
                            transition: "transform 0.2s ease",
                          }}
                        />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {/* TRACK DETAILS / EXPANDABLE FRAME HISTORY DRAWER */}
      {selectedTrack && (
        <section
          className="panel"
          style={{
            border: "1.5px solid var(--primary)",
            background: "#ffffff",
            padding: "24px",
            marginBottom: "24px",
            boxShadow: "0 8px 30px rgba(21, 155, 211, 0.12)",
          }}
        >
          {/* Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderBottom: "1px solid var(--line)",
              paddingBottom: "16px",
              marginBottom: "20px",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "8px",
                  background: "var(--primary-gradient)",
                  display: "grid",
                  placeItems: "center",
                  color: "#fff",
                }}
              >
                <Layers size={18} />
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <h3 style={{ margin: 0, fontSize: "17px", color: "var(--text-dark)" }}>
                    Persistent Anomaly: {selectedTrack.track_id}
                  </h3>
                  <Badge tone={RISK_TONE[selectedTrack.highest_risk_level] || "info"}>
                    {selectedTrack.highest_risk_level || "MEDIUM"} RISK
                  </Badge>
                </div>
                <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                  Class: <strong>{formatClassName(selectedTrack.class_name)}</strong> · Max Confidence:{" "}
                  <strong>{selectedTrack.max_confidence ? `${(selectedTrack.max_confidence * 100).toFixed(1)}%` : "N/A"}</strong> · Detected in {selectedTrack.frames_seen} frames (Frames: {(selectedTrack.frame_indices || []).map(i => i + 1).join(", ")})
                </span>
              </div>
            </div>

            <button
              type="button"
              className="icon-btn"
              onClick={() => setSelectedTrack(null)}
              title="Close frame history"
            >
              <X size={20} />
            </button>
          </div>

          {/* Sequential Frame Occurrences History */}
          <div>
            <h4
              style={{
                fontSize: "13px",
                fontWeight: "700",
                textTransform: "uppercase",
                letterSpacing: "0.6px",
                color: "var(--muted)",
                margin: "0 0 14px 0",
              }}
            >
              Chronological Frame History for {selectedTrack.track_id}
            </h4>

            <div style={{ display: "grid", gap: "14px" }}>
              {(selectedTrack.bbox_history || []).map((entry, hIdx) => {
                const fIdx = entry.frame_index;
                const sourceFrame = frames[fIdx] || {};
                const confidence = selectedTrack.confidence_history?.[hIdx] ?? 0;
                const riskScore = selectedTrack.risk_score_history?.[hIdx] ?? selectedTrack.max_risk_score ?? 0;
                const bbox = entry.bbox || [];
                const geo = entry.geolocation;
                const evidenceFile = sourceFrame.evidence_filename;

                const hasGps = geo && geo.latitude != null && geo.longitude != null;

                return (
                  <div
                    key={hIdx}
                    style={{
                      background: "var(--panel-tint)",
                      border: "1px solid var(--line)",
                      borderRadius: "10px",
                      padding: "16px",
                      display: "grid",
                      gridTemplateColumns: evidenceFile ? "180px 1fr" : "1fr",
                      gap: "18px",
                      alignItems: "center",
                    }}
                  >
                    {/* Evidence thumbnail if available */}
                    {evidenceFile && (
                      <div
                        style={{
                          width: "100%",
                          height: "120px",
                          borderRadius: "8px",
                          overflow: "hidden",
                          background: "#040912",
                          border: "1px solid var(--line)",
                        }}
                      >
                        <img
                          src={evidenceUrl(evidenceFile)}
                          alt={`Evidence Frame ${fIdx + 1}`}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          loading="lazy"
                        />
                      </div>
                    )}

                    {/* Metadata & Geometry */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                        <span
                          style={{
                            fontFamily: "Space Grotesk, sans-serif",
                            fontSize: "14px",
                            fontWeight: "700",
                            color: "var(--text-dark)",
                          }}
                        >
                          Frame {String(fIdx + 1).padStart(2, "0")} · {sourceFrame.original_filename || `frame_${fIdx}.jpg`}
                        </span>

                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                            Confidence: <strong>{(confidence * 100).toFixed(1)}%</strong>
                          </span>
                          <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                            Risk Score: <strong>{Number(riskScore).toFixed(2)}</strong>
                          </span>
                        </div>
                      </div>

                      {/* Bounding Box Information */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "14px",
                          fontSize: "11.5px",
                          color: "var(--muted)",
                          background: "#ffffff",
                          padding: "8px 12px",
                          borderRadius: "6px",
                          border: "1px solid var(--line)",
                          flexWrap: "wrap",
                        }}
                      >
                        <span>
                          <strong>Bounding Box:</strong>{" "}
                          {bbox.length === 4
                            ? `[${bbox.map((v) => Math.round(v)).join(", ")}]`
                            : "N/A"}
                        </span>
                      </div>

                      {/* Acoustic & Geolocation Parameters (Strictly adhering to No Fake GPS rule) */}
                      <div
                        style={{
                          fontSize: "11.5px",
                          padding: "8px 12px",
                          borderRadius: "6px",
                          background: hasGps ? "var(--green-light)" : "var(--panel2)",
                          border: `1px solid ${hasGps ? "var(--green-border)" : "var(--line)"}`,
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                          flexWrap: "wrap",
                        }}
                      >
                        {hasGps ? (
                          <>
                            <div style={{ display: "flex", alignItems: "center", gap: "5px", color: "var(--green-text)" }}>
                              <MapPin size={13} />
                              <strong>Lat: {geo.latitude?.toFixed(6)}°</strong>,{" "}
                              <strong>Lon: {geo.longitude?.toFixed(6)}°</strong>
                            </div>
                            {geo.slant_range_m != null && (
                              <span style={{ color: "var(--muted)" }}>
                                Slant Range: {geo.slant_range_m}m
                              </span>
                            )}
                            {geo.bearing_deg != null && (
                              <span style={{ color: "var(--muted)" }}>
                                Bearing: {geo.bearing_deg}°
                              </span>
                            )}
                          </>
                        ) : (
                          <>
                            <div style={{ display: "flex", alignItems: "center", gap: "5px", color: "var(--muted)" }}>
                              <Compass size={13} />
                              <strong>Geographic coordinates unavailable</strong> (Relative coordinate system)
                            </div>
                            {geo?.range_m != null && (
                              <span style={{ color: "var(--text)" }}>
                                Range: {geo.range_m}m
                              </span>
                            )}
                            {geo?.bearing_deg != null && (
                              <span style={{ color: "var(--text)" }}>
                                Bearing: {geo.bearing_deg}°
                              </span>
                            )}
                            {geo?.local_x_m != null && geo?.local_y_m != null && (
                              <span style={{ color: "var(--text)" }}>
                                Local X/Y: ({geo.local_x_m}m, {geo.local_y_m}m)
                              </span>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* RAW FRAME DETECTIONS BREAKDOWN (Audit view for operators) */}
      <section className="panel">
        <SectionHeader
          title="Frame-by-Frame Acoustic Audit"
          subtitle="Inspect individual detections across all processed survey frames"
        />

        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "10px 14px", textAlign: "left" }}>Frame</th>
                <th style={{ padding: "10px 14px", textAlign: "left" }}>Source Image</th>
                <th style={{ padding: "10px 14px", textAlign: "center" }}>Status</th>
                <th style={{ padding: "10px 14px", textAlign: "center" }}>Detections</th>
                <th style={{ padding: "10px 14px", textAlign: "left" }}>Target Classes</th>
                <th style={{ padding: "10px 14px", textAlign: "center" }}>Persistent Track</th>
              </tr>
            </thead>
            <tbody>
              {frames.map((frame, idx) => {
                const fIdx = frame.frame_index ?? idx;
                const dets = (frame.detections || []).filter((d) => d.filter_status !== "FAIL");
                const matchedTracks = tracks.filter((t) =>
                  (t.frame_indices || []).includes(fIdx)
                );

                return (
                  <tr key={fIdx}>
                    <td style={{ padding: "12px 14px", fontWeight: "700", fontFamily: "Space Grotesk, sans-serif" }}>
                      Frame {String(fIdx + 1).padStart(2, "0")}
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <strong style={{ fontSize: "13px", color: "var(--text-dark)" }}>
                        {frame.original_filename}
                      </strong>
                    </td>
                    <td style={{ padding: "12px 14px", textAlign: "center" }}>
                      {frame.processing_status === "ok" ? (
                        <span className="badge badge-success">PROCESSED</span>
                      ) : (
                        <span className="badge badge-danger">FAILED</span>
                      )}
                    </td>
                    <td style={{ padding: "12px 14px", textAlign: "center", fontWeight: "600" }}>
                      {dets.length}
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      {dets.length > 0 ? (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                          {dets.map((d, dIdx) => (
                            <span
                              key={dIdx}
                              style={{
                                fontSize: "11px",
                                background: "var(--panel2)",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                color: "var(--text)",
                              }}
                            >
                              {formatClassName(d.class_name)} ({(d.confidence * 100).toFixed(0)}%)
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ fontSize: "12px", color: "var(--muted)", fontStyle: "italic" }}>
                          No targets in swath
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "12px 14px", textAlign: "center" }}>
                      {matchedTracks.length > 0 ? (
                        <div style={{ display: "flex", justifyContent: "center", gap: "4px", flexWrap: "wrap" }}>
                          {matchedTracks.map((t) => (
                            <span
                              key={t.track_id}
                              onClick={() => setSelectedTrack(t)}
                              style={{
                                cursor: "pointer",
                                fontSize: "10.5px",
                                fontWeight: "700",
                                fontFamily: "Space Grotesk, sans-serif",
                                background: "var(--primary-gradient)",
                                color: "#fff",
                                padding: "2px 8px",
                                borderRadius: "4px",
                              }}
                              title="Click to inspect track"
                            >
                              {t.track_id}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ fontSize: "12px", color: "var(--muted)" }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
