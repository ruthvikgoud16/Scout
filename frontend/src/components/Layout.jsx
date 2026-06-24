import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Terminal, Sparkles, LogOut, LayoutDashboard } from "lucide-react";
import { useAuth } from "@/lib/auth";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const navItems = [
  { to: "/", label: "Home" },
  { to: "/hackathons", label: "Hackathons" },
  { to: "/resources", label: "Resources" },
];

export default function Layout({ children }) {
  const loc = useLocation();
  const nav = useNavigate();
  const { user, logout } = useAuth();

  return (
    <>
      <header
        className="sticky top-0 z-30 backdrop-blur-xl bg-white/75 border-b border-black/10"
        data-testid="site-header"
      >
        <div className="max-w-7xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group" data-testid="logo-link">
            <div className="w-8 h-8 grid place-items-center bg-zinc-950 text-white rounded-sm group-hover:bg-[var(--brand)] transition-colors">
              <Terminal className="w-4 h-4" />
            </div>
            <div className="leading-tight">
              <div className="display font-extrabold text-lg">OpportunityOS</div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-zinc-500">
                Hackathons · Events · Live
              </div>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1" data-testid="nav">
            {navItems.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-testid={`nav-${n.label.toLowerCase()}`}
                className={({ isActive }) =>
                  `px-3 py-1.5 text-sm font-medium border border-transparent transition-colors ${
                    isActive
                      ? "bg-zinc-950 text-white"
                      : "text-zinc-700 hover:bg-zinc-100 hover:text-zinc-950"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
            {user && (
              <NavLink
                to="/dashboard"
                data-testid="nav-dashboard"
                className={({ isActive }) =>
                  `px-3 py-1.5 text-sm font-medium border border-transparent transition-colors ${
                    isActive
                      ? "bg-zinc-950 text-white"
                      : "text-zinc-700 hover:bg-zinc-100 hover:text-zinc-950"
                  }`
                }
              >
                Dashboard
              </NavLink>
            )}
          </nav>

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className="flex items-center gap-2 hover:bg-zinc-100 px-2 py-1.5 transition-colors"
                  data-testid="user-menu-btn"
                >
                  {user.picture ? (
                    <img
                      src={user.picture}
                      alt={user.name}
                      className="w-7 h-7 rounded-full border border-zinc-200"
                    />
                  ) : (
                    <div className="w-7 h-7 grid place-items-center bg-zinc-950 text-white text-[11px] font-bold rounded-full">
                      {user.name?.[0]?.toUpperCase() || "?"}
                    </div>
                  )}
                  <span className="text-sm font-medium hidden sm:inline">
                    {user.name?.split(" ")[0]}
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="rounded-none">
                <DropdownMenuLabel className="text-xs">
                  {user.email}
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => nav("/dashboard")} data-testid="menu-dashboard">
                  <LayoutDashboard className="w-3.5 h-3.5 mr-2" /> Dashboard
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={async () => {
                    await logout();
                    nav("/");
                  }}
                  data-testid="menu-logout"
                >
                  <LogOut className="w-3.5 h-3.5 mr-2" /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="hidden sm:inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 hover:bg-zinc-100 transition-colors"
                data-testid="login-link"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 bg-zinc-950 text-white hover:bg-[var(--brand)] transition-colors"
                data-testid="signup-link"
              >
                <Sparkles className="w-3.5 h-3.5" /> Get started
              </Link>
            </div>
          )}
        </div>
        {loc.pathname !== "/" && (
          <div className="border-t border-black/5 bg-zinc-50">
            <div className="max-w-7xl mx-auto px-6 md:px-10 py-2 text-[11px] text-zinc-500 uppercase tracking-[0.18em] flex items-center gap-2">
              <span className="blink-dot" />
              Live feed · Gemini auto-curated · refresh every 6h
            </div>
          </div>
        )}
      </header>

      <main className="max-w-7xl mx-auto px-6 md:px-10 py-10 md:py-14">
        {children}
      </main>

      <footer className="border-t border-black/10 mt-24 bg-white">
        <div className="max-w-7xl mx-auto px-6 md:px-10 py-10 grid md:grid-cols-3 gap-8">
          <div>
            <div className="display font-extrabold text-2xl">OpportunityOS</div>
            <p className="text-sm text-zinc-600 mt-2 max-w-xs">
              Track every hiring hackathon, conference, summit, workshop & invite-only event. Auto-curated, AI prep included.
            </p>
          </div>
          <div className="text-sm">
            <div className="label-over mb-3">Navigate</div>
            <ul className="space-y-1.5">
              {navItems.map((n) => (
                <li key={n.to}>
                  <Link to={n.to} className="hover:underline underline-offset-4">
                    {n.label}
                  </Link>
                </li>
              ))}
              <li>
                <Link to={user ? "/dashboard" : "/login"} className="hover:underline underline-offset-4">
                  {user ? "Dashboard" : "Sign in"}
                </Link>
              </li>
            </ul>
          </div>
          <div className="text-sm">
            <div className="label-over mb-3">Built with</div>
            <ul className="space-y-1.5 text-zinc-600">
              <li>Gemini 3 Flash · auto-curation</li>
              <li>FastAPI · MongoDB · Resend</li>
              <li>React · Tailwind · shadcn/ui</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-black/5 text-xs text-zinc-500 text-center py-4">
          © {new Date().getFullYear()} OpportunityOS · For students & professionals
        </div>
      </footer>
    </>
  );
}
