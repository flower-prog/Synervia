import type { ReactNode } from "react";

import { SettingsNav } from "@/components/settings/settings-nav";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 pb-10">
      <header>
        <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          Settings
        </p>
        <h1 className="font-display text-foreground mt-1 text-3xl font-bold tracking-tight sm:text-4xl">
          Workspace settings
        </h1>
        <p className="text-foreground/65 mt-1 text-sm">
          Personal account, API keys, notifications, integrations.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[220px_1fr] lg:gap-10">
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <SettingsNav />
        </aside>
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}
