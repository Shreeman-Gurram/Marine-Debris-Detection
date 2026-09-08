// src/pages/Placeholder.jsx
import {
  Bell,
  Map,
  History,
  BarChart3,
  Settings,
  Construction,
  PlusCircle,
} from "lucide-react";
import { Link } from "react-router-dom";
import SectionHeader from "../components/SectionHeader";

const ICON_MAP = {
  Bell,
  Map,
  History,
  BarChart3,
  Settings,
};

export default function Placeholder({ title = "Module", icon = "Construction" }) {
  const IconComponent = ICON_MAP[icon] || Construction;

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">MODULE</span>
          <h1>{title}</h1>
          <p>SONARIS Marine Intelligence Platform — SIH 2026</p>
        </div>
        <Link to="/surveys/new" className="primary-btn">
          <PlusCircle size={18} /> New Survey
        </Link>
      </div>

      <section className="panel" style={{ textAlign: "center", padding: "60px 20px" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: "68px",
            height: "68px",
            borderRadius: "16px",
            background: "rgba(73, 183, 255, 0.1)",
            color: "var(--primary)",
            marginBottom: "20px",
            border: "1px solid rgba(73, 183, 255, 0.2)",
          }}
        >
          <IconComponent size={34} />
        </div>
        <h2 style={{ fontSize: "20px", fontWeight: 600, margin: "0 0 10px 0" }}>
          {title} Module
        </h2>
        <p style={{ color: "var(--muted)", maxWidth: "460px", margin: "0 auto 24px auto", lineHeight: 1.6 }}>
          This component is staged for the upcoming SONARIS milestone. It integrates directly with
          the MongoDB Atlas intelligence archive and DRISHTI anomaly registry.
        </p>
        <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
          <Link to="/dashboard" className="secondary-btn">
            Return to Dashboard
          </Link>
          <Link to="/surveys/new" className="primary-btn">
            Upload Sonar Imagery
          </Link>
        </div>
      </section>
    </div>
  );
}
