import { Link } from "react-router-dom";
import { Calendar, MapPin, ArrowUpRight, Users, Briefcase } from "lucide-react";
import { fmtDate, countdown, statusColor } from "@/lib/format";
import CompanyLogo from "@/components/CompanyLogo";
import BookmarkButton from "@/components/BookmarkButton";

export default function HackathonCard({ h }) {
  const cd = countdown(h.registration_deadline);
  const live = h.status === "Open";
  const aud = h.audience || [];

  return (
    <Link
      to={`/hackathons/${h.id}`}
      data-testid={`hackathon-card-${h.id}`}
      className={`group relative card-flat p-5 flex flex-col gap-4 ${
        live ? "ring-pulse" : ""
      }`}
    >
      <div className="absolute top-2 right-2 z-10">
        <BookmarkButton hackathonId={h.id} testid={`bookmark-card-${h.id}`} />
      </div>
      <div className="flex items-start justify-between gap-3 pr-8">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 bg-zinc-100 grid place-items-center border border-zinc-200 overflow-hidden shrink-0">
            <CompanyLogo name={h.company} url={h.company_logo} />
          </div>
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500 truncate">
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
        {h.event_type && (
          <span className="pill border-zinc-900 bg-zinc-950 text-white">
            {h.event_type}
          </span>
        )}
        <span className="pill">{h.mode}</span>
        <span className="pill">{h.region}</span>
        {aud.includes("Students") && (
          <span className="pill" title="Students">
            <Users className="w-3 h-3" /> Students
          </span>
        )}
        {aud.includes("Professionals") && (
          <span className="pill" title="Professionals">
            <Briefcase className="w-3 h-3" /> Pros
          </span>
        )}
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
