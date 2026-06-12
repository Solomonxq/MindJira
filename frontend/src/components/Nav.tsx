import { Link, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/auth";

const navItems = [
  { path: "/", label: "Dashboard" },
  { path: "/enrich", label: "Enrich Description" },
  { path: "/test-cases", label: "Test Cases" },
  { path: "/sprint-summary", label: "Sprint Summary" },
  { path: "/jobs", label: "Jobs" },
];

export function Nav() {
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 justify-between">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary-600 flex items-center justify-center text-white font-bold">
                MJ
              </div>
              <span className="text-lg font-semibold text-gray-900">MindJira</span>
            </Link>
            <div className="hidden md:flex gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    location.pathname === item.path
                      ? "bg-primary-50 text-primary-700"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-4">
            {user && (
              <span className="text-sm text-gray-600 hidden sm:block">
                {user.email}
              </span>
            )}
            <button onClick={logout} className="btn-secondary text-xs">
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
