"""Generate ICS calendar file content for an event."""
from datetime import datetime, timezone


def _dt(iso):
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.strftime("%Y%m%dT%H%M%SZ")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _esc(s: str) -> str:
    if not s:
        return ""
    return (
        s.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def build_ics(h: dict) -> str:
    uid = f"{h.get('id')}@opportunityos"
    start = _dt(h.get("start_date") or "")
    end = _dt(h.get("end_date") or h.get("start_date") or "")
    summary = _esc(f"{h.get('title')} · {h.get('company')}")
    desc_parts = [
        h.get("description") or "",
        f"\\n\\nRegistration: {h.get('registration_link') or '—'}",
        f"\\nDeadline: {h.get('registration_deadline') or '—'}",
        f"\\nEligibility: {h.get('eligibility') or '—'}",
        f"\\nPrizes: {h.get('prizes') or '—'}",
    ]
    description = _esc(" ".join(desc_parts))
    location = _esc(h.get("location") or "")
    url = h.get("registration_link") or h.get("source_url") or ""
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//OpportunityOS//HackTrack//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART:{start}",
        f"DTEND:{end}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"LOCATION:{location}",
        f"URL:{url}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Event reminder",
        "TRIGGER:-P1D",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines)
