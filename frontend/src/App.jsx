// src/App.jsx
// SONARIS — Marine Intelligence Platform
// No authentication — opens directly at Dashboard.
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import NewSurvey from "./pages/NewSurvey";
import AnalysisResult from "./pages/AnalysisResult";
import Reports from "./pages/Reports";
import Alerts from "./pages/Alerts";
import DetectionMap from "./pages/DetectionMap";
import SurveyHistory from "./pages/SurveyHistory";
import Analytics from "./pages/Analytics";
import Placeholder from "./pages/Placeholder";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/"                     element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard"            element={<Dashboard />} />
        <Route path="/surveys/new"          element={<NewSurvey />} />
        <Route path="/analysis/:analysisId" element={<AnalysisResult />} />
        <Route path="/surveys/:analysisId"  element={<AnalysisResult />} />
        <Route path="/reports"              element={<Reports />} />
        <Route path="/alerts"               element={<Alerts />} />
        <Route path="/map"                  element={<DetectionMap />} />
        <Route path="/history"              element={<SurveyHistory />} />
        <Route path="/analytics"            element={<Analytics />} />
        <Route path="/settings"             element={<Placeholder title="Settings" icon="Settings" />} />

        <Route path="*"                     element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
