import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Calendar,
  MapPin,
  ExternalLink,
  CheckCircle2,
  Sparkles,
  ArrowLeft,
  Clock,
  BookOpen,
  Video,
  GraduationCap,
  FileText,
  Target,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import { getHackathon, generatePrep } from "@/lib/api";
import { fmtDate, countdown, statusColor } from "@/lib/format";
import CompanyLogo from "@/components/CompanyLogo";
import { toast } from "sonner";

const RES_ICON = {
  article: BookOpen,
  video: Video,
  course: GraduationCap,
  docs: FileText,
  practice: Target,
};

export default function HackathonDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
  const { data: h, isLoading } = useQuery({
    queryKey: ["hackathon", id],
    queryFn: () => getHackathon(id),
  });
  const [checked, setChecked] = useState({});

  const prepMutation = useMutation({
    mutationFn: () => generatePrep(id),
    onSuccess: () => {
      toast.success("AI prep generated", {
        description: "Rounds, requirements, checklist and resources are ready.",
      });
      qc.invalidateQueries({ queryKey: ["hackathon", id] });
    },
    onError: () =>
      toast.error("Could not generate prep — please retry in a moment."),
  });

  if (isLoading) return <DetailSkeleton />;
  if (!h)
    return (
      <div className="text-center py-20">
        <p>Hackathon not found.</p>
        <Link to="/hackathons" className="underline mt-3 inline-block">
          Back to listings
        </Link>
      </div>
    );

  const cd = countdown(h.registration_deadline);
  const prep = h.prep;
  const checklistProgress = prep?.checklist?.length
    ? Math.round(
        (Object.values(checked).filter(Boolean).length /
          prep.checklist.length) *
          100
      )
    : 0;

  return (
    <div className="space-y-12" data-testid="detail-page">
      <Link
        to="/hackathons"
        className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-[0.18em] hover:text-[var(--brand)]"
        data-testid="back-link"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to listings
      </Link>

      {/* HERO */}
      <header className="grid lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-zinc-100 border border-zinc-200 grid place-items-center overflow-hidden">
              <CompanyLogo name={h.company} url={h.company_logo} />
            </div>
            <div>
              <div className="label-over">{h.company}</div>
              <div className="text-xs text-zinc-500">
                {h.event_type} · {h.region} · {h.mode}
                {h.audience?.length ? ` · ${h.audience.join(" & ")}` : ""}
              </div>
            </div>
            <span
              className={`ml-auto text-[10px] font-bold uppercase tracking-wider px-2 py-1 ${statusColor(
                h.status
              )}`}
            >
              {h.status}
            </span>
          </div>
          <h1 className="display text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tighter leading-[0.95]">
            {h.title}
          </h1>
          <p className="text-zinc-600 mt-4 leading-relaxed max-w-2xl">
            {h.description}
          </p>

          <div className="flex flex-wrap gap-2 mt-5">
            {(h.tags || []).map((t) => (
              <span key={t} className="pill">
                {t}
              </span>
            ))}
          </div>

          <div className="flex flex-wrap gap-3 mt-7">
            {h.registration_link && (
              <Button
                asChild
                className="rounded-none bg-zinc-950 text-white hover:bg-[var(--brand)] h-12 px-5"
                data-testid="register-cta"
              >
                <a
                  href={h.registration_link}
                  target="_blank"
                  rel="noreferrer"
                >
                  Register now <ExternalLink className="ml-2 w-4 h-4" />
                </a>
              </Button>
            )}
            <Button
              variant="outline"
              className="rounded-none border-zinc-300 h-12 px-5"
              onClick={() => prepMutation.mutate()}
              disabled={prepMutation.isPending}
              data-testid="generate-prep-btn"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              {prepMutation.isPending
                ? "Generating with Gemini…"
                : prep
                  ? "Regenerate AI prep"
                  : "Generate AI prep"}
            </Button>
          </div>
        </div>

        {/* Side info */}
        <aside className="lg:col-span-4 space-y-3">
          <InfoTile
            label="Registration deadline"
            value={fmtDate(h.registration_deadline)}
            sub={cd?.label}
            icon={<Clock className="w-4 h-4" />}
            highlight={!cd?.expired}
          />
          <InfoTile
            label="Event dates"
            value={`${fmtDate(h.start_date)} → ${fmtDate(h.end_date)}`}
            icon={<Calendar className="w-4 h-4" />}
          />
          <InfoTile
            label="Location"
            value={h.location || "—"}
            icon={<MapPin className="w-4 h-4" />}
          />
          {h.eligibility && (
            <div className="card-flat p-4">
              <div className="label-over mb-1">Eligibility</div>
              <div className="text-sm text-zinc-700">{h.eligibility}</div>
            </div>
          )}
          {h.prizes && (
            <div className="card-flat p-4">
              <div className="label-over mb-1">Prizes</div>
              <div className="text-sm text-zinc-700">{h.prizes}</div>
            </div>
          )}
        </aside>
      </header>

      {/* PREP */}
      <section className="border-t border-black/10 pt-12" data-testid="prep-section">
        <div className="flex items-end justify-between mb-6">
          <div>
            <div className="label-over">/// prep playbook</div>
            <h2 className="display text-3xl sm:text-4xl font-bold tracking-tight mt-2">
              How to prepare
            </h2>
          </div>
          {prep?.generated_at && (
            <div className="text-[11px] text-zinc-500 uppercase tracking-wider">
              AI generated · {fmtDate(prep.generated_at)}
            </div>
          )}
        </div>

        {!prep && (
          <div
            className="card-flat p-10 text-center"
            data-testid="prep-empty"
          >
            <Sparkles className="w-8 h-8 mx-auto text-zinc-400" />
            <h3 className="display text-2xl font-bold mt-3">
              No prep generated yet
            </h3>
            <p className="text-zinc-600 mt-2 max-w-md mx-auto">
              Click &ldquo;Generate AI prep&rdquo; above and Gemini will build a complete
              playbook — typical rounds, requirements, checklist and curated
              resources.
            </p>
          </div>
        )}

        {prep && (
          <div className="grid lg:grid-cols-12 gap-8">
            {/* Rounds */}
            <div className="lg:col-span-7 space-y-6">
              <div>
                <h3 className="display text-xl font-semibold mb-4">
                  Typical rounds
                </h3>
                <div className="space-y-3">
                  {prep.rounds?.map((r, i) => (
                    <div
                      key={i}
                      className="card-flat p-5"
                      data-testid={`round-${i}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="font-mono text-xs font-semibold bg-zinc-950 text-white w-8 h-8 grid place-items-center shrink-0">
                          0{i + 1}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-baseline justify-between gap-2">
                            <div className="display text-lg font-semibold">
                              {r.name}
                            </div>
                            {r.duration && (
                              <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono">
                                {r.duration}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-zinc-600 mt-1 leading-relaxed">
                            {r.description}
                          </p>
                          {r.tips && (
                            <div className="mt-3 text-xs font-medium bg-blue-50 border-l-2 border-[var(--brand)] px-3 py-2 text-zinc-700">
                              <span className="font-bold text-[var(--brand)]">
                                TIP:{" "}
                              </span>
                              {r.tips}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Requirements */}
              <div>
                <h3 className="display text-xl font-semibold mb-4">
                  Requirements
                </h3>
                <ul className="card-flat p-5 space-y-2">
                  {prep.requirements?.map((req, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-zinc-700"
                    >
                      <span className="font-mono text-[var(--brand)] mt-0.5">
                        ▸
                      </span>
                      {req}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Checklist + Resources */}
            <div className="lg:col-span-5 space-y-6">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="display text-xl font-semibold">
                    Prep checklist
                  </h3>
                  <span className="font-mono text-xs text-zinc-500">
                    {checklistProgress}%
                  </span>
                </div>
                <div className="h-1 bg-zinc-100 mb-3">
                  <div
                    className="h-full bg-[var(--brand)] transition-all"
                    style={{ width: `${checklistProgress}%` }}
                  />
                </div>
                <ul className="card-flat p-5 space-y-3">
                  {prep.checklist?.map((c, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <Checkbox
                        checked={!!checked[i]}
                        onCheckedChange={(v) =>
                          setChecked((p) => ({ ...p, [i]: !!v }))
                        }
                        className="mt-0.5"
                        data-testid={`check-${i}`}
                      />
                      <span
                        className={`text-sm leading-relaxed ${
                          checked[i]
                            ? "line-through text-zinc-400"
                            : "text-zinc-700"
                        }`}
                      >
                        {c}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h3 className="display text-xl font-semibold mb-3">
                  Curated resources
                </h3>
                <ul className="space-y-2">
                  {prep.resources?.map((r, i) => {
                    const Icon = RES_ICON[r.type] || BookOpen;
                    return (
                      <li key={i}>
                        <a
                          href={r.url}
                          target="_blank"
                          rel="noreferrer"
                          className="card-flat p-4 flex items-center gap-3 group"
                          data-testid={`resource-${i}`}
                        >
                          <Icon className="w-4 h-4 text-zinc-500 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate group-hover:text-[var(--brand)]">
                              {r.title}
                            </div>
                            <div className="text-[11px] text-zinc-500 uppercase tracking-wider truncate">
                              {r.type} · {new URL(r.url).hostname}
                            </div>
                          </div>
                          <ExternalLink className="w-3.5 h-3.5 text-zinc-400" />
                        </a>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function InfoTile({ label, value, sub, icon, highlight }) {
  return (
    <div className="card-flat p-4">
      <div className="flex items-center justify-between">
        <span className="label-over">{label}</span>
        <span className="text-zinc-400">{icon}</span>
      </div>
      <div className="display text-lg font-semibold mt-1.5">{value}</div>
      {sub && (
        <div
          className={`text-xs mt-1 ${
            highlight ? "text-[var(--brand)] font-semibold" : "text-zinc-500"
          }`}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-8">
      <Skeleton className="h-6 w-32 rounded-none" />
      <Skeleton className="h-12 w-2/3 rounded-none" />
      <Skeleton className="h-32 w-full rounded-none" />
      <div className="grid lg:grid-cols-12 gap-6">
        <Skeleton className="lg:col-span-8 h-72 rounded-none" />
        <Skeleton className="lg:col-span-4 h-72 rounded-none" />
      </div>
    </div>
  );
}
