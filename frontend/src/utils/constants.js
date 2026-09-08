// src/utils/constants.js
import {
  LayoutDashboard,
  PlusCircle,
  Bell,
  Map,
  History,
  BarChart3,
  FileBarChart,
  Settings,
} from "lucide-react";

export const navItems = [
  { label: "Dashboard",       path: "/dashboard",  icon: LayoutDashboard },
  { label: "New Survey",      path: "/surveys/new", icon: PlusCircle },
  { label: "Alerts",          path: "/alerts",      icon: Bell },
  { label: "Detection Map",   path: "/map",         icon: Map },
  { label: "Survey History",  path: "/history",     icon: History },
  { label: "Analytics",       path: "/analytics",   icon: BarChart3 },
  { label: "Reports",         path: "/reports",     icon: FileBarChart },
  { label: "Settings",        path: "/settings",    icon: Settings,   placeholder: true },
];

export const RISK_TONE = {
  CRITICAL: "danger",
  HIGH:     "danger",
  MEDIUM:   "warning",
  LOW:      "success",
};

export const RISK_DOT = {
  CRITICAL: "high",
  HIGH:     "high",
  MEDIUM:   "medium",
  LOW:      "low",
};
