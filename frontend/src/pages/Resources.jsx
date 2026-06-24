import { useQuery } from "@tanstack/react-query";
import {
  ExternalLink,
  BookOpen,
  Video,
  GraduationCap,
  FileText,
  Target,
} from "lucide-react";
import { getResources } from "@/lib/api";

const ICON = {
  article: BookOpen,
  video: Video,
  course: GraduationCap,
  docs: FileText,
  practice: Target,
};

export default function Resources() {
  const { data, isLoading } = useQuery({
    queryKey: ["resources"],
    queryFn: getResources,
  });

  return (
    <div className="space-y-12" data-testid="resources-page">
      <header>
        <div className="label-over">/// resources hub</div>
        <h1 className="display text-4xl sm:text-5xl font-extrabold tracking-tighter mt-2">
          Everything you need to crack hiring hackathons.
        </h1>
        <p className="text-zinc-600 mt-3 max-w-2xl">
          Hand-picked links across DSA, system design, behavioral interviews and
          hackathon discovery platforms. Use these alongside AI prep to maximise
          your shot.
        </p>
      </header>

      {isLoading ? (
        <div className="text-zinc-500">Loading…</div>
      ) : (
        <div className="space-y-12">
          {Object.entries(data || {}).map(([category, items]) => (
            <section key={category} data-testid={`res-${category}`}>
              <div className="flex items-baseline gap-3 mb-4">
                <h2 className="display text-2xl font-bold">{category}</h2>
                <span className="font-mono text-xs text-zinc-500">
                  ({items.length})
                </span>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {items.map((r, i) => {
                  const Icon = ICON[r.type] || BookOpen;
                  let host = "";
                  try {
                    host = new URL(r.url).hostname.replace("www.", "");
                  } catch {
                    host = "";
                  }
                  return (
                    <a
                      key={i}
                      href={r.url}
                      target="_blank"
                      rel="noreferrer"
                      className="card-flat p-4 flex items-start gap-3 group"
                      data-testid={`res-link-${category}-${i}`}
                    >
                      <Icon className="w-4 h-4 mt-1 text-zinc-500 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium group-hover:text-[var(--brand)] transition-colors">
                          {r.title}
                        </div>
                        <div className="text-[11px] text-zinc-500 uppercase tracking-wider mt-1">
                          {r.type} · {host}
                        </div>
                      </div>
                      <ExternalLink className="w-3.5 h-3.5 text-zinc-400 mt-1" />
                    </a>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
