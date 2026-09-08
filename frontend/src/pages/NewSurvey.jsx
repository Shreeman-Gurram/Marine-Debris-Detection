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
} from "lucide-react";
import SectionHeader from "../components/SectionHeader";
import { analyzeSonar } from "../services/api";

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

  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  // Optional survey metadata
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

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">NEW MISSION</span>
          <h1>Upload Sonar Imagery</h1>
          <p>Execute DRISHTI anomaly detection, false-positive filtering, and threat scoring</p>
        </div>
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

      {/* When analyzing, show active operational processing state */}
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
    </div>
  );
}
