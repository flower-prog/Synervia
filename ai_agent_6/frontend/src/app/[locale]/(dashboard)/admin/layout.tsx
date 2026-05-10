import type { ReactNode } from "react";

import { AdminNav } from "@/components/admin/admin-nav";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-7xl pb-10">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Admin · power-user tools
          </p>
          <h1 className="font-display text-foreground mt-1 text-3xl font-bold tracking-tight sm:text-4xl">
            Operate the workspace
          </h1>
        </div>
        <span className="border-foreground/15 text-foreground/65 inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[11px] tracking-wider uppercase">
          <span aria-hidden className="bg-brand h-1.5 w-1.5 rounded-full" />
          Admin role required
        </span>
      </header>

      <div className="grid gap-6 lg:grid-cols-[200px_1fr] lg:gap-8">
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <AdminNav />
        </aside>
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}
