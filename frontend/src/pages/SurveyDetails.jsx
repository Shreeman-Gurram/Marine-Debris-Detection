import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  Map,
  Table2,
  BarChart3,
} from "lucide-react";

import SectionHeader from "../components/SectionHeader";
import Badge from "../components/Badge";
import SonarViewer from "../components/SonarViewer";
import MapPreview from "../components/MapPreview";
import { mockSurvey } from "../services/api";

export default function SurveyDetails() {
  const [tab, setTab] = useState("sonar");
  const { surveyId } = useParams();

  const survey = {
    ...mockSurvey,
    id: surveyId,
  };

  return (
    <div>
      <Link className="back-link" to="/dashboard">
        <ArrowLeft size={16} />
        Back to dashboard
      </Link>

      <div className="page-heading">
        <div>
          <span className="eyebrow">SURVEY DETAILS</span>
          <h1>{survey.name}</h1>
          <p>
            {survey.location} ┬╖ {survey.date} ┬╖{" "}
            <Badge tone="success">{survey.status}</Badge>
          </p>
        </div>

        <button className="secondary-btn">
          <Download size={17} />
          Export report
        </button>
      </div>

      <div className="detail-tabs">
        <button
          className={tab === "sonar" ? "active" : ""}
          onClick={() => setTab("sonar")}
        >
          <Map size={17} />
          Sonar view
        </button>

        <button
          className={tab === "map" ? "active" : ""}
          onClick={() => setTab("map")}
        >
          <Map size={17} />
          Map view
        </button>

        <button
          className={tab === "table" ? "active" : ""}
          onClick={() => setTab("table")}
        >
          <Table2 size={17} />
          Detection table
        </button>

        <button
          className={tab === "analytics" ? "active" : ""}
          onClick={() => setTab("analytics")}
        >
          <BarChart3 size={17} />
          Analytics
        </button>
      </div>

      {tab === "sonar" && (
        <section className="panel">
          <SectionHeader
            title="Uploaded sonar image"
            subtitle="AI detection boxes will appear here after real detection results are available"
          />

          <SonarViewer
            imageUrl={survey.imageUrl}
            detections={[]}
          />
        </section>
      )}

      {tab === "map" && (
        <section className="panel">
          <SectionHeader
            title="Survey map"
            subtitle="Locations are shown using available sonar coordinates"
          />
          <MapPreview detections={survey.detections} />
        </section>
      )}

      {tab === "table" && (
        <section className="panel">
          <SectionHeader
            title="Detection table"
            subtitle={`${survey.detections.length} detections in this survey`}
          />
          <DetectionTable detections={survey.detections} />
        </section>
      )}

      {tab === "analytics" && (
        <Analytics detections={survey.detections} />
      )}
    </div>
  );
}

function DetectionTable({ detections }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Object class</th>
            <th>Confidence</th>
            <th>Priority</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>

        <tbody>
          {detections.map((d) => (
            <tr key={d.id}>
              <td>
                <strong>{d.id}</strong>
              </td>
              <td>{d.type}</td>
              <td>{d.confidence}%</td>
              <td>
                <Badge
                  tone={
                    d.priority === "High"
                      ? "danger"
                      : d.priority === "Medium"
                      ? "warning"
                      : "neutral"
                  }
                >
                  {d.priority}
                </Badge>
              </td>
              <td>
                <Badge
                  tone={
                    d.status === "Confirmed"
                      ? "success"
                      : d.status === "Rejected"
                      ? "danger"
                      : "warning"
                  }
                >
                  {d.status}
                </Badge>
              </td>
              <td>
                <Link
                  className="text-link"
                  to={`/anomalies/${d.id}`}
                >
                  Review
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Analytics({ detections }) {
  const avg =
    detections.length > 0
      ? Math.round(
          detections.reduce((a, d) => a + d.confidence, 0) /
            detections.length
        )
      : 0;

  return (
    <div className="analytics-grid">
      <div className="panel">
        <SectionHeader
          title="Model confidence"
          subtitle="Average confidence across detections"
        />

        <div className="big-number">{avg}%</div>

        <div className="progress">
          <span style={{ width: `${avg}%` }} />
        </div>
      </div>

      <div className="panel">
        <SectionHeader title="Priority distribution" />

        <div className="bars">
          {["High", "Medium", "Low"].map((priority) => {
            const count = detections.filter(
              (d) => d.priority === priority
            ).length;

            const percentage =
              detections.length > 0
                ? (count / detections.length) * 100
                : 0;

            return (
              <div className="bar-row" key={priority}>
                <span>{priority}</span>

                <div className="bar">
                  <i style={{ width: `${percentage}%` }} />
                </div>

                <b>{count}</b>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
