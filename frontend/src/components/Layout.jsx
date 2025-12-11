import React, { useEffect, useState } from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";

/* Inline SVG icons to avoid extra dependencies */
const IconHome = (props) => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" {...props}>
    <path d="M3 10.5L12 4l9 6.5" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M4 21V11.5h16V21" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const IconDiagnosis = (props) => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" {...props}>
    <path d="M9 7h6M9 11h6M9 15h6" strokeLinecap="round" strokeLinejoin="round" />
    <rect x="3" y="3" width="18" height="18" rx="3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const IconCattle = (props) => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" {...props}>
    <path d="M4 15c0-3 3-5 6-5s6 2 6 5" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M8 6v-2m8 2v-2" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M6 18v1a1 1 0 0 0 1 1h2" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M18 18v1a1 1 0 0 1-1 1h-2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const IconHistory = (props) => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" {...props}>
    <path d="M21 12a9 9 0 1 1-3-6.7L21 12z" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M12 7v5l3 1" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const IconMail = (props) => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5" {...props}>
    <path d="M3 8.5v7a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M21 8.5L12 14 3 8.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

function NavItem({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        "inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition " +
        (isActive ? "bg-brand-100 text-brand-800 shadow-sm" : "text-gray-700 hover:bg-gray-50")
      }
    >
      <span className="text-lg leading-none text-current"><Icon /></span>
      <span>{label}</span>
    </NavLink>
  );
}

export default function Layout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    // update auth state based on token presence when location changes
    const token = localStorage.getItem("access_token");
    setAuthenticated(!!token);
  }, [location]);

  const handleLogin = () => {
    navigate("/login");
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    // optionally remove refresh token etc.
    setAuthenticated(false);
    // Redirect to home after logout
    navigate("/");
    // force reload to reset API interceptors if needed
    window.location.reload();
  };

  return (
    <div className="min-h-screen flex flex-col bg-[linear-gradient(180deg,#f7fdf7,#f0f9f0)]">
      {/* Top minimal header with brand + auth button */}
      <div className="bg-white/95 border-b">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div>
            <div className="text-lg font-extrabold text-brand-600">AI Cattle Disease Diagnosis</div>
            <div className="text-xs text-gray-500">Dawana Farm</div>
          </div>

          <div className="flex items-center gap-3">
            {authenticated ? (
              <button onClick={handleLogout} className="btn px-3 py-1 text-sm bg-red-100 text-red-700 rounded-md">
                Logout
              </button>
            ) : (
              <button onClick={handleLogin} className="btn btn-primary px-3 py-1 text-sm">
                Login
              </button>
            )}
          </div>
        </div>

        {/* Navigation bar */}
        <nav className="bg-white">
          <div className="max-w-6xl mx-auto px-6">
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-4">
                <NavItem to="/dashboard" icon={IconHome} label="Dashboard" />
                <NavItem to="/diagnosis/new" icon={IconDiagnosis} label="New Diagnosis" />
                <NavItem to="/cattle" icon={IconCattle} label="Cattle Records" />
                <NavItem to="/history" icon={IconHistory} label="Diagnosis History" />
              </div>

              <div className="flex items-center gap-3">
                <NavLink to="/profile" className="px-3 py-1 rounded-md text-sm text-gray-700 hover:bg-gray-50">
                  Profile
                </NavLink>
                <NavLink to="/settings" className="px-3 py-1 rounded-md text-sm text-gray-700 hover:bg-gray-50">
                  Settings
                </NavLink>
              </div>
            </div>
          </div>
        </nav>
      </div>

      {/* Cards below nav (profile, description, quick links) */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {/* PROFILE CARD */}
          <div className="card flex flex-col gap-3">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 font-bold text-lg">
                AD
              </div>
              <div>
                <div className="text-lg font-bold text-brand-600">AI Cattle Disease Diagnosis</div>
                <div className="text-sm text-gray-600">Dawana Farm</div>
              </div>
            </div>

            <div className="mt-2">
              <div className="text-sm font-semibold">Lee Royn Dawana</div>
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                <span className="inline-flex items-center gap-1"><IconMail /> leeroyndawana26@gmail.com</span>
              </div>
            </div>
          </div>

          {/* DESCRIPTION CARD */}
          <div className="card md:col-span-1 md:col-start-2">
            <div className="text-sm text-gray-700">
              <strong className="block mb-2">Advanced AI-powered system for early detection and diagnosis of cattle diseases.</strong>
              Upload images, input symptoms, and get instant diagnostic recommendations. Designed for farm-level use and veterinary review.
            </div>
          </div>

          {/* QUICK LINKS CARD */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold">Quick Links</div>
              <div className="text-xs text-gray-400">Fast access</div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <NavItem to="/dashboard" icon={IconHome} label="Home" />
              <NavItem to="/diagnosis/new" icon={IconDiagnosis} label="New Diagnosis" />
              <NavItem to="/cattle" icon={IconCattle} label="Cattle Records" />
              <NavItem to="/history" icon={IconHistory} label="Diagnosis History" />
            </div>

            <div className="mt-4">
              <NavLink to="/diagnosis/new" className="btn btn-primary w-full text-center">
                New Diagnosis
              </NavLink>
            </div>
          </div>
        </div>
      </div>

      {/* Main content area (children pages) */}
      <main className="flex-1 p-6">
        <div className="max-w-6xl mx-auto">{children}</div>
      </main>

      {/* Footer */}
      <footer className="bg-white/95 border-t">
        <div className="max-w-6xl mx-auto px-6 py-4 text-xs text-gray-500 flex items-center justify-between">
          <div>© {new Date().getFullYear()} AI Cattle Disease Diagnosis — Dawana Farm</div>
          <div className="text-right">
            <div>System Status: <span className="font-medium text-green-600">Active</span></div>
          </div>
        </div>
      </footer>
    </div>
  );
}
