"use client";

import { PaymentMethodsPanel } from "@/components/billing";

export default function PaymentMethodsPage() {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <header>
        <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          Billing · Payment methods
        </p>
        <h1 className="font-display text-foreground mt-1 text-3xl font-bold tracking-tight sm:text-4xl">
          Cards on file
        </h1>
        <p className="text-foreground/65 mt-1 max-w-xl text-sm">
          Cards and bank accounts you can charge are managed in the Stripe billing portal — open it
          to add, remove, or set a default.
        </p>
      </header>
      <PaymentMethodsPanel />
    </div>
  );
}
