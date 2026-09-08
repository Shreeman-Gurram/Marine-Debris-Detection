// src/pages/DetectionMap.jsx
// Interactive Detection Map for SONARIS Marine Intelligence
// Powered by React-Leaflet + OpenStreetMap
import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  useMap,
} from "react-leaflet";
import {
  AlertTriangle,
  ArrowUpRight,
  Compass,
  Crosshair,
  ExternalLink,
  Layers,
  MapPin,
  Maximize2,
  Radar,
  RefreshCw,
  ScanLine,
  ShieldAlert,
  SlidersHorizontal,
  Waves,
} from "lucide-react";
import SectionHeader from "../components/SectionHeader";
import Badge from "../components/Badge";
import { getRecentSurveys, evidenceUrl } from "../services/api";
import { extractAlertsFromSurveys, formatAnomalyName, formatAlertDate } from "../utils/alerts";
import { RISK_TONE } from "../utils/constants";

// Helper component to auto-fit map bounds to all located markers
function MapBoundsController({ markers }) {
  const map = useMap();

  useEffect(() => {
    if (markers.length === 1) {
      map.setView([markers[0].latitude, markers[0].longitude], 14);
    } else if (markers.length > 1) {
      const bounds = L.latLngBounds(markers.map((m) => [m.latitude, m.longitude]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
    }
  }, [markers, map]);

  return null;
}

// Custom DivIcon generator to color-code markers by priority with radar pulse
function createPriorityIcon(riskLevel) {
  const isHigh = riskLevel === "CRITICAL" || riskLevel === "HIGH";
  const isMedium = riskLevel === "MEDIUM";
  const color = isHigh ? "#f36d7a" : isMedium ? "#f4b84b" : "#49b7ff";

  return L.divIcon({
    className: "custom-sonar-marker",
    html: `
      <div style="
        position: relative;
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="
          position: absolute;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: ${color};
          opacity: 0.3;
          animation: pulse-ring 2s infinite ease-out;
        "></div>
        <div style="
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: ${color};
          border: 2px solid #ffffff;
          box-shadow: 0 0 10px ${color};
          z-index: 2;
        "></div>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
}

export default function DetectionMap() {
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDetection, setSelectedDetection] = useState(null);

  async function loadMapData() {
    try {
      setLoading(true);
      const data = await getRecentSurveys(50);
      setSurveys(data || []);
      setError(null);
    } catch (err) {
      console.error("Failed to load map surveys:", err);
      setError(err.message || "Failed to load detection map data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMapData();
  }, []);

  const allAlerts = useMemo(() => extractAlertsFromSurveys(surveys), [surveys]);

  // Separate located (GPS) vs unlocated (local sonar) detections
  const locatedDetections = useMemo(
    () => allAlerts.filter((a) => a.hasGps && !isNaN(a.latitude) && !isNaN(a.longitude)),
    [allAlerts]
  );

  const unlocatedDetections = useMemo(
    () => allAlerts.filter((a) => !a.hasGps || isNaN(a.latitude) || isNaN(a.longitude)),
    [allAlerts]
  );

  // Summary counts
  const stats = useMemo(() => {
    let high = 0;
    let medium = 0;
    let low = 0;

    locatedDetections.forEach((d) => {
      if (d.riskLevel === "CRITICAL" || d.riskLevel === "HIGH") high++;
      else if (d.riskLevel === "MEDIUM") medium++;
      else low++;
    });

    return {
      totalLocated: locatedDetections.length,
      high,
      medium,
      low,
      totalUnlocated: unlocatedDetections.length,
    };
  }, [locatedDetections, unlocatedDetections]);

  // Center coordinates: if any located markers exist, center on the first; else default marine coordinates (Bay of Bengal / Indian Ocean)
  const defaultCenter = useMemo(() => {
    if (locatedDetections.length > 0) {
      return [locatedDetections[0].latitude, locatedDetections[0].longitude];
    }
    return [13.0827, 80.2707]; // Chennai / Bay of Bengal marine corridor
  }, [locatedDetections]);

  return (
    <div>
      {/* Page Heading */}
      <div className="page-heading">
        <div>
          <span className="eyebrow">GEOSPATIAL SITUATIONAL AWARENESS</span>
          <h1>Detection Map</h1>
          <p>Real-time georeferenced tracking of seabed contacts, obstacles, and pipeline anomalies</p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            className="secondary-btn"
            onClick={loadMapData}
            disabled={loading}
            style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh Map
          </button>
          <Link to="/alerts" className="secondary-btn" style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
            <Radar size={15} /> Priority Alerts
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

      {/* TOP SUMMARY BAR */}
      <div className="kpi-summary-grid" style={{ marginBottom: "20px" }}>
        <div className="kpi-card">
          <div className="kpi-label">
            <span>Total Located (GPS)</span>
            <MapPin size={15} color="var(--green)" />
          </div>
          <div className="kpi-value">
            {stats.totalLocated}
            <span style={{ fontSize: "12px", color: "var(--muted)", fontWeight: 400 }}>plotted</span>
          </div>
          <div className="kpi-sub">WGS84 GNSS validated</div>
        </div>

        <div className="kpi-card kpi-card-high" style={{ borderColor: stats.high > 0 ? "rgba(224, 76, 90, 0.4)" : "" }}>
          <div className="kpi-label">
            <span>High Priority (GPS)</span>
            <ShieldAlert size={15} color="var(--red)" />
          </div>
          <div className="kpi-value" style={{ color: stats.high > 0 ? "var(--red)" : "var(--text)" }}>
            {stats.high}
          </div>
          <div className="kpi-sub">🔴 High threat markers</div>
        </div>

        <div className="kpi-card" style={{ borderColor: stats.medium > 0 ? "rgba(217, 131, 36, 0.4)" : "" }}>
          <div className="kpi-label">
            <span>Medium Priority (GPS)</span>
            <AlertTriangle size={15} color="var(--amber)" />
          </div>
          <div className="kpi-value" style={{ color: stats.medium > 0 ? "var(--amber)" : "var(--text)" }}>
            {stats.medium}
          </div>
          <div className="kpi-sub">🟠 Medium threat markers</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Low Priority (GPS)</span>
            <Layers size={15} color="var(--primary)" />
          </div>
          <div className="kpi-value">
            {stats.low}
          </div>
          <div className="kpi-sub">🔵 Low threat markers</div>
        </div>

        <div className="kpi-card" style={{ borderColor: stats.totalUnlocated > 0 ? "rgba(217, 131, 36, 0.3)" : "" }}>
          <div className="kpi-label">
            <span>Unlocated Contacts</span>
            <Compass size={15} color="var(--amber)" />
          </div>
          <div className="kpi-value" style={{ color: stats.totalUnlocated > 0 ? "var(--amber)" : "var(--text)" }}>
            {stats.totalUnlocated}
          </div>
          <div className="kpi-sub">Local sonar grid frame</div>
        </div>
      </div>

      {/* MAIN MAP WORKSPACE & SELECTED DETECTION GRID */}
      <div className="content-grid two-one" style={{ marginBottom: "24px", alignItems: "stretch" }}>
        {/* Left: Map Container */}
        <section className="panel" style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          {/* Map Controls Header */}
          <div
            style={{
              padding: "10px 16px",
              background: "var(--panel-alt)",
              borderBottom: "1px solid var(--line)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, color: "var(--text)" }}>
              <Compass size={16} color="var(--primary)" />
              <span>SONARIS Geospatial Radar Viewport</span>
            </div>
            <span style={{ color: "var(--muted)", fontSize: "11px" }}>
              OpenStreetMap Telemetry Tile Layer
            </span>
          </div>

          {/* Leaflet Map Stage */}
          <div style={{ position: "relative", height: "460px", width: "100%", background: "#060e18" }}>
            <MapContainer
              center={defaultCenter}
              zoom={locatedDetections.length > 0 ? 13 : 6}
              scrollWheelZoom={true}
              style={{ height: "100%", width: "100%" }}
            >
              {/* OpenStreetMap Tile Layer */}
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {/* Fit Bounds Controller */}
              <MapBoundsController markers={locatedDetections} />

              {/* Real Located Detection Markers with Uncertainty Circles */}
              {locatedDetections.map((det) => {
                const isHigh = det.riskLevel === "CRITICAL" || det.riskLevel === "HIGH";
                const isMedium = det.riskLevel === "MEDIUM";
                const markerColor = isHigh ? "#f36d7a" : isMedium ? "#f4b84b" : "#49b7ff";
                const icon = createPriorityIcon(det.riskLevel);
                const uncertainty = det.uncertainty_m != null && det.uncertainty_m > 0 ? det.uncertainty_m : null;

                return (
                  <div key={det.id}>
                    {/* Positional Uncertainty Circle */}
                    {uncertainty && (
                      <Circle
                        center={[det.latitude, det.longitude]}
                        radius={uncertainty}
                        pathOptions={{
                          color: markerColor,
                          fillColor: markerColor,
                          fillOpacity: 0.12,
                          weight: 1.5,
                          dashArray: "4, 6",
                        }}
                      />
                    )}

                    {/* Target Contact Marker */}
                    <Marker
                      position={[det.latitude, det.longitude]}
                      icon={icon}
                      eventHandlers={{
                        click: () => setSelectedDetection(det),
                      }}
                    >
                      <Popup className="sonaris-leaflet-popup">
                        <div style={{ minWidth: "190px", fontSize: "12px", color: "#fff" }}>
                          <strong style={{ fontSize: "13px", display: "block", color: "var(--primary)", marginBottom: "4px" }}>
                            {formatAnomalyName(det.className)}
                          </strong>
                          <div style={{ display: "flex", gap: "6px", marginBottom: "8px" }}>
                            <Badge tone={RISK_TONE[det.riskLevel]}>{det.riskLevel}</Badge>
                            <span style={{ fontSize: "11px", color: "var(--muted)", alignSelf: "center" }}>
                              {det.confidence != null ? `${(det.confidence * 100).toFixed(1)}%` : ""}
                            </span>
                          </div>

                          <div style={{ fontSize: "11px", lineHeight: "1.5", color: "#c8d6e8", marginBottom: "8px" }}>
                            <div>Risk Score: <strong>{det.riskScore != null ? det.riskScore.toFixed(2) : "N/A"}</strong></div>
                            <div>Lat: <strong>{det.latitude.toFixed(6)}°</strong></div>
                            <div>Lon: <strong>{det.longitude.toFixed(6)}°</strong></div>
                            <div>Uncertainty: <strong>±{det.uncertainty_m ?? 5} m</strong></div>
                            <div>Survey: <code>{det.surveyFilename}</code></div>
                          </div>

                          <Link
                            to={`/analysis/${det.surveyId}`}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              color: "var(--primary)",
                              fontWeight: 600,
                              textDecoration: "underline",
                              fontSize: "11px",
                            }}
                          >
                            VIEW ANALYSIS <ArrowUpRight size={12} />
                          </Link>
                        </div>
                      </Popup>
                    </Marker>
                  </div>
                );
              })}
            </MapContainer>

            {/* Informational overlay banner if 0 located detections */}
            {locatedDetections.length === 0 && (
              <div
                style={{
                  position: "absolute",
                  bottom: "20px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  background: "rgba(8, 17, 31, 0.9)",
                  border: "1px solid rgba(244, 184, 75, 0.4)",
                  padding: "8px 16px",
                  borderRadius: "8px",
                  zIndex: 1000,
                  fontSize: "12px",
                  color: "#dbe9f7",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  boxShadow: "0 4px 14px rgba(0,0,0,0.5)",
                }}
              >
                <AlertTriangle size={15} color="var(--amber)" />
                <span>
                  No GPS coordinates in current dataset. Detections without vessel GNSS are cataloged in <strong>Unlocated Detections</strong> below.
                </span>
              </div>
            )}

            {/* MAP LEGEND OVERLAY */}
            <div
              style={{
                position: "absolute",
                top: "14px",
                right: "14px",
                background: "rgba(255, 255, 255, 0.95)",
                backdropFilter: "blur(6px)",
                border: "1px solid var(--line)",
                borderRadius: "8px",
                padding: "8px 12px",
                zIndex: 1000,
                fontSize: "11px",
                display: "flex",
                flexDirection: "column",
                gap: "5px",
                boxShadow: "var(--shadow-sm)",
                color: "var(--text)",
              }}
            >
              <span style={{ fontWeight: 600, color: "var(--text)", marginBottom: "2px", textTransform: "uppercase", fontSize: "10px", letterSpacing: "0.5px" }}>
                Map Legend
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "var(--red)" }}></span>
                <span>🔴 HIGH Priority Contact</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "var(--amber)" }}></span>
                <span>🟠 MEDIUM Priority Contact</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "var(--primary)" }}></span>
                <span>🔵 LOW Priority Contact</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", borderTop: "1px solid var(--line)", paddingTop: "4px" }}>
                <span style={{ width: "10px", height: "10px", borderRadius: "50%", border: "1.5px dashed var(--muted)", display: "inline-block" }}></span>
                <span>⭕ Positional Uncertainty</span>
              </div>
            </div>
          </div>
        </section>

        {/* Right: Selected Detection Deep-Dive Card */}
        <section className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <SectionHeader
            title="Selected Detection"
            subtitle={selectedDetection ? formatAnomalyName(selectedDetection.className) : "Click any marker to inspect"}
          />

          {selectedDetection ? (
            <div style={{ display: "grid", gap: "14px", marginTop: "10px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  background: "var(--panel-alt)",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  border: "1px solid var(--line)",
                }}
              >
                <div>
                  <span style={{ fontSize: "11px", color: "var(--muted)", display: "block" }}>Target Class</span>
                  <strong style={{ fontSize: "14px", color: "var(--text)" }}>
                    {formatAnomalyName(selectedDetection.className)}
                  </strong>
                </div>
                <Badge tone={RISK_TONE[selectedDetection.riskLevel]}>
                  {selectedDetection.riskLevel}
                </Badge>
              </div>

              {/* Confidence & Risk */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div style={{ background: "var(--panel-alt)", padding: "10px", borderRadius: "8px", border: "1px solid var(--line)" }}>
                  <span style={{ fontSize: "11px", color: "var(--muted)", display: "block" }}>Confidence</span>
                  <strong style={{ color: "var(--primary)", fontSize: "15px" }}>
                    {selectedDetection.confidence != null ? `${(selectedDetection.confidence * 100).toFixed(1)}%` : "N/A"}
                  </strong>
                </div>
                <div style={{ background: "var(--panel-alt)", padding: "10px", borderRadius: "8px", border: "1px solid var(--line)" }}>
                  <span style={{ fontSize: "11px", color: "var(--muted)", display: "block" }}>Risk Threat Score</span>
                  <strong style={{ color: "var(--red)", fontSize: "15px" }}>
                    {selectedDetection.riskScore != null ? Number(selectedDetection.riskScore).toFixed(2) : "0.00"}
                  </strong>
                </div>
              </div>

              {/* Coordinates block */}
              <div
                style={{
                  background: selectedDetection.hasGps ? "rgba(16, 185, 129, 0.08)" : "rgba(217, 131, 36, 0.08)",
                  padding: "12px",
                  borderRadius: "8px",
                  border: `1px solid ${selectedDetection.hasGps ? "rgba(16, 185, 129, 0.25)" : "rgba(217, 131, 36, 0.25)"}`,
                  fontSize: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                  <MapPin size={15} color={selectedDetection.hasGps ? "var(--green)" : "var(--amber)"} />
                  <strong style={{ color: selectedDetection.hasGps ? "var(--green)" : "var(--amber)" }}>
                    {selectedDetection.hasGps ? "WGS84 Geolocation" : "Local Acoustic Sensor Grid"}
                  </strong>
                </div>

                {selectedDetection.hasGps ? (
                  <div style={{ display: "grid", gap: "4px" }}>
                    <div>Coordinates: <strong>{selectedDetection.latitude.toFixed(6)}°N, {selectedDetection.longitude.toFixed(6)}°E</strong></div>
                    <div>Uncertainty: <strong>±{selectedDetection.uncertainty_m ?? 5} m</strong></div>
                    <div>Coordinate Frame: <code>WGS84 GNSS</code></div>
                  </div>
                ) : (
                  <div style={{ display: "grid", gap: "4px" }}>
                    <div>Local Range: <strong>{selectedDetection.range_m != null ? `${selectedDetection.range_m.toFixed(2)} m` : "N/A"}</strong></div>
                    <div>Acoustic Bearing: <strong>{selectedDetection.bearing_deg != null ? `${selectedDetection.bearing_deg.toFixed(1)}°` : "90°"}</strong></div>
                    <div>Local Grid: <strong>X: {selectedDetection.local_x_m != null ? `${selectedDetection.local_x_m.toFixed(2)}m` : "0m"}, Y: {selectedDetection.local_y_m != null ? `${selectedDetection.local_y_m.toFixed(2)}m` : "0m"}</strong></div>
                    <div>Coordinate System: <code>local_sonar</code></div>
                  </div>
                )}
              </div>

              {/* Parent Survey Meta */}
              <div style={{ fontSize: "11px", color: "var(--muted)" }}>
                <div>Survey File: <code style={{ color: "var(--text)" }}>{selectedDetection.surveyFilename}</code></div>
                <div>Mission ID: <code>{selectedDetection.surveyId}</code></div>
                <div>Logged: {formatAlertDate(selectedDetection.timestamp)}</div>
              </div>

              {/* View Analysis CTA */}
              <Link
                to={`/analysis/${selectedDetection.surveyId}`}
                className="primary-btn"
                style={{ textAlign: "center", marginTop: "auto", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
              >
                View Full Analysis <ArrowUpRight size={15} />
              </Link>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "40px 14px", color: "var(--muted)", margin: "auto 0" }}>
              <Crosshair size={36} style={{ opacity: 0.4, margin: "0 auto 10px auto" }} />
              <p style={{ fontSize: "13px" }}>
                Select a marker on the map or an unlocated contact below to inspect target coordinates and threat metrics.
              </p>
            </div>
          )}
        </section>
      </div>

      {/* UNLOCATED DETECTIONS SECTION */}
      <section className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginBottom: "14px" }}>
          <div>
            <SectionHeader
              title="Unlocated Detections (Local Sonar Frame)"
              subtitle={`${unlocatedDetections.length} candidate contacts lacking vessel GNSS telemetry`}
            />
          </div>
          <span
            style={{
              fontSize: "11px",
              padding: "4px 10px",
              borderRadius: "6px",
              background: "rgba(244, 184, 75, 0.1)",
              border: "1px solid rgba(244, 184, 75, 0.3)",
              color: "var(--amber)",
            }}
          >
            ⚠️ Relative Sonar Swath Frame (Zero Fabricated Coordinates)
          </span>
        </div>

        {unlocatedDetections.length === 0 ? (
          <div style={{ padding: "24px", textAlign: "center", color: "var(--muted)" }}>
            <p style={{ fontSize: "13px" }}>All recorded contacts have valid GNSS coordinates plotted on the map.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "14px" }}>
            {unlocatedDetections.map((det) => {
              const tone = RISK_TONE[det.riskLevel] || "neutral";
              const isSelected = selectedDetection?.id === det.id;

              return (
                <div
                  key={det.id}
                  className="detection-card"
                  style={{
                    borderLeft: `4px solid ${
                      det.riskLevel === "CRITICAL" || det.riskLevel === "HIGH"
                        ? "var(--red)"
                        : det.riskLevel === "MEDIUM"
                        ? "var(--amber)"
                        : "var(--primary)"
                    }`,
                    background: isSelected ? "var(--panel-alt)" : "var(--panel)",
                    cursor: "pointer",
                  }}
                  onClick={() => setSelectedDetection(det)}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                      <div>
                        <strong style={{ fontSize: "14px", color: isSelected ? "var(--primary)" : "var(--text)" }}>
                          {formatAnomalyName(det.className)}
                        </strong>
                        <span style={{ fontSize: "11px", color: "var(--muted)", display: "block", marginTop: "2px" }}>
                          Survey: {det.surveyFilename}
                        </span>
                      </div>
                      <Badge tone={tone}>{det.riskLevel}</Badge>
                    </div>

                    {/* Quick Metrics */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", margin: "8px 0", background: "var(--panel-alt)", padding: "8px 10px", borderRadius: "6px", fontSize: "11px" }}>
                      <div>
                        <span style={{ color: "var(--muted)" }}>Confidence:</span>{" "}
                        <strong style={{ color: "var(--text)" }}>
                          {det.confidence != null ? `${(det.confidence * 100).toFixed(1)}%` : "N/A"}
                        </strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--muted)" }}>Risk Score:</span>{" "}
                        <strong style={{ color: "var(--text)" }}>
                          {det.riskScore != null ? Number(det.riskScore).toFixed(2) : "0.00"}
                        </strong>
                      </div>
                    </div>

                    {/* Local Sonar Geometry */}
                    <div
                      style={{
                        fontSize: "11px",
                        padding: "8px 10px",
                        borderRadius: "6px",
                        background: "rgba(217, 131, 36, 0.08)",
                        border: "1px solid rgba(217, 131, 36, 0.25)",
                        lineHeight: "1.6",
                      }}
                    >
                      <div style={{ color: "var(--amber)", fontWeight: 600, marginBottom: "2px" }}>
                        ⚠️ Geolocation unavailable
                      </div>
                      <div style={{ color: "var(--muted)" }}>
                        Coordinate frame: <code style={{ color: "var(--text)" }}>local_sonar</code>
                      </div>
                      <div style={{ color: "var(--text)" }}>
                        Range: <strong>{det.range_m != null ? `${det.range_m.toFixed(2)} m` : "N/A"}</strong> ·{" "}
                        Bearing: <strong>{det.bearing_deg != null ? `${det.bearing_deg.toFixed(1)}°` : "90.0°"}</strong>
                      </div>
                      <div style={{ color: "var(--text)" }}>
                        Local X: <strong>{det.local_x_m != null ? `${det.local_x_m.toFixed(2)} m` : "0.00 m"}</strong> ·{" "}
                        Local Y: <strong>{det.local_y_m != null ? `${det.local_y_m.toFixed(2)} m` : "0.00 m"}</strong>
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginTop: "12px",
                      paddingTop: "8px",
                      borderTop: "1px solid var(--line)",
                    }}
                  >
                    <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                      {formatAlertDate(det.timestamp)}
                    </span>
                    <Link
                      to={`/analysis/${det.surveyId}`}
                      className="text-link"
                      style={{ fontSize: "11px", display: "inline-flex", alignItems: "center", gap: "4px" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      View Analysis <ArrowUpRight size={13} />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
