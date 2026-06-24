import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  RefreshCw,
  Zap,
  Globe2,
  Trophy,
  GraduationCap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { getStats, listHackathons, refreshFeed } from "@/lib/api";
import HackathonCard from "@/components/HackathonCard";
import { toast } from "sonner";
import { useState } from "react";

export default function Home() {
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const { data: feed, refetch } = useQuery({
    queryKey: ["feed-home"],
    queryFn: () => listHackathons({}),
  });
  const [refreshing, setRefreshing] = useState(false);

  const featured = (feed || []).slice(0, 6);
  const marqueeItems = (feed || []).filter(
    (h) => h.status === "Open" || h.status === "Upcoming"
  );

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshFeed();
      toast.success("AI refresh started — new hackathons appearing soon", {
        description: "Gemini is scanning the web. Refresh in ~30s.",
      });
      setTimeout(() => refetch(), 25000);
    } catch {
      toast.error("Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="space-y-20">
      {/* HERO */}
      <section className="relative" data-testid="hero">
        <div className="absolute inset-0 grid-bg opacity-40 pointer-events-none" />
        <div className="relative grid lg:grid-cols-12 gap-10 items-end">
          <div className="lg:col-span-8">
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="label-over inline-flex items-center gap-2"
            >
              <span className="blink-dot" /> Live · Gemini-curated · Updated{" "}
              {stats?.last_refreshed_at
                ? new Date(stats.last_refreshed_at).toLocaleString()
                : "—"}
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.05 }}
              className="display text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tighter leading-[0.95] mt-4"
            >
              Every{" "}
              <span className="text-[var(--brand)]">hackathon, conference</span>
              <br />& invite-only event — in one place.
            </motion.h1>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-zinc-600 text-base sm:text-lg max-w-2xl mt-6 leading-relaxed"
            >
              Hiring hackathons (Myntra HackerRamp, Meesho Maverix), global tech
              conferences (Google I/O, KubeCon, AWS re:Invent), invite-only
              summits (YC Startup School, Stripe Sessions), local meetups &
              workshops. Indian + international. Online, offline & hybrid. With
              an AI-generated prep playbook for every event — for{" "}
              <strong>students</strong> and <strong>working professionals</strong>.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.35 }}
              className="flex flex-wrap items-center gap-3 mt-8"
            >
              <Button
                asChild
                size="lg"
                className="rounded-none bg-zinc-950 text-white hover:bg-[var(--brand)] hover:text-white h-12 px-6 text-sm font-semibold"
                data-testid="cta-explore"
              >
                <Link to="/hackathons">
                  Explore hackathons <ArrowRight className="ml-2 w-4 h-4" />
                </Link>
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={handleRefresh}
                disabled={refreshing}
                className="rounded-none border-zinc-300 h-12 px-5 text-sm hover:bg-zinc-100"
                data-testid="cta-refresh"
              >
                <RefreshCw
                  className={`w-4 h-4 mr-2 ${refreshing ? "animate-spin" : ""}`}
                />
                AI refresh feed
              </Button>
            </motion.div>
          </div>

          {/* Bento stats */}
          <div className="lg:col-span-4 grid grid-cols-2 gap-3" data-testid="stats-grid">
            <StatTile
              label="Total tracked"
              value={stats?.total ?? "—"}
              icon={<Trophy className="w-4 h-4" />}
              testid="stat-total"
            />
            <StatTile
              label="Open now"
              value={stats?.open ?? "—"}
              accent="bg-emerald-400"
              icon={<Zap className="w-4 h-4" />}
              testid="stat-open"
            />
            <StatTile
              label="Upcoming"
              value={stats?.upcoming ?? "—"}
              accent="bg-amber-300"
              icon={<GraduationCap className="w-4 h-4" />}
              testid="stat-upcoming"
            />
            <StatTile
              label="Companies"
              value={stats?.companies_count ?? "—"}
              icon={<Globe2 className="w-4 h-4" />}
              testid="stat-companies"
            />
          </div>
        </div>
      </section>

      {/* MARQUEE */}
      {marqueeItems.length > 0 && (
        <section
          className="relative border-y border-black/10 bg-zinc-950 text-white py-4 -mx-6 md:-mx-10 overflow-hidden"
          data-testid="marquee"
        >
          <div className="marquee-track px-6">
            {[...marqueeItems, ...marqueeItems].map((h, i) => (
              <Link
                key={`${h.id}-${i}`}
                to={`/hackathons/${h.id}`}
                className="flex items-center gap-3 text-sm whitespace-nowrap hover:text-[var(--live)] transition-colors"
              >
                <span className="text-[var(--live)] font-mono text-xs">
                  ▌
                </span>
                <span className="font-semibold uppercase tracking-wider">
                  {h.company}
                </span>
                <span className="text-zinc-400">{h.title}</span>
                <span className="text-[var(--warn)] text-xs uppercase">
                  {h.status}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* FEATURED */}
      <section data-testid="featured">
        <div className="flex items-end justify-between mb-6">
          <div>
            <div className="label-over">/// featured</div>
            <h2 className="display text-3xl sm:text-4xl font-bold tracking-tight mt-2">
              Hot hackathons this month
            </h2>
          </div>
          <Link
            to="/hackathons"
            className="hidden sm:inline-flex text-sm font-semibold items-center gap-1 hover:gap-2 transition-all"
            data-testid="see-all"
          >
            See all <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {featured.map((h) => (
            <HackathonCard key={h.id} h={h} />
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="border-t border-black/10 pt-12" data-testid="how">
        <div className="label-over">/// how it works</div>
        <h2 className="display text-3xl sm:text-4xl font-bold tracking-tight mt-2 mb-10 max-w-2xl">
          Built for students. Always live.
        </h2>
        <div className="grid md:grid-cols-3 gap-0 border-l border-t border-black/10">
          {[
            {
              n: "01",
              title: "Discover",
              body: "We auto-curate hiring hackathons, conferences, summits, workshops, meetups & invite-only events from India and the world — using Gemini AI.",
            },
            {
              n: "02",
              title: "Prep",
              body: "Each event has typical rounds, eligibility, a personalised checklist and hand-picked learning resources — tailored to students or working professionals.",
            },
            {
              n: "03",
              title: "Win",
              body: "Track deadlines, chat with HackPilot AI for strategy, and walk into your dream event prepared.",
            },
          ].map((s) => (
            <div
              key={s.n}
              className="border-r border-b border-black/10 p-8 hover:bg-zinc-50 transition-colors"
            >
              <div className="font-mono text-zinc-300 text-3xl">{s.n}</div>
              <div className="display text-xl font-semibold mt-3">
                {s.title}
              </div>
              <p className="text-sm text-zinc-600 mt-2 leading-relaxed">
                {s.body}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function StatTile({ label, value, accent, icon, testid }) {
  return (
    <div
      className="relative card-flat p-5 overflow-hidden"
      data-testid={testid}
    >
      <div className="flex items-center justify-between">
        <span className="label-over">{label}</span>
        <span className="text-zinc-400">{icon}</span>
      </div>
      <div className="display font-extrabold text-4xl mt-3">{value}</div>
      {accent && <div className={`h-1 w-12 ${accent} mt-3`} />}
    </div>
  );
}
