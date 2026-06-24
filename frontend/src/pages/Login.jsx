import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth, startGoogleAuth } from "@/lib/auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(email, password);
      toast.success("Welcome back!");
      nav(loc.state?.from || "/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-12" data-testid="login-page">
      <div className="label-over">/// sign in</div>
      <h1 className="display text-4xl font-extrabold tracking-tighter mt-2 mb-6">
        Welcome back.
      </h1>

      <button
        onClick={() => startGoogleAuth("/auth/callback")}
        className="w-full border border-zinc-300 h-12 inline-flex items-center justify-center gap-2 hover:bg-zinc-50 transition-colors"
        data-testid="google-login-btn"
      >
        <GoogleIcon /> Continue with Google
      </button>

      <div className="flex items-center gap-3 my-6">
        <div className="flex-1 h-px bg-zinc-200" />
        <span className="text-[11px] uppercase tracking-wider text-zinc-500">
          or with email
        </span>
        <div className="flex-1 h-px bg-zinc-200" />
      </div>

      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label-over block mb-1.5">Email</label>
          <Input
            type="email"
            value={email}
            required
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-none border-zinc-300 h-11 font-mono text-sm"
            data-testid="login-email"
          />
        </div>
        <div>
          <label className="label-over block mb-1.5">Password</label>
          <Input
            type="password"
            value={password}
            required
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-none border-zinc-300 h-11 font-mono text-sm"
            data-testid="login-password"
          />
        </div>
        <Button
          type="submit"
          disabled={busy}
          className="w-full rounded-none bg-zinc-950 hover:bg-[var(--brand)] h-12 text-sm font-semibold"
          data-testid="login-submit"
        >
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="text-sm text-zinc-600 mt-6 text-center">
        New here?{" "}
        <Link
          to="/register"
          className="text-zinc-950 font-semibold underline underline-offset-4"
          data-testid="goto-register"
        >
          Create an account
        </Link>
      </p>
    </div>
  );
}

export function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }
    setBusy(true);
    try {
      await register(email, password, name);
      toast.success("Account created — welcome!");
      nav("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Registration failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-12" data-testid="register-page">
      <div className="label-over">/// create account</div>
      <h1 className="display text-4xl font-extrabold tracking-tighter mt-2 mb-6">
        Join OpportunityOS.
      </h1>
      <p className="text-zinc-600 mb-6">
        Bookmark events, get 24h reminders, upload your resume for a
        personalised feed.
      </p>

      <button
        onClick={() => startGoogleAuth("/auth/callback")}
        className="w-full border border-zinc-300 h-12 inline-flex items-center justify-center gap-2 hover:bg-zinc-50"
        data-testid="google-signup-btn"
      >
        <GoogleIcon /> Continue with Google
      </button>

      <div className="flex items-center gap-3 my-6">
        <div className="flex-1 h-px bg-zinc-200" />
        <span className="text-[11px] uppercase tracking-wider text-zinc-500">
          or with email
        </span>
        <div className="flex-1 h-px bg-zinc-200" />
      </div>

      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label-over block mb-1.5">Name</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-none border-zinc-300 h-11 font-mono text-sm"
            data-testid="register-name"
          />
        </div>
        <div>
          <label className="label-over block mb-1.5">Email</label>
          <Input
            type="email"
            value={email}
            required
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-none border-zinc-300 h-11 font-mono text-sm"
            data-testid="register-email"
          />
        </div>
        <div>
          <label className="label-over block mb-1.5">Password</label>
          <Input
            type="password"
            value={password}
            required
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-none border-zinc-300 h-11 font-mono text-sm"
            data-testid="register-password"
          />
        </div>
        <Button
          type="submit"
          disabled={busy}
          className="w-full rounded-none bg-zinc-950 hover:bg-[var(--brand)] h-12 text-sm font-semibold"
          data-testid="register-submit"
        >
          {busy ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <p className="text-sm text-zinc-600 mt-6 text-center">
        Have an account?{" "}
        <Link
          to="/login"
          className="text-zinc-950 font-semibold underline underline-offset-4"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.25h2.9c1.7-1.56 2.7-3.87 2.7-6.61z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.25c-.8.54-1.83.86-3.06.86-2.35 0-4.34-1.59-5.05-3.73H.96v2.33A9 9 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.95 10.7A5.4 5.4 0 0 1 3.66 9c0-.59.1-1.16.29-1.7V4.96H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.04l3-2.34z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.34l2.58-2.58A9 9 0 0 0 9 0 9 9 0 0 0 .96 4.96l3 2.33C4.66 5.17 6.65 3.58 9 3.58z"
      />
    </svg>
  );
}
