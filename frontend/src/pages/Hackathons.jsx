import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Filter, X } from "lucide-react";
import {
  listHackathons,
  getCompanies,
  getEventTypes,
} from "@/lib/api";
import HackathonCard from "@/components/HackathonCard";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";

const REGIONS = ["All", "India", "International"];
const MODES = ["All", "Online", "Offline", "Hybrid"];
const STATUSES = ["All", "Open", "Upcoming", "Closed"];
const AUDIENCES = ["All", "Students", "Professionals"];

export default function Hackathons() {
  const [search, setSearch] = useState("");
  const [region, setRegion] = useState("All");
  const [mode, setMode] = useState("All");
  const [status, setStatus] = useState("All");
  const [company, setCompany] = useState("All");
  const [eventType, setEventType] = useState("All");
  const [audience, setAudience] = useState("All");

  const { data: companies = [] } = useQuery({
    queryKey: ["companies"],
    queryFn: getCompanies,
  });
  const { data: types = [] } = useQuery({
    queryKey: ["event-types"],
    queryFn: getEventTypes,
  });
  const { data: items = [], isLoading } = useQuery({
    queryKey: [
      "hackathons",
      { search, region, mode, status, company, eventType, audience },
    ],
    queryFn: () =>
      listHackathons({
        search: search || undefined,
        region,
        mode,
        status,
        company,
        event_type: eventType,
        audience,
      }),
  });

  const grouped = useMemo(() => {
    const open = items.filter((i) => i.status === "Open");
    const upcoming = items.filter((i) => i.status === "Upcoming");
    const closed = items.filter((i) => i.status === "Closed");
    return { open, upcoming, closed };
  }, [items]);

  const clearFilters = () => {
    setSearch("");
    setRegion("All");
    setMode("All");
    setStatus("All");
    setCompany("All");
    setEventType("All");
    setAudience("All");
  };

  const activeFilters =
    (region !== "All" ? 1 : 0) +
    (mode !== "All" ? 1 : 0) +
    (status !== "All" ? 1 : 0) +
    (company !== "All" ? 1 : 0) +
    (eventType !== "All" ? 1 : 0) +
    (audience !== "All" ? 1 : 0) +
    (search ? 1 : 0);

  return (
    <div className="space-y-10" data-testid="hackathons-page">
      <header>
        <div className="label-over">/// catalog</div>
        <h1 className="display text-4xl sm:text-5xl font-extrabold tracking-tighter mt-2">
          Every event worth attending.
        </h1>
        <p className="text-zinc-600 mt-3 max-w-2xl">
          Hackathons, conferences, summits, workshops, meetups & invite-only
          programs. Filter by event type, audience, region & mode — then open
          any card for the AI-generated prep guide.
        </p>
      </header>

      {/* Filters */}
      <div className="card-flat p-4 sm:p-5 space-y-4" data-testid="filters">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title, company, tag…"
            className="pl-9 h-11 rounded-none border-zinc-300 font-mono text-sm"
            data-testid="search-input"
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <FilterSelect
            label="Type"
            value={eventType}
            onChange={setEventType}
            options={["All", ...types]}
            testid="filter-type"
          />
          <FilterSelect
            label="Audience"
            value={audience}
            onChange={setAudience}
            options={AUDIENCES}
            testid="filter-audience"
          />
          <FilterSelect
            label="Region"
            value={region}
            onChange={setRegion}
            options={REGIONS}
            testid="filter-region"
          />
          <FilterSelect
            label="Mode"
            value={mode}
            onChange={setMode}
            options={MODES}
            testid="filter-mode"
          />
          <FilterSelect
            label="Status"
            value={status}
            onChange={setStatus}
            options={STATUSES}
            testid="filter-status"
          />
          <FilterSelect
            label="Company"
            value={company}
            onChange={setCompany}
            options={["All", ...companies]}
            testid="filter-company"
          />
        </div>
        {activeFilters > 0 && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-500">
              <Filter className="inline w-3.5 h-3.5 mr-1" />
              {activeFilters} filter{activeFilters > 1 ? "s" : ""} active ·{" "}
              {items.length} results
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              className="rounded-none h-8 text-xs"
              data-testid="clear-filters"
            >
              <X className="w-3 h-3 mr-1" /> Clear
            </Button>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-zinc-500">Loading…</div>
      ) : items.length === 0 ? (
        <div className="text-center py-20" data-testid="empty-state">
          <div className="display text-3xl font-bold mb-2">No matches</div>
          <p className="text-zinc-600">
            Try clearing filters or trigger an AI refresh from the homepage.
          </p>
        </div>
      ) : (
        <div className="space-y-12">
          <Group title="Open now" items={grouped.open} />
          <Group title="Upcoming" items={grouped.upcoming} />
          <Group title="Closed" items={grouped.closed} dim />
        </div>
      )}
    </div>
  );
}

function FilterSelect({ label, value, onChange, options, testid }) {
  return (
    <div>
      <div className="label-over mb-1.5">{label}</div>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger
          className="rounded-none border-zinc-300 h-11 font-mono text-sm"
          data-testid={testid}
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o} value={o} className="font-mono text-sm">
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function Group({ title, items, dim }) {
  if (!items.length) return null;
  return (
    <section data-testid={`group-${title.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="flex items-baseline gap-3 mb-4">
        <h2 className="display text-2xl font-bold">{title}</h2>
        <span className="font-mono text-xs text-zinc-500">
          ({items.length})
        </span>
      </div>
      <div
        className={`grid sm:grid-cols-2 lg:grid-cols-3 gap-4 ${
          dim ? "opacity-60" : ""
        }`}
      >
        {items.map((h) => (
          <HackathonCard key={h.id} h={h} />
        ))}
      </div>
    </section>
  );
}
