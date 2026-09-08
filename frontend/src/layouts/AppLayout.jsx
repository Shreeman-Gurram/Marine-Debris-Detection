// src/layouts/AppLayout.jsx
// SONARIS App Shell — no authentication. Opens directly to Dashboard.
import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { Menu, X, Bell, Activity } from "lucide-react";
import Logo from "../components/Logo";
import { navItems } from "../utils/constants";

export default function AppLayout() {
  const [open, setOpen] = useState(false);

  return (
    <div className="app-shell">
      {/* ── Sidebar ──────────────────────────────── */}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="sidebar-top">
          <Logo />
          <button className="icon-btn mobile-close" onClick={() => setOpen(false)}>
            <X size={20} />
          </button>
        </div>

        {/* System status badge */}
        <div className="workspace">
          <span className="status-dot" />
          <span className="status-label">SYSTEM ONLINE</span>
        </div>

        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  [isActive ? "active" : "", item.placeholder ? "nav-placeholder" : ""].join(" ").trim()
                }
                title={item.placeholder ? "Coming soon" : item.label}
              >
                <Icon size={18} />
                {item.label}
                {item.placeholder && <span className="nav-soon">Soon</span>}
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="help-card">
            <strong>SONARIS v0.3</strong>
            <span>Marine Intelligence Platform · SIH 2026</span>
          </div>
        </div>
      </aside>

      {open && <div className="overlay" onClick={() => setOpen(false)} />}

      {/* ── Main area ────────────────────────────── */}
      <main className="main-area">
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setOpen(true)}>
            <Menu size={20} />
          </button>

          <div className="topbar-center">
            <Activity size={14} className="topbar-pulse" />
            <span className="topbar-status">SYSTEM ONLINE</span>
          </div>

          <div className="topbar-actions">
            <Link to="/alerts" className="icon-btn" title="View Priority Alerts">
              <Bell size={19} />
            </Link>
          </div>
        </header>

        <div className="page-content">
          <Outlet />
        </div>

        {/* Decorative marine wave footer */}
        <div className="marine-wave-footer" aria-hidden="true">
          <svg viewBox="0 0 1440 80" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
            <path d="M0,32L60,42.7C120,53,240,75,360,69.3C480,64,600,32,720,26.7C840,21,960,43,1080,48C1200,53,1320,43,1380,37.3L1440,32L1440,80L1380,80C1320,80,1200,80,1080,80C960,80,840,80,720,80C600,80,480,80,360,80C240,80,120,80,60,80L0,80Z" fill="rgba(21, 155, 211, 0.05)" />
            <path d="M0,48L60,53.3C120,59,240,69,360,64C480,59,600,37,720,32C840,27,960,37,1080,42.7C1200,48,1320,48,1380,48L1440,48L1440,80L1380,80C1320,80,1200,80,1080,80C960,80,840,80,720,80C600,80,480,80,360,80C240,80,120,80,60,80L0,80Z" fill="rgba(11, 131, 198, 0.04)" />
          </svg>
        </div>
      </main>
    </div>
  );
}
