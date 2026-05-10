import Link from "next/link";
import { Check, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

interface Plan {
  name: string;
  price: string;
  cadence?: string;
  description: string;
  features: string[];
  cta: { label: string; href: string };
  featured?: boolean;
  badge?: string;
}

interface PricingTeaserProps {
  plans: Plan[];
  fullPricingHref?: string;
}

export function PricingTeaser({ plans, fullPricingHref = "/pricing" }: PricingTeaserProps) {
  return (
    <div className="space-y-12">
      <div className="grid items-stretch gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={cn(
              "relative flex flex-col rounded-2xl border p-8 transition-transform",
              plan.featured
                ? "border-brand bg-brand/[0.06] -translate-y-2 shadow-2xl"
                : "border-foreground/15 bg-card lift",
            )}
          >
            {plan.badge && (
              <div className="bg-brand text-brand-foreground absolute -top-3 left-1/2 inline-flex -translate-x-1/2 items-center gap-1 rounded-full px-3 py-1 font-mono text-[11px] font-semibold tracking-wider uppercase">
                <Sparkles className="h-3 w-3" />
                {plan.badge}
              </div>
            )}

            <div>
              <p className="eyebrow text-foreground/55">{plan.name}</p>
              <div className="mt-4 flex items-baseline gap-2">
                <span className="font-display text-foreground text-5xl font-bold tracking-tight">
                  {plan.price}
                </span>
                {plan.cadence && <span className="text-foreground/55 text-sm">{plan.cadence}</span>}
              </div>
              <p className="text-foreground/65 mt-2 text-sm">{plan.description}</p>
            </div>

            <ul className="mt-8 flex-1 space-y-3">
              {plan.features.map((f) => (
                <li key={f} className="text-foreground/85 flex gap-3 text-sm">
                  <span
                    className={cn(
                      "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                      plan.featured
                        ? "bg-brand text-brand-foreground"
                        : "bg-foreground/8 text-foreground",
                    )}
                  >
                    <Check className="h-3 w-3" />
                  </span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>

            <Link
              href={plan.cta.href}
              className={cn(
                "mt-8 inline-flex w-full items-center justify-center rounded-full px-5 py-3 text-sm font-medium transition-colors",
                plan.featured
                  ? "bg-foreground text-background hover:bg-foreground/90"
                  : "border-foreground/20 hover:border-foreground/40 hover:bg-foreground hover:text-background border",
              )}
            >
              {plan.cta.label}
            </Link>
          </div>
        ))}
      </div>

      <div className="text-center">
        <Link
          href={fullPricingHref}
          className="border-foreground/15 hover:border-foreground/40 text-foreground/70 hover:text-foreground inline-flex items-center gap-2 border-b pb-1 text-sm font-medium transition-colors"
        >
          See full pricing comparison →
        </Link>
      </div>
    </div>
  );
}
