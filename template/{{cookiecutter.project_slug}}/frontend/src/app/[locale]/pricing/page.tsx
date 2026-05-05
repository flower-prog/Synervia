{%- if cookiecutter.enable_comparison_pages %}
"use client";
{% raw %}
import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import Link from "next/link";
import { LandingNav } from "@/components/layout/landing-nav";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api-client";

interface PlanRead {
  id: string;
  code: string;
  display_name: string;
  description: string | null;
  monthly_credits_base: number;
  features: Record<string, unknown>;
  prices: Array<{
    id: string;
    currency: string;
    unit_amount: number;
    interval: string;
    is_active: boolean;
    trial_period_days: number | null;
  }>;
}

export default function PricingPage() {
  const [plans, setPlans] = useState<PlanRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [billing, setBilling] = useState<"month" | "year">("month");

  useEffect(() => {
    apiClient
      .get<{ items: PlanRead[]; total: number }>("/billing/plans")
      .then((d) => setPlans(d.items))
      .catch(() => setPlans([]))
      .finally(() => setIsLoading(false));
  }, []);

  const activePlans = plans.filter((p) =>
    p.prices.some((pr) => pr.is_active && pr.interval === billing)
  );

  return (
    <>
      <LandingNav />
      <main className="mx-auto max-w-5xl px-4 py-16">
        <div className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-bold">Simple, transparent pricing</h1>
          <p className="mb-8 text-lg text-muted-foreground">
            Start free. Upgrade when you&apos;re ready.
          </p>
          <div className="inline-flex rounded-lg border p-1">
            <button
              onClick={() => setBilling("month")}
              className={`rounded-md px-4 py-2 text-sm font-medium transition ${
                billing === "month"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBilling("year")}
              className={`rounded-md px-4 py-2 text-sm font-medium transition ${
                billing === "year"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              }`}
            >
              Annual
              <Badge variant="secondary" className="ml-2 text-xs">
                Save 20%
              </Badge>
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="grid gap-6 sm:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-96 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {activePlans.map((plan, i) => {
              const price = plan.prices.find((p) => p.is_active && p.interval === billing);
              const isPopular = i === 1;
              return (
                <Card
                  key={plan.id}
                  className={`relative flex flex-col ${
                    isPopular ? "border-primary shadow-lg" : ""
                  }`}
                >
                  {isPopular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <Badge className="px-3">Most Popular</Badge>
                    </div>
                  )}
                  <CardHeader>
                    <CardTitle>{plan.display_name}</CardTitle>
                    <CardDescription>{plan.description}</CardDescription>
                    {price && (
                      <div className="mt-4">
                        <span className="text-4xl font-bold">
                          {(price.unit_amount / 100).toLocaleString("en-US", {
                            style: "currency",
                            currency: price.currency.toUpperCase(),
                            minimumFractionDigits: 0,
                          })}
                        </span>
                        <span className="text-muted-foreground">/ {billing}</span>
                      </div>
                    )}
                    {price?.trial_period_days && (
                      <p className="text-sm text-muted-foreground">
                        {price.trial_period_days}-day free trial
                      </p>
                    )}
                  </CardHeader>
                  <CardContent className="flex flex-1 flex-col justify-between gap-6">
                    <ul className="space-y-2 text-sm">
                      {plan.monthly_credits_base > 0 && (
                        <li className="flex items-center gap-2">
                          <Check className="h-4 w-4 text-primary" />
                          {plan.monthly_credits_base.toLocaleString()} credits / month
                        </li>
                      )}
                      {Object.entries(plan.features)
                        .filter(([, v]) => v === true || typeof v === "string")
                        .slice(0, 5)
                        .map(([k, v]) => (
                          <li key={k} className="flex items-center gap-2">
                            <Check className="h-4 w-4 text-primary" />
                            {typeof v === "string" ? v : k.replace(/_/g, " ")}
                          </li>
                        ))}
                    </ul>
                    <Button
                      asChild
                      className="w-full"
                      variant={isPopular ? "default" : "outline"}
                    >
                      <Link href="/auth/register">Get Started</Link>
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
{% endraw %}
{%- else %}
export default function PricingPage() {
  return null;
}
{%- endif %}
