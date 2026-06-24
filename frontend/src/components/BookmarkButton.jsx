import { useState } from "react";
import { Bookmark, BookmarkCheck, Loader2 } from "lucide-react";
import { useAuth, me } from "@/lib/auth";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

export default function BookmarkButton({ hackathonId, className = "", testid }) {
  const { user, refresh } = useAuth();
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const isOn = !!user?.bookmarks?.includes(hackathonId);

  const toggle = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) {
      toast("Sign in to save events", {
        action: { label: "Sign in", onClick: () => nav("/login") },
      });
      return;
    }
    setBusy(true);
    try {
      await me.toggleBookmark(hackathonId);
      await refresh();
    } catch {
      toast.error("Couldn't save");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      onClick={toggle}
      aria-label={isOn ? "Remove bookmark" : "Add bookmark"}
      title={isOn ? "Saved" : "Save for later"}
      className={`p-1.5 hover:bg-zinc-100 transition-colors ${className}`}
      data-testid={testid || `bookmark-${hackathonId}`}
    >
      {busy ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : isOn ? (
        <BookmarkCheck className="w-4 h-4 text-[var(--brand)] fill-[var(--brand)]" />
      ) : (
        <Bookmark className="w-4 h-4 text-zinc-500" />
      )}
    </button>
  );
}
