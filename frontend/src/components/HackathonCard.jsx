import { Link } from "react-router-dom";
import { Calendar, MapPin, ArrowUpRight } from "lucide-react";
import { fmtDate, countdown, statusColor } from "@/lib/format";

export default function HackathonCard({ h }) {
  const cd = countdown(h.registration_deadline);
  const live = h.status === "Open";

  return (
    <Link
      to={`/hackathons/${h.id}`}
      data-testid={`hackathon-card-${h.id}`}
      className={`group relative card-flat p-5 flex flex-col gap-4 ${
        live ? "ring-pulse" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 bg-zinc-100 grid place-items-center border border-zinc-200 overflow-hidden shrink-0">
            {h.company_logo ? (
              <img
                src={h.company_logo}
                alt={h.company}
                className="w-full h-full object-contain"
                onError={(e) => {
                  e.target.style.display = "none";
                }}
              />
            ) : (
              <span className="text-xs font-semibold">
                {h.company?.slice(0, 2)}
              </span>
            )}
          </div>
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
              {h.company}
            </div>
            <div className="font-semibold text-zinc-950 truncate group-hover:text-[var(--brand)] transition-colors">
              {h.title}
            </div>
          </div>
        </div>
        <span
          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-sm ${statusColor(
            h.status
          )}`}
          data-testid={`status-${h.id}`}
        >
          {h.status}
        </span>
      </div>

      <p className="text-sm text-zinc-600 line-clamp-2 leading-relaxed">
        {h.description}
      </p>

      <div className="flex flex-wrap gap-1.5">
        <span className="pill">{h.mode}</span>
        <span className="pill">{h.region}</span>
        {(h.tags || []).slice(0, 2).map((t) => (
          <span key={t} className="pill">
            {t}
          </span>
        ))}
      </div>

      <div className="border-t border-zinc-100 pt-3 flex items-center justify-between text-xs text-zinc-600">
        <div className="flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" />
          <span>{fmtDate(h.start_date)}</span>
        </div>
        <div className="flex items-center gap-1.5 truncate max-w-[50%]">
          <MapPin className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{h.location || "—"}</span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-xs">
          {cd && (
            <span
              className={`font-medium ${
                cd.expired ? "text-zinc-400" : "text-[var(--brand)]"
              }`}
            >
              {cd.label}
            </span>
          )}
        </div>
        <span className="text-xs font-semibold inline-flex items-center gap-1 text-zinc-950 group-hover:gap-2 transition-all">
          View Prep <ArrowUpRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </Link>
  );
}
