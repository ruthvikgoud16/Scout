import { useState } from "react";

const PALETTE = [
  "bg-blue-600",
  "bg-rose-500",
  "bg-amber-500",
  "bg-emerald-600",
  "bg-violet-600",
  "bg-cyan-600",
  "bg-fuchsia-600",
  "bg-orange-500",
  "bg-teal-600",
];

function hashColor(str = "") {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) | 0;
  }
  return PALETTE[Math.abs(h) % PALETTE.length];
}

export default function CompanyLogo({ name = "", url, className = "" }) {
  const [failed, setFailed] = useState(false);
  const initials = name
    .split(/\s+/)
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  if (url && !failed) {
    return (
      <img
        src={url}
        alt={name}
        onError={() => setFailed(true)}
        className={`w-full h-full object-contain ${className}`}
      />
    );
  }
  return (
    <div
      className={`w-full h-full grid place-items-center text-white text-xs font-bold ${hashColor(
        name
      )} ${className}`}
      aria-label={name}
    >
      {initials || "??"}
    </div>
  );
}
