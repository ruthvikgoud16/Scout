import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";

export default function AuthCallback() {
  const { googleExchange } = useAuth();
  const nav = useNavigate();
  const done = useRef(false);

  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const hash = window.location.hash || "";
    const m = hash.match(/session_id=([^&]+)/);
    if (!m) {
      nav("/login");
      return;
    }
    (async () => {
      try {
        await googleExchange(m[1]);
        // clear hash and go to dashboard
        window.history.replaceState({}, document.title, window.location.pathname);
        toast.success("Signed in with Google");
        nav("/dashboard", { replace: true });
      } catch {
        toast.error("Google sign-in failed");
        nav("/login", { replace: true });
      }
    })();
  }, [googleExchange, nav]);

  return (
    <div className="text-center py-20" data-testid="auth-callback">
      <div className="display text-2xl font-bold mb-2">Signing you in…</div>
      <p className="text-zinc-500">One moment.</p>
    </div>
  );
}
