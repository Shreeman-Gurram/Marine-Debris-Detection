import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { CheckCircle2, Cpu, Database, ScanLine } from "lucide-react";
import { mockSurvey } from "../services/api";

const steps = [{label:"Validating imagery", icon:Database}, {label:"Preprocessing sonar", icon:ScanLine}, {label:"Running AI detection", icon:Cpu}, {label:"Preparing results", icon:CheckCircle2}];

export default function Processing() {
  const navigate = useNavigate(); const location = useLocation(); const [current, setCurrent] = useState(0);
  useEffect(() => { const timer = setInterval(() => setCurrent(v => v < steps.length ? v + 1 : v), 900); return () => clearInterval(timer); }, []);
  useEffect(() => { if (current === steps.length) { const t = setTimeout(() => navigate(`/surveys/${mockSurvey.id}`), 700); return () => clearTimeout(t); } }, [current, navigate]);
  return <div className="processing-page"><div className="processing-card"><div className="processing-orb"><ScanLine size={38}/></div><span className="eyebrow">SURVEY PROCESSING</span><h1>Analyzing sonar imagery</h1><p className="muted">{location.state?.form?.name || "Your survey"} is being processed. You can keep this tab open.</p><div className="processing-steps">{steps.map((step, i) => { const Icon = step.icon; return <div className={`processing-step ${i < current ? "done" : i === current ? "active" : ""}`} key={step.label}><span className="step-icon"><Icon size={18}/></span><span>{step.label}</span>{i < current && <CheckCircle2 size={17}/>}</div>})}</div><div className="progress large"><span style={{width:`${Math.min(current / steps.length * 100, 100)}%`}} /></div><small>{Math.min(Math.round(current / steps.length * 100),100)}% complete</small></div></div>;
}
