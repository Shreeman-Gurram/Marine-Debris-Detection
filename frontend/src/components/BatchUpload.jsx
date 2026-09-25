// src/components/BatchUpload.jsx
// Batch Analysis multi-frame upload component with chronological ordering, thumbnails, and reordering.
import { useState, useRef, useEffect } from "react";
import {
  UploadCloud,
  X,
  FileImage,
  ChevronUp,
  ChevronDown,
  AlertCircle,
  Layers,
  ArrowUpDown,
} from "lucide-react";

export default function BatchUpload({
  files,
  setFiles,
  disabled = false,
  error = null,
  setError = () => {},
}) {
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [thumbnails, setThumbnails] = useState([]);

  // Generate and manage object URL previews for selected files
  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setThumbnails(urls);

    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [files]);

  function handleFilesAdded(newFilesList) {
    if (!newFilesList || newFilesList.length === 0) return;
    setError(null);

    const validExtensions = /\.(jpe?g|png)$/i;
    const acceptedFiles = [];
    const rejectedFiles = [];

    for (const f of newFilesList) {
      if (
        (f.type && (f.type === "image/jpeg" || f.type === "image/png" || f.type === "image/jpg")) ||
        validExtensions.test(f.name)
      ) {
        acceptedFiles.push(f);
      } else {
        rejectedFiles.push(f.name);
      }
    }

    if (rejectedFiles.length > 0) {
      setError(
        `Unsupported format for: ${rejectedFiles.join(", ")}. Accepted formats: .jpg, .jpeg, .png`
      );
      return;
    }

    const merged = [...files, ...acceptedFiles];
    if (merged.length > 10) {
      setError(
        `Batch exceeds maximum limit of 10 frames. Selected ${merged.length} frames.`
      );
    }

    setFiles(merged);
  }

  function handleDrag(e) {
    if (disabled) return;
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }

  function handleDrop(e) {
    if (disabled) return;
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer?.files) {
      handleFilesAdded(Array.from(e.dataTransfer.files));
    }
  }

  function removeFile(index) {
    if (disabled) return;
    const updated = files.filter((_, i) => i !== index);
    setFiles(updated);
    if (updated.length <= 10 && error?.includes("exceeds maximum limit")) {
      setError(null);
    }
  }

  function moveFileUp(index) {
    if (disabled || index === 0) return;
    const updated = [...files];
    const temp = updated[index - 1];
    updated[index - 1] = updated[index];
    updated[index] = temp;
    setFiles(updated);
  }

  function moveFileDown(index) {
    if (disabled || index === files.length - 1) return;
    const updated = [...files];
    const temp = updated[index + 1];
    updated[index + 1] = updated[index];
    updated[index] = temp;
    setFiles(updated);
  }

  function clearAll() {
    if (disabled) return;
    setFiles([]);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Informative Guidance Banner */}
      <div
        style={{
          background: "rgba(21, 155, 211, 0.08)",
          border: "1px solid rgba(21, 155, 211, 0.25)",
          borderRadius: "10px",
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Layers size={18} color="var(--primary)" />
          <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-dark)" }}>
            Upload frames in chronological survey order.
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              fontSize: "12px",
              fontWeight: "600",
              color: files.length > 10 ? "var(--red)" : files.length > 0 ? "var(--primary)" : "var(--muted)",
              background: files.length > 10 ? "var(--red-light)" : "var(--panel)",
              padding: "4px 10px",
              borderRadius: "20px",
              border: `1px solid ${files.length > 10 ? "var(--red-border)" : "var(--line)"}`,
            }}
          >
            {files.length} / 10 frames selected
          </span>
          {files.length > 0 && !disabled && (
            <button
              type="button"
              onClick={clearAll}
              className="toolbar-btn"
              style={{ fontSize: "11.5px", padding: "4px 8px" }}
            >
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Multi-file Dropzone */}
      <div
        className={`dropzone ${dragActive ? "drag-active" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        style={{
          cursor: disabled ? "not-allowed" : "pointer",
          border: dragActive
            ? "2px dashed var(--primary)"
            : files.length > 10
            ? "1.5px dashed var(--red)"
            : "1.5px dashed #a5d2eb",
          minHeight: files.length === 0 ? "200px" : "110px",
          padding: "20px",
          opacity: disabled ? 0.6 : 1,
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".jpg,.jpeg,.png,image/jpeg,image/png"
          multiple
          disabled={disabled}
          style={{ display: "none" }}
          onChange={(e) => {
            if (e.target.files) {
              handleFilesAdded(Array.from(e.target.files));
              e.target.value = "";
            }
          }}
        />

        <div style={{ textAlign: "center", pointerEvents: "none" }}>
          <UploadCloud
            size={files.length === 0 ? 38 : 28}
            color="var(--primary)"
            style={{ margin: "0 auto 8px auto" }}
          />
          <strong style={{ display: "block", fontSize: "14px", marginBottom: "4px" }}>
            {files.length === 0
              ? "Select or drag & drop sequential sonar frames"
              : "Add more frames (click or drop here)"}
          </strong>
          <span style={{ color: "var(--muted)", fontSize: "12px" }}>
            Accepted: .jpg, .jpeg, .png · Max 10 frames per batch
          </span>
        </div>
      </div>

      {/* Numbered Chronological Frame List */}
      {files.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 4px",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                textTransform: "uppercase",
                letterSpacing: "0.6px",
                color: "var(--muted)",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <ArrowUpDown size={13} /> Frame Sequence (Chronological Order)
            </span>
            <span style={{ fontSize: "11px", color: "var(--muted)" }}>
              Use arrows to reorder frames before analysis
            </span>
          </div>

          <div
            style={{
              maxHeight: "360px",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              paddingRight: "4px",
            }}
          >
            {files.map((file, idx) => {
              const frameNumStr = String(idx + 1).padStart(2, "0");
              const sizeKb = (file.size / 1024).toFixed(1);
              const preview = thumbnails[idx];

              return (
                <div
                  key={`${file.name}-${idx}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "12px",
                    background: "var(--panel)",
                    border: "1px solid var(--line)",
                    borderRadius: "10px",
                    padding: "8px 14px",
                    boxShadow: "0 1px 3px rgba(7, 59, 92, 0.03)",
                    transition: "all 0.15s ease",
                  }}
                >
                  {/* Left: Frame index & preview & metadata */}
                  <div style={{ display: "flex", alignItems: "center", gap: "14px", minWidth: 0 }}>
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "8px",
                        background: "var(--panel2)",
                        border: "1px solid var(--line)",
                        display: "grid",
                        placeItems: "center",
                        fontSize: "12px",
                        fontWeight: "700",
                        fontFamily: "Space Grotesk, sans-serif",
                        color: "var(--primary)",
                        flexShrink: 0,
                      }}
                    >
                      {frameNumStr}
                    </div>

                    {/* Thumbnail */}
                    <div
                      style={{
                        width: "48px",
                        height: "36px",
                        borderRadius: "6px",
                        overflow: "hidden",
                        background: "#040912",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        border: "1px solid var(--line)",
                      }}
                    >
                      {preview ? (
                        <img
                          src={preview}
                          alt={`Frame ${frameNumStr}`}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        />
                      ) : (
                        <FileImage size={18} color="var(--muted)" />
                      )}
                    </div>

                    <div style={{ minWidth: 0 }}>
                      <strong
                        style={{
                          display: "block",
                          fontSize: "13px",
                          color: "var(--text-dark)",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                        title={file.name}
                      >
                        {file.name}
                      </strong>
                      <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                        Frame {idx + 1} · {sizeKb} KB
                      </span>
                    </div>
                  </div>

                  {/* Right: Reorder and remove controls */}
                  <div style={{ display: "flex", alignItems: "center", gap: "4px", flexShrink: 0 }}>
                    <button
                      type="button"
                      disabled={disabled || idx === 0}
                      onClick={() => moveFileUp(idx)}
                      className="icon-btn"
                      style={{
                        padding: "5px",
                        opacity: disabled || idx === 0 ? 0.35 : 1,
                        cursor: disabled || idx === 0 ? "not-allowed" : "pointer",
                      }}
                      title="Move up (earlier in time)"
                    >
                      <ChevronUp size={16} />
                    </button>

                    <button
                      type="button"
                      disabled={disabled || idx === files.length - 1}
                      onClick={() => moveFileDown(idx)}
                      className="icon-btn"
                      style={{
                        padding: "5px",
                        opacity: disabled || idx === files.length - 1 ? 0.35 : 1,
                        cursor: disabled || idx === files.length - 1 ? "not-allowed" : "pointer",
                      }}
                      title="Move down (later in time)"
                    >
                      <ChevronDown size={16} />
                    </button>

                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => removeFile(idx)}
                      className="icon-btn"
                      style={{
                        padding: "5px",
                        color: "var(--red)",
                        opacity: disabled ? 0.35 : 1,
                        marginLeft: "4px",
                      }}
                      title="Remove frame"
                    >
                      <X size={16} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
