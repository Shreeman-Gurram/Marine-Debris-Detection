// src/pages/NewSurvey.jsx
import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  UploadCloud,
  X,
  FileImage,
  ChevronRight,
  AlertCircle,
  ScanLine,
  Compass,
  MapPin,
  Maximize2,
  CheckCircle2,
  Layers,
} from "lucide-react";
import SectionHeader from "../components/SectionHeader";
import BatchUpload from "../components/BatchUpload";
import { analyzeSonar, analyzeBatch } from "../services/api";

const LOADING_PHASES = [
  "Validating sonar imagery format...",
  "Preprocessing sonar image (NLM + CLAHE)...",
  "Running DRISHTI YOLO anomaly detection...",
  "Filtering false positives & assessing risk...",
  "Computing acoustic geolocation & coordinates...",
  "Persisting intelligence to MongoDB Atlas...",
];

export default function NewSurvey() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // Survey Mode: "single" | "batch" (Default: "single")
  const [surveyMode, setSurveyMode] = useState("single");

  // Single analysis state
  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  // Batch analysis state
  const [batchFiles, setBatchFiles] = useState([]);
  const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false);

  // Optional survey metadata (shared between single and batch)
  const [meta, setMeta] = useState({
    range_m: "50",
    latitude: "",
    longitude: "",
    heading_deg: "0",
  });

  // Processing & error states
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [errorMsg, setErrorMsg] = useState(null);

  function handleFileSelection(selected) {
    if (!selected) return;
    const validTypes = ["image/jpeg", "image/png", "image/jpg"];
    if (!validTypes.includes(selected.type) && !/\.(jpe?g|png)$/i.test(selected.name)) {
      setErrorMsg("Please select a valid Side-Scan Sonar image (.jpg, .jpeg, or .png).");
      return;
    }
    setErrorMsg(null);
    setFile(selected);
    const url = URL.createObjectURL(selected);
    setFilePreview(url);
  }

  function handleDrag(e) {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  }

  function clearFile(e) {
    e?.preventDefault();
    e?.stopPropagation();
    if (filePreview) URL.revokeObjectURL(filePreview);
    setFile(null);
    setFilePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleAnalyze(e) {
    e.preventDefault();
    if (!file) {
      setErrorMsg("Please select a sonar image to analyze.");
      return;
    }

    setIsAnalyzing(true);
    setErrorMsg(null);
    setPhaseIndex(0);

    // Advance UI loading phase sequentially
    const phaseTimer = setInterval(() => {
      setPhaseIndex((prev) => (prev < LOADING_PHASES.length - 1 ? prev + 1 : prev));
    }, 700);

    try {
      // Build optional metadata payload
      const metaPayload = {};
      if (meta.range_m && !isNaN(parseFloat(meta.range_m))) {
        metaPayload.range_m = parseFloat(meta.range_m);
      }
      if (meta.latitude && !isNaN(parseFloat(meta.latitude))) {
        metaPayload.latitude = parseFloat(meta.latitude);
      }
      if (meta.longitude && !isNaN(parseFloat(meta.longitude))) {
        metaPayload.longitude = parseFloat(meta.longitude);
      }
      if (meta.heading_deg && !isNaN(parseFloat(meta.heading_deg))) {
        metaPayload.heading_deg = parseFloat(meta.heading_deg);
      }

      // Real API request to POST /api/analyze
      const result = await analyzeSonar(file, metaPayload);
      clearInterval(phaseTimer);

      // Navigate to detailed analysis review page with real results
      const analysisId = result.analysis_id || result._id || "latest";
      navigate(`/analysis/${analysisId}`, {
        state: {
          analysis: result,
          originalPreview: filePreview,
          originalFilename: file.name,
        },
      });
    } catch (err) {
      clearInterval(phaseTimer);
      setIsAnalyzing(false);
      console.error("Analysis request failed:", err);
      setErrorMsg(
        err.message || "Pipeline execution failed. Please verify that the backend is running."
      );
    }
  }

  async function handleBatchAnalyze(e) {
    e.preventDefault();
    if (batchFiles.length === 0) {
      setErrorMsg("Please select at least one sonar frame for batch analysis.");
      return;
    }
    if (batchFiles.length > 10) {
      setErrorMsg("Batch analysis supports a maximum of 10 frames.");
      return;
    }

    setIsBatchAnalyzing(true);
    setErrorMsg(null);

    try {
      const metaPayload = {};
      if (meta.range_m && !isNaN(parseFloat(meta.range_m))) {
        metaPayload.slant_range_m = parseFloat(meta.range_m);
      }
      if (meta.latitude && !isNaN(parseFloat(meta.latitude))) {
        metaPayload.latitude = parseFloat(meta.latitude);
      }
      if (meta.longitude && !isNaN(parseFloat(meta.longitude))) {
        metaPayload.longitude = parseFloat(meta.longitude);
      }
      if (meta.heading_deg && !isNaN(parseFloat(meta.heading_deg))) {
        metaPayload.heading_deg = parseFloat(meta.heading_deg);
      }

      const result = await analyzeBatch(batchFiles, metaPayload);
      setIsBatchAnalyzing(false);

      const batchTargetId = result.batch_db_id || result.id || result.batch_id;
      navigate(`/batches/${batchTargetId}`, {
        state: {
          batch: result,
        },
      });
    } catch (err) {
      setIsBatchAnalyzing(false);
      console.error("Batch analysis request failed:", err);
      setErrorMsg(
        err.message || "Batch pipeline execution failed. Please verify that the backend is running."
      );
    }
  }

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">NEW MISSION</span>
          <h1>Upload Sonar Imagery</h1>
          <p>Execute DRISHTI anomaly detection, false-positive filtering, and threat scoring</p>
        </div>
      </div>

      {/* Mode Selector: Single Analysis vs Batch Analysis */}
      <div className="view-mode-pill" style={{ marginBottom: "24px" }}>
        <button
          type="button"
          className={surveyMode === "single" ? "active" : ""}
          onClick={() => {
            if (!isAnalyzing && !isBatchAnalyzing) {
              setSurveyMode("single");
              setErrorMsg(null);
            }
          }}
          disabled={isAnalyzing || isBatchAnalyzing}
        >
          <FileImage size={15} /> Single Analysis
        </button>
        <button
          type="button"
          className={surveyMode === "batch" ? "active" : ""}
          onClick={() => {
            if (!isAnalyzing && !isBatchAnalyzing) {
              setSurveyMode("batch");
              setErrorMsg(null);
            }
          }}
          disabled={isAnalyzing || isBatchAnalyzing}
        >
          <Layers size={15} /> Batch Analysis
        </button>
      </div>

      {errorMsg && (
        <div
          style={{
            marginBottom: "20px",
            padding: "14px 18px",
            borderRadius: "10px",
            background: "rgba(243, 109, 122, 0.15)",
            border: "1px solid rgba(243, 109, 122, 0.35)",
            color: "#ff8b97",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <AlertCircle size={20} />
          <span style={{ fontSize: "14px" }}>{errorMsg}</span>
        </div>
      )}

      {/* ============================================================ */}
      {/* MODE 1: SINGLE ANALYSIS WORKFLOW (Unchanged)                 */}
      {/* ============================================================ */}
      {surveyMode === "single" && (
        <>
          {isAnalyzing ? (
            <section className="panel" style={{ padding: "50px 30px", textAlign: "center" }}>
              <div
                style={{
                  width: "72px",
                  height: "72px",
                  margin: "0 auto 24px auto",
                  borderRadius: "50%",
                  background: "radial-gradient(circle, rgba(73, 183, 255, 0.2) 0%, rgba(36, 126, 234, 0.05) 70%)",
                  border: "1px solid rgba(73, 183, 255, 0.4)",
                  display: "grid",
                  placeItems: "center",
                  animation: "pulse 2s infinite ease-in-out",
                }}
              >
                <ScanLine size={36} color="var(--primary)" />
              </div>
              <span className="eyebrow" style={{ color: "var(--primary)" }}>AI INFERENCE PIPELINE</span>
              <h2 style={{ fontSize: "22px", margin: "10px 0 6px 0" }}>Analyzing Sonar Imagery</h2>
              <p style={{ color: "var(--muted)", maxWidth: "480px", margin: "0 auto 24px auto" }}>
                Processing <strong style={{ color: "var(--text)" }}>{file?.name}</strong> through DRISHTI YOLO detector
                and geometric geolocation engine.
              </p>

              <div
                style={{
                  maxWidth: "460px",
                  margin: "0 auto 20px auto",
                  background: "var(--panel-alt)",
                  borderRadius: "10px",
                  padding: "16px 20px",
                  border: "1px solid var(--line)",
                  textAlign: "left",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--primary)", fontSize: "14px" }}>
                  <div
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: "var(--green)",
                      boxShadow: "0 0 8px var(--green)",
                    }}
                  />
                  <strong>{LOADING_PHASES[phaseIndex]}</strong>
                </div>
                <div className="progress" style={{ marginTop: "14px" }}>
                  <span
                    style={{
                      width: `${Math.round(((phaseIndex + 1) / LOADING_PHASES.length) * 100)}%`,
                      transition: "width 0.4s ease",
                    }}
                  />
                </div>
              </div>
              <small style={{ color: "var(--muted)" }}>Do not close this window during acoustic processing...</small>
            </section>
          ) : (
            <form onSubmit={handleAnalyze} className="form-layout">
              {/* Sonar Image Dropzone */}
              <section className="panel">
                <SectionHeader
                  title="Side-Scan Sonar Imagery"
                  subtitle="Upload sonar waterfall or acoustic tile (.JPG, .PNG)"
                />

                <div
                  className={`dropzone ${file ? "has-file" : ""} ${dragActive ? "drag-active" : ""}`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => !file && fileInputRef.current?.click()}
                  style={{
                    cursor: file ? "default" : "pointer",
                    position: "relative",
                    border: dragActive ? "2px dashed var(--primary)" : undefined,
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/jpg"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      if (e.target.files?.[0]) handleFileSelection(e.target.files[0]);
                    }}
                  />

                  {file ? (
                    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "14px" }}>
                      <div
                        style={{
                          maxHeight: "320px",
                          borderRadius: "8px",
                          overflow: "hidden",
                          background: "#040912",
                          display: "flex",
                          justifyContent: "center",
                          alignItems: "center",
                        }}
                      >
                        <img
                          src={filePreview}
                          alt="Sonar preview"
                          style={{ maxHeight: "320px", width: "100%", objectFit: "contain" }}
                        />
                      </div>

                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          background: "var(--panel-alt)",
                          padding: "10px 14px",
                          borderRadius: "8px",
                          border: "1px solid var(--line)",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          <FileImage size={24} color="var(--primary)" />
                          <div>
                            <strong style={{ display: "block", fontSize: "14px" }}>{file.name}</strong>
                            <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                              {(file.size / 1024).toFixed(1)} KB · {file.type || "image"}
                            </span>
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: "8px" }}>
                          <button
                            type="button"
                            className="secondary-btn"
                            style={{ padding: "6px 12px", fontSize: "12px" }}
                            onClick={() => fileInputRef.current?.click()}
                          >
                            Replace
                          </button>
                          <button
                            type="button"
                            className="icon-btn"
                            onClick={clearFile}
                            title="Remove image"
                          >
                            <X size={18} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: "40px 20px", textAlign: "center" }}>
                      <UploadCloud size={40} color="var(--primary)" style={{ margin: "0 auto 12px auto" }} />
                      <strong style={{ display: "block", fontSize: "16px", marginBottom: "6px" }}>
                        Select or drag & drop sonar imagery
                      </strong>
                      <span style={{ color: "var(--muted)", fontSize: "13px" }}>
                        Supported formats: Standard high-resolution JPG, PNG sonar tiles
                      </span>
                    </div>
                  )}
                </div>
              </section>

              {/* Survey Acoustic Metadata (Optional) */}
              <section className="panel">
                <SectionHeader
                  title="Survey Acoustic & Geolocation Metadata"
                  subtitle="Optional navigation parameters for acoustic-to-geodetic projection"
                />

                <div className="form-grid">
                  <label>
                    Sonar slant range (meters)
                    <div className="input-icon">
                      <Maximize2 size={16} />
                      <input
                        type="number"
                        step="0.5"
                        value={meta.range_m}
                        onChange={(e) => setMeta({ ...meta, range_m: e.target.value })}
                        placeholder="e.g. 50"
                      />
                    </div>
                  </label>

                  <label>
                    Vessel heading (degrees 0-360)
                    <div className="input-icon">
                      <Compass size={16} />
                      <input
                        type="number"
                        step="1"
                        min="0"
                        max="360"
                        value={meta.heading_deg}
                        onChange={(e) => setMeta({ ...meta, heading_deg: e.target.value })}
                        placeholder="e.g. 90"
                      />
                    </div>
                  </label>

                  <label>
                    Towfish / Vessel Latitude (decimal)
                    <div className="input-icon">
                      <MapPin size={16} />
                      <input
                        type="number"
                        step="0.000001"
                        value={meta.latitude}
                        onChange={(e) => setMeta({ ...meta, latitude: e.target.value })}
                        placeholder="Optional (e.g. 18.9219)"
                      />
                    </div>
                  </label>

                  <label>
                    Towfish / Vessel Longitude (decimal)
                    <div className="input-icon">
                      <MapPin size={16} />
                      <input
                        type="number"
                        step="0.000001"
                        value={meta.longitude}
                        onChange={(e) => setMeta({ ...meta, longitude: e.target.value })}
                        placeholder="Optional (e.g. 72.8346)"
                      />
                    </div>
                  </label>
                </div>

                <div className="form-actions" style={{ marginTop: "24px" }}>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => navigate("/dashboard")}
                  >
                    Cancel
                  </button>
                  <button
                    className="primary-btn"
                    type="submit"
                    disabled={!file || isAnalyzing}
                    style={{ opacity: !file ? 0.6 : 1 }}
                  >
                    <ScanLine size={18} /> Analyze Sonar <ChevronRight size={17} />
                  </button>
                </div>
              </section>
            </form>
          )}
        </>
      )}

      {/* ============================================================ */}
      {/* MODE 2: BATCH ANALYSIS WORKFLOW (Phase 3)                   */}
      {/* ============================================================ */}
      {surveyMode === "batch" && (
        <>
          {isBatchAnalyzing ? (
            <section className="panel" style={{ padding: "50px 30px", textAlign: "center" }}>
              <div
                style={{
                  width: "72px",
                  height: "72px",
                  margin: "0 auto 24px auto",
                  borderRadius: "50%",
                  background: "radial-gradient(circle, rgba(21, 155, 211, 0.25) 0%, rgba(11, 131, 198, 0.05) 70%)",
                  border: "1px solid rgba(21, 155, 211, 0.4)",
                  display: "grid",
                  placeItems: "center",
                  animation: "pulse 2s infinite ease-in-out",
                }}
              >
                <Layers size={36} color="var(--primary)" />
              </div>
              <span className="eyebrow" style={{ color: "var(--primary)" }}>SEQUENTIAL BATCH PIPELINE</span>
              <h2 style={{ fontSize: "22px", margin: "10px 0 6px 0" }}>Processing Sonar Frames...</h2>
              <p style={{ color: "var(--muted)", maxWidth: "520px", margin: "0 auto 24px auto" }}>
                Running DRISHTI YOLO anomaly detection across{" "}
                <strong style={{ color: "var(--text)" }}>{batchFiles.length} sequential frames</strong> and executing
                SonarTracker persistent IoU correlation.
              </p>

              <div
                style={{
                  maxWidth: "480px",
                  margin: "0 auto 20px auto",
                  background: "var(--panel-alt)",
                  borderRadius: "10px",
                  padding: "16px 20px",
                  border: "1px solid var(--line)",
                  textAlign: "left",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--primary)", fontSize: "14px" }}>
                  <div
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: "var(--primary)",
                      boxShadow: "0 0 8px var(--primary)",
                    }}
                  />
                  <strong>Sequential acoustic inference in progress...</strong>
                </div>
                <div
                  className="progress"
                  style={{
                    marginTop: "14px",
                    position: "relative",
                    overflow: "hidden",
                  }}
                >
                  <span
                    style={{
                      width: "100%",
                      animation: "pulse 1.8s infinite ease-in-out",
                    }}
                  />
                </div>
              </div>
              <small style={{ color: "var(--muted)" }}>
                Do not close or reload this window during acoustic batch correlation...
              </small>
            </section>
          ) : (
            <form onSubmit={handleBatchAnalyze} className="form-layout">
              {/* Batch Upload Section */}
              <section className="panel">
                <SectionHeader
                  title="Sequential Sonar Frame Batch"
                  subtitle="Upload 1–10 chronological sonar swath frames (.JPG, .PNG)"
                />

                <BatchUpload
                  files={batchFiles}
                  setFiles={setBatchFiles}
                  disabled={isBatchAnalyzing}
                  error={errorMsg}
                  setError={setErrorMsg}
                />
              </section>

              {/* Shared Metadata Section */}
              <section className="panel">
                <SectionHeader
                  title="Survey Acoustic & Geolocation Metadata"
                  subtitle="Optional navigation parameters applied across all batch frames"
                />

                <div className="form-grid">
                  <label>
                    Sonar slant range (meters)
                    <div className="input-icon">
                      <Maximize2 size={16} />
                      <input
                        type="number"
                        step="0.5"
                        value={meta.range_m}
                        onChange={(e) => setMeta({ ...meta, range_m: e.target.value })}
                        placeholder="e.g. 50"
                        disabled={isBatchAnalyzing}
                      />
                    </div>
                  </label>

                  <label>
                    Vessel heading (degrees 0-360)
                    <div className="input-icon">
                      <Compass size={16} />
                      <input
                        type="number"
                        step="1"
                        min="0"
                        max="360"
                        value={meta.heading_deg}
                        onChange={(e) => setMeta({ ...meta, heading_deg: e.target.value })}
                        placeholder="e.g. 90"
                        disabled={isBatchAnalyzing}
                      />
                    </div>
                  </label>

                  <label>
                    Towfish / Vessel Latitude (decimal)
                    <div className="input-icon">
                      <MapPin size={16} />
                      <input
                        type="number"
                        step="0.000001"
                        value={meta.latitude}
                        onChange={(e) => setMeta({ ...meta, latitude: e.target.value })}
                        placeholder="Optional (e.g. 18.9219)"
                        disabled={isBatchAnalyzing}
                      />
                    </div>
                  </label>

                  <label>
                    Towfish / Vessel Longitude (decimal)
                    <div className="input-icon">
                      <MapPin size={16} />
                      <input
                        type="number"
                        step="0.000001"
                        value={meta.longitude}
                        onChange={(e) => setMeta({ ...meta, longitude: e.target.value })}
                        placeholder="Optional (e.g. 72.8346)"
                        disabled={isBatchAnalyzing}
                      />
                    </div>
                  </label>
                </div>

                <div
                  style={{
                    marginTop: "16px",
                    background: "var(--panel2)",
                    borderRadius: "8px",
                    padding: "10px 14px",
                    border: "1px solid var(--line)",
                    fontSize: "12px",
                    color: "var(--muted)",
                  }}
                >
                  GPS coordinates are optional. If omitted, target positions remain relative to local sonar frame (range and bearing) without fabricating geographic coordinates.
                </div>

                <div className="form-actions" style={{ marginTop: "24px" }}>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => navigate("/dashboard")}
                    disabled={isBatchAnalyzing}
                  >
                    Cancel
                  </button>
                  <button
                    className="primary-btn"
                    type="submit"
                    disabled={batchFiles.length === 0 || batchFiles.length > 10 || isBatchAnalyzing}
                    style={{
                      opacity: batchFiles.length === 0 || batchFiles.length > 10 || isBatchAnalyzing ? 0.6 : 1,
                    }}
                  >
                    <Layers size={18} /> Start Batch Analysis <ChevronRight size={17} />
                  </button>
                </div>
              </section>
            </form>
          )}
        </>
      )}
    </div>
  );
}
