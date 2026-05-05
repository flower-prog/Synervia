{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system and cookiecutter.enable_teams %}
"use client";
{% raw %}
import { useEffect, useState, useCallback } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";

interface UsageAggregate {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_tokens: number;
  total_credits_charged: number;
  total_events: number;
  by_model: Array<{
    model: string;
    provider: string;
    input_tokens: number;
    output_tokens: number;
    credits_charged: number;
    events: number;
  }>;
}

interface CreditTransaction {
  id: string;
  delta: number;
  balance_after: number;
  type: string;
  description: string | null;
  created_at: string;
}

export default function UsageDashboardPage() {
  const [aggregate, setAggregate] = useState<UsageAggregate | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUsage = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.get<UsageAggregate>("/billing/me/credits/usage");
      setAggregate(data);
    } catch {
      setAggregate(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  const handleExport = async () => {
    try {
      const txData = await apiClient.get<{ items: CreditTransaction[] }>(
        "/billing/me/credits/transactions?skip=0&limit=1000"
      );
      const csv = [
        "Date,Type,Delta,Balance After,Description",
        ...txData.items.map((t) =>
          [
            new Date(t.created_at).toISOString(),
            t.type,
            t.delta,
            t.balance_after,
            `"${(t.description ?? "").replace(/"/g, '""')}"`,
          ].join(",")
        ),
      ].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "credits-export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  const chartData =
    aggregate?.by_model.map((m) => ({
      name: m.model.split("-").slice(-2).join("-"),
      input: m.input_tokens,
      output: m.output_tokens,
      credits: m.credits_charged,
    })) ?? [];

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Usage Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Token consumption and credit usage across your organization.
          </p>
        </div>
        <Button variant="outline" onClick={handleExport}>
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Credits Used</CardDescription>
              <CardTitle className="text-3xl tabular-nums">
                {aggregate?.total_credits_charged.toLocaleString() ?? "—"}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Tokens</CardDescription>
              <CardTitle className="text-3xl tabular-nums">
                {aggregate
                  ? (aggregate.total_input_tokens + aggregate.total_output_tokens).toLocaleString()
                  : "—"}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total API Calls</CardDescription>
              <CardTitle className="text-3xl tabular-nums">
                {aggregate?.total_events.toLocaleString() ?? "—"}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {!isLoading && chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Credits by Model</CardTitle>
            <CardDescription>Credit consumption broken down by model.</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 12 }}
                  className="fill-muted-foreground"
                />
                <YAxis tick={{ fontSize: 12 }} className="fill-muted-foreground" />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "6px",
                  }}
                />
                <Bar dataKey="credits" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {!isLoading && aggregate && aggregate.by_model.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Per-Model Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {aggregate.by_model.map((m) => (
                <div key={m.model} className="grid grid-cols-4 gap-4 py-3 text-sm">
                  <div className="col-span-2">
                    <p className="font-medium">{m.model}</p>
                    <p className="text-xs text-muted-foreground">{m.provider}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Tokens</p>
                    <p className="font-mono">{(m.input_tokens + m.output_tokens).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Credits</p>
                    <p className="font-mono">{m.credits_charged.toLocaleString()}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
{% endraw %}
{%- else %}
export default function UsageDashboardPage() {
  return null;
}
{%- endif %}
