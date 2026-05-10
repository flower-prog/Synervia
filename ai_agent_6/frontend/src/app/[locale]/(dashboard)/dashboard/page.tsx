"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  CheckCircle,
  CreditCard,
  Database,
  List,
  MessageSquare,
  Search,
  Sparkles,
  Star,
  XCircle,
} from "lucide-react";
import { ActiveSessions } from "@/components/dashboard/active-sessions";
import { OnboardingBanner } from "@/components/dashboard/onboarding-banner";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { SegmentedControl } from "@/components/dashboard/segmented-control";
import { StatCard } from "@/components/dashboard/stat-card";
import { SubscriptionChip } from "@/components/dashboard/subscription-chip";
import { TeamSummary } from "@/components/dashboard/team-summary";
import { ToolUsage } from "@/components/dashboard/tool-usage";
import { TopModels } from "@/components/dashboard/top-models";
import { UsageTimeline } from "@/components/dashboard/usage-timeline";
import { useAuth } from "@/hooks";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { listCollections, getCollectionInfo } from "@/lib/rag-api";
import type { HealthResponse } from "@/types";

interface CreditBalance {
  balance: number;
  low_threshold: number;
}

interface UsageBucket {
  day: string;
  credits_charged: number;
  total_calls: number;
}

interface UsageTimelineRead {
  buckets: UsageBucket[];
  days: number;
}

interface ConversationsResponse {
  total?: number;
  items: Array<{ id: string }>;
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function pctDelta(current: number[], prior: number[]): number | undefined {
  const cur = current.reduce((a, b) => a + b, 0);
  const prev = prior.reduce((a, b) => a + b, 0);
  if (prev === 0) return cur > 0 ? 100 : 0;
  return ((cur - prev) / prev) * 100;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [credits, setCredits] = useState<CreditBalance | null>(null);
  const [creditsLoading, setCreditsLoading] = useState(true);
  const [conversations, setConversations] = useState<{ total: number } | null>(null);
  const [convLoading, setConvLoading] = useState(true);
  const [ragStats, setRagStats] = useState<{ collections: number; vectors: number } | null>(null);
  const [timeline, setTimeline] = useState<UsageBucket[] | null>(null);
  const [period, setPeriod] = useState<7 | 30 | 90>(7);

  useEffect(() => {
    apiClient
      .get<HealthResponse>("/health")
      .then((d) => {
        setHealth(d);
        setHealthError(false);
      })
      .catch(() => setHealthError(true));

    apiClient
      .get<CreditBalance>("/billing/me/credits")
      .then(setCredits)
      .catch(() => setCredits(null))
      .finally(() => setCreditsLoading(false));

    apiClient
      .get<ConversationsResponse>("/conversations?limit=1")
      .then((d) => setConversations({ total: d.total ?? d.items?.length ?? 0 }))
      .catch(() => setConversations({ total: 0 }))
      .finally(() => setConvLoading(false));
    listCollections()
      .then(async (list) => {
        let totalVectors = 0;
        for (const name of list.items) {
          try {
            const info = await getCollectionInfo(name);
            totalVectors += info.total_vectors;
          } catch {
            /* ignore */
          }
        }
        setRagStats({ collections: list.items.length, vectors: totalVectors });
      })
      .catch(() => setRagStats({ collections: 0, vectors: 0 }));
  }, []);

  // Refetch the timeline whenever the period changes.
  // Fetch period * 2 days so we have current + prior windows for delta math.
  useEffect(() => {
    let cancelled = false;
    setTimeline(null);
    apiClient
      .get<UsageTimelineRead>(`/billing/me/credits/usage/timeline?days=${period * 2}`)
      .then((d) => {
        if (!cancelled) setTimeline(d.buckets);
      })
      .catch(() => {
        if (!cancelled) setTimeline([]);
      });
    return () => {
      cancelled = true;
    };
  }, [period]);

  // Derived sparklines + deltas (last `period`d vs prior `period`d)
  const creditsSpark = (timeline ?? []).slice(-period).map((b) => b.credits_charged);
  const callsSpark = (timeline ?? []).slice(-period).map((b) => b.total_calls);
  const creditsDelta = timeline
    ? pctDelta(
        timeline.slice(-period).map((b) => b.credits_charged),
        timeline.slice(-period * 2, -period).map((b) => b.credits_charged),
      )
    : undefined;
  const callsDelta = timeline
    ? pctDelta(
        timeline.slice(-period).map((b) => b.total_calls),
        timeline.slice(-period * 2, -period).map((b) => b.total_calls),
      )
    : undefined;
  const deltaLabel = `vs prior ${period}d`;

  return (
    <div className="space-y-6 pb-8">
      <OnboardingBanner />

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Dashboard
          </p>
          <h1 className="font-display text-foreground mt-1 text-3xl font-bold tracking-tight sm:text-4xl">
            {getGreeting()}
            {user?.full_name
              ? `, ${user.full_name.split(" ")[0]}`
              : user?.email
                ? `, ${user.email.split("@")[0]}`
                : ""}
            <span className="text-foreground/30">.</span>
          </h1>
          <p className="text-foreground/65 mt-1 text-sm">
            Here&apos;s what&apos;s happening with your workspace.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <SearchHint />
          <Link
            href={ROUTES.CHAT}
            className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors"
          >
            <MessageSquare className="h-4 w-4" />
            New chat
          </Link>
        </div>
      </div>

      {/* Stat cards */}
      <div className="flex items-center justify-between">
        <h2 className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          Workspace metrics
        </h2>
        <SegmentedControl
          value={String(period)}
          onChange={(v) => setPeriod(Number(v) as 7 | 30 | 90)}
          options={[
            { label: "7d", value: "7" },
            { label: "30d", value: "30" },
            { label: "90d", value: "90" },
          ]}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Credits balance"
          value={creditsLoading ? "—" : credits ? credits.balance.toLocaleString() : "0"}
          icon={Sparkles}
          delta={creditsDelta}
          deltaLabel={deltaLabel}
          spark={creditsSpark.length >= 2 ? creditsSpark : [0, 0]}
          loading={creditsLoading}
          featured
        />
        <StatCard
          label="Conversations"
          value={convLoading ? "—" : (conversations?.total ?? 0).toLocaleString()}
          icon={MessageSquare}
          loading={convLoading}
        />
        <StatCard
          label={`API calls (${period}d)`}
          value={timeline ? callsSpark.reduce((a, b) => a + b, 0).toLocaleString() : "—"}
          icon={Activity}
          delta={callsDelta}
          deltaLabel={deltaLabel}
          spark={callsSpark.length >= 2 ? callsSpark : [0, 0]}
          loading={!timeline}
        />
        <StatCard
          label="Knowledge base"
          value={ragStats ? ragStats.vectors.toLocaleString() : "—"}
          unit={ragStats ? `vector${ragStats.vectors === 1 ? "" : "s"}` : undefined}
          icon={Database}
          loading={!ragStats}
        />
      </div>

      {/* Status strip */}
      <div className="border-border bg-card flex flex-wrap items-center gap-x-6 gap-y-2 rounded-2xl border px-5 py-3 text-xs">
        <span className="inline-flex items-center gap-2">
          {healthError ? (
            <>
              <XCircle className="text-destructive h-4 w-4" />
              <span className="text-destructive font-mono tracking-wider uppercase">
                API offline
              </span>
            </>
          ) : (
            <>
              <CheckCircle className="text-brand h-4 w-4" />
              <span className="text-foreground/70 font-mono tracking-wider uppercase">
                {health?.status || "Operational"}
              </span>
            </>
          )}
        </span>
        {health?.version && (
          <span className="text-foreground/45 font-mono tracking-wider uppercase">
            v{health.version}
          </span>
        )}
        <span className="text-foreground/45 font-mono tracking-wider uppercase">
          {ragStats
            ? `${ragStats.collections} collection${ragStats.collections === 1 ? "" : "s"}`
            : "—"}
        </span>
        {credits && credits.low_threshold > 0 && (
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase",
              credits.balance < credits.low_threshold
                ? "bg-destructive/10 text-destructive"
                : "text-foreground/45",
            )}
            title={
              credits.balance < credits.low_threshold
                ? "Balance dropped below the auto-refill threshold"
                : "Auto-refill threshold (turns the chip red when crossed)"
            }
          >
            {credits.balance < credits.low_threshold ? "Below threshold" : "Threshold"}{" "}
            {credits.low_threshold.toLocaleString()}
          </span>
        )}
        <SubscriptionChip />
        <Link
          href={ROUTES.BILLING}
          className="text-foreground/55 hover:text-foreground ml-auto inline-flex items-center gap-1 font-mono tracking-wider uppercase"
        >
          <CreditCard className="h-3.5 w-3.5" />
          Manage billing →
        </Link>
      </div>

      {/* Usage timeline (full width) */}
      <UsageTimeline />

      {/* Activity + behavior insights */}
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <RecentActivity />
        <TopModels />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ToolUsage />
        <TeamSummary />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ActiveSessions />
      </div>

      <QuickActions />

      {/* Admin row */}
      {user?.role === "admin" && (
        <div>
          <h2 className="font-display text-foreground mb-3 text-base font-semibold">
            Admin actions
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <AdminTile
              icon={Star}
              label="Response ratings"
              description="View and manage ratings"
              href={ROUTES.ADMIN_RATINGS}
            />
            <AdminTile
              icon={List}
              label="All conversations"
              description="Inspect any user's chats"
              href={ROUTES.ADMIN_CONVERSATIONS}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function SearchHint() {
  return (
    <div className="border-foreground/15 bg-background hidden items-center gap-2 rounded-full border px-3 py-1.5 text-xs sm:inline-flex">
      <Search className="text-foreground/45 h-3.5 w-3.5" />
      <span className="text-foreground/55">Search</span>
      <kbd className="border-foreground/15 bg-card text-foreground/65 rounded-md border px-1.5 py-0.5 font-mono text-[10px]">
        ⌘K
      </kbd>
    </div>
  );
}

function AdminTile({
  icon: Icon,
  label,
  description,
  href,
}: {
  icon: typeof Star;
  label: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="lift border-border hover:border-foreground/30 bg-card flex items-center gap-3 rounded-2xl border p-4 transition-colors"
    >
      <span className="bg-foreground/8 text-foreground flex h-9 w-9 items-center justify-center rounded-full">
        <Icon className="h-4 w-4" />
      </span>
      <div className="flex-1">
        <p className="text-foreground text-sm font-semibold">{label}</p>
        <p className="text-foreground/55 text-xs">{description}</p>
      </div>
    </Link>
  );
}
