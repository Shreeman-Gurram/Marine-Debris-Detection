import { ScanSearch } from "lucide-react";

export default function SonarViewer({
  detections = [],
  imageUrl,
}) {
  return (
    <div className="sonar-viewer">
      {imageUrl ? (
        <img
          src={imageUrl}
          alt="Uploaded side-scan sonar"
        />
      ) : (
        <div className="sonar-art">
          <div className="sonar-lines" />
          <div className="sonar-object object-one" />
          <div className="sonar-object object-two" />
          <div className="sonar-object object-three" />
        </div>
      )}

      <div className="sonar-overlay-label">
        <ScanSearch size={15} />
        <span>Side-scan sonar view</span>
      </div>

      {detections.map((item) => (
        <div
          className="detection-box"
          key={item.id}
          style={{
            left: `${item.x}%`,
            top: `${item.y}%`,
          }}
        >
          <span>{item.id}</span>
        </div>
      ))}
    </div>
  );
}
