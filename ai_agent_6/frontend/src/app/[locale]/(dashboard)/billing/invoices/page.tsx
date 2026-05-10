"use client";

import { InvoicesPanel } from "@/components/billing";

export default function InvoicesPage() {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <header>
        <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          Billing · Invoices
        </p>
        <h1 className="font-display text-foreground mt-1 text-3xl font-bold tracking-tight sm:text-4xl">
          Billing history
        </h1>
        <p className="text-foreground/65 mt-1 max-w-xl text-sm">
          Every invoice sent to this workspace, with a download link straight to the Stripe-hosted
          PDF.
        </p>
      </header>
      <InvoicesPanel />
    </div>
  );
}
