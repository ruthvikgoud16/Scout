import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Bookmark,
  Upload,
  Sparkles,
  Plus,
  X,
  CheckCircle2,
  Mail,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useAuth, me } from "@/lib/auth";
import HackathonCard from "@/components/HackathonCard";
import { toast } from "sonner";

export default function Dashboard() {
  const { user, refresh } = useAuth();
  const qc = useQueryClient();
  const fileRef = useRef(null);
  const [newSkill, setNewSkill] = useState("");
  const [skills, setSkills] = useState(user?.skills || []);
  const [notify, setNotify] = useState(user?.email_notify ?? true);

  useEffect(() => {
    setSkills(user?.skills || []);
    setNotify(user?.email_notify ?? true);
  }, [user]);

  const { data: bookmarks = [] } = useQuery({
    queryKey: ["bookmarks"],
    queryFn: me.listBookmarks,
    enabled: !!user,
  });
  const { data: feed = [] } = useQuery({
    queryKey: ["feed", skills.join("|")],
    queryFn: me.feed,
    enabled: !!user,
  });

  const saveSkills = useMutation({
    mutationFn: (s) => me.setSkills(s),
    onSuccess: async () => {
      toast.success("Skills updated");
      await refresh();
      qc.invalidateQueries({ queryKey: ["feed"] });
    },
  });

  const uploadResume = useMutation({
    mutationFn: (f) => me.uploadResume(f),
    onSuccess: async (data) => {
      toast.success(
        `Extracted ${data.extracted_skills?.length || 0} skills from resume`
      );
      await refresh();
      qc.invalidateQueries({ queryKey: ["feed"] });
    },
    onError: () => toast.error("Resume upload failed"),
  });

  const toggleNotify = useMutation({
    mutationFn: (v) => me.setNotify(v),
    onSuccess: (data) => {
      setNotify(data.email_notify);
      toast.success(
        data.email_notify ? "Reminders enabled" : "Reminders disabled"
      );
    },
  });

  if (!user) return null;

  const addSkill = () => {
    const s = newSkill.trim();
    if (!s) return;
    const next = Array.from(new Set([...skills, s])).slice(0, 50);
    setSkills(next);
    setNewSkill("");
    saveSkills.mutate(next);
  };
  const removeSkill = (s) => {
    const next = skills.filter((x) => x !== s);
    setSkills(next);
    saveSkills.mutate(next);
  };

  return (
    <div className="space-y-12" data-testid="dashboard-page">
      <header className="grid lg:grid-cols-12 gap-6 items-end">
        <div className="lg:col-span-8">
          <div className="label-over">/// my opportunityos</div>
          <h1 className="display text-4xl sm:text-5xl font-extrabold tracking-tighter mt-2">
            Hey, {user.name?.split(" ")[0] || "there"}.
          </h1>
          <p className="text-zinc-600 mt-3 max-w-2xl">
            Your bookmarks, your personalised feed, and your 24-hour deadline
            reminders — all in one place.
          </p>
        </div>
        <div className="lg:col-span-4">
          <div className="card-flat p-4 flex items-center gap-3">
            {user.picture ? (
              <img
                src={user.picture}
                alt={user.name}
                className="w-10 h-10 rounded-full border border-zinc-200"
              />
            ) : (
              <div className="w-10 h-10 grid place-items-center bg-zinc-950 text-white text-xs font-bold rounded-full">
                {user.name?.[0]?.toUpperCase() || "?"}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold truncate">
                {user.name}
              </div>
              <div className="text-[11px] text-zinc-500 truncate">
                {user.email}
              </div>
            </div>
            <span className="pill">{user.auth_provider}</span>
          </div>
        </div>
      </header>

      <section className="grid lg:grid-cols-12 gap-8">
        {/* Skills + Resume */}
        <div className="lg:col-span-5 space-y-8">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card-flat p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="display text-xl font-semibold">Your skills</h2>
              <span className="text-[11px] uppercase tracking-wider text-zinc-500">
                {skills.length}/50
              </span>
            </div>
            <div className="flex gap-2 mb-3">
              <Input
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                placeholder="e.g. React, Kubernetes, Product Strategy"
                className="rounded-none border-zinc-300 h-10 font-mono text-sm"
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSkill())}
                data-testid="skill-input"
              />
              <Button
                onClick={addSkill}
                className="rounded-none bg-zinc-950 hover:bg-[var(--brand)] h-10"
                data-testid="skill-add-btn"
              >
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {skills.length === 0 ? (
                <span className="text-sm text-zinc-500">
                  Add a few skills — or upload a resume and we'll do it for you.
                </span>
              ) : (
                skills.map((s) => (
                  <span
                    key={s}
                    className="pill cursor-pointer hover:border-rose-400 hover:text-rose-600 group"
                    onClick={() => removeSkill(s)}
                    data-testid={`skill-${s}`}
                  >
                    {s}
                    <X className="w-3 h-3 opacity-50 group-hover:opacity-100" />
                  </span>
                ))
              )}
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card-flat p-6">
            <h2 className="display text-xl font-semibold mb-2">Resume</h2>
            <p className="text-sm text-zinc-600 mb-4">
              Upload your PDF/DOCX — Gemini will extract your skills automatically
              and personalise your feed.
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) uploadResume.mutate(f);
              }}
              className="hidden"
              data-testid="resume-file-input"
            />
            <Button
              onClick={() => fileRef.current?.click()}
              disabled={uploadResume.isPending}
              className="rounded-none bg-zinc-950 hover:bg-[var(--brand)] h-11 px-5"
              data-testid="upload-resume-btn"
            >
              {uploadResume.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Extracting…
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />{" "}
                  {user.resume_filename ? "Replace resume" : "Upload resume"}
                </>
              )}
            </Button>
            {user.resume_filename && (
              <div className="mt-3 text-xs flex items-center gap-1.5 text-emerald-700">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {user.resume_filename}
              </div>
            )}
          </motion.div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card-flat p-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Mail className="w-4 h-4 text-zinc-500" />
                  <h2 className="display text-lg font-semibold">
                    24-hour deadline reminders
                  </h2>
                </div>
                <p className="text-sm text-zinc-600 max-w-sm">
                  We'll email you {user.email} 24h before any bookmarked
                  event's registration closes.
                </p>
              </div>
              <Switch
                checked={notify}
                onCheckedChange={(v) => toggleNotify.mutate(v)}
                data-testid="notify-switch"
              />
            </div>
          </motion.div>
        </div>

        {/* Bookmarks + Feed */}
        <div className="lg:col-span-7 space-y-10">
          <div>
            <div className="flex items-baseline justify-between mb-4">
              <h2 className="display text-2xl font-bold">
                <Bookmark className="inline w-5 h-5 mb-1 mr-1" />
                Bookmarks
              </h2>
              <span className="font-mono text-xs text-zinc-500">
                ({bookmarks.length})
              </span>
            </div>
            {bookmarks.length === 0 ? (
              <div className="card-flat p-8 text-center" data-testid="empty-bookmarks">
                <p className="text-zinc-600">
                  No bookmarks yet —{" "}
                  <Link to="/hackathons" className="underline font-semibold">
                    browse opportunities
                  </Link>{" "}
                  and tap the bookmark icon.
                </p>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 gap-4">
                {bookmarks.map((h) => (
                  <HackathonCard key={h.id} h={h} />
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="flex items-baseline justify-between mb-4">
              <h2 className="display text-2xl font-bold">
                <Sparkles className="inline w-5 h-5 mb-1 mr-1 text-[var(--brand)]" />
                Personalised for you
              </h2>
              <span className="font-mono text-xs text-zinc-500">
                ({feed.length})
              </span>
            </div>
            {feed.length === 0 ? (
              <div className="card-flat p-8 text-center">
                <p className="text-zinc-600">No matches yet — add skills above.</p>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 gap-4">
                {feed.slice(0, 8).map((h) => (
                  <HackathonCard key={h.id} h={h} />
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
