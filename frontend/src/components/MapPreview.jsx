import { MapPin } from "lucide-react";

export default function MapPreview({ detections = [] }) {
  return (
    <div className="map-preview">
      <div className="map-grid" />
      <div className="map-label">Relative survey coordinates</div>
      {detections.map((item) => (
        <div
          className="map-pin"
          key={item.id}
          style={{ left: `${item.x}%`, top: `${item.y}%` }}
          title={item.type}
        >
          <MapPin size={24} />
        </div>
      ))}
      <div className="map-scale">N Γåæ &nbsp; 100 m</div>
    </div>
  );
}
