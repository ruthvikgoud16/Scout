export function fmtDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

export function countdown(iso) {
  if (!iso) return null;
  const target = new Date(iso).getTime();
  const now = Date.now();
  const diff = target - now;
  if (diff <= 0) return { expired: true, label: "Closed" };
  const days = Math.floor(diff / 86_400_000);
  const hours = Math.floor((diff % 86_400_000) / 3_600_000);
  if (days >= 1) return { expired: false, label: `${days}d ${hours}h left` };
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  return { expired: false, label: `${hours}h ${mins}m left` };
}

export function statusColor(status) {
  switch (status) {
    case "Open":
      return "bg-emerald-500 text-zinc-950";
    case "Upcoming":
      return "bg-amber-300 text-zinc-950";
    case "Closed":
      return "bg-zinc-300 text-zinc-700";
    default:
      return "bg-zinc-200 text-zinc-700";
  }
}
