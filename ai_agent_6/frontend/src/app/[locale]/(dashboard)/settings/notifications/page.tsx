"use client";

import { useEffect, useMemo, useState } from "react";
import { CreditCard, MessageSquare, Sparkles, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { toast } from "sonner";

import { SettingsSection } from "@/components/settings/settings-section";
import { Button } from "@/components/ui";

interface NotificationCategory {
  key: string;
  label: string;
  description: string;
  icon: LucideIcon;
  /** Default values for new users. */
  defaults: { email: boolean; inApp: boolean };
}

const CATEGORIES: NotificationCategory[] = [
  {
    key: "billing",
    label: "Billing",
    description: "Subscription renewals, payment failures, low credit warnings.",
    icon: CreditCard,
    defaults: { email: true, inApp: true },
  },
  {
    key: "members",
    label: "Team activity",
    description: "Invitations accepted, members joining or leaving your workspace.",
    icon: Users,
    defaults: { email: true, inApp: true },
  },
  {
    key: "security",
    label: "Security alerts",
    description: "New device sign-ins, password changes, suspicious activity.",
    icon: MessageSquare,
    defaults: { email: true, inApp: true },
  },
  {
    key: "product",
    label: "Product updates",
    description: "New features, release notes, occasional how-to tips.",
    icon: Sparkles,
    defaults: { email: false, inApp: true },
  },
];

const STORAGE_KEY = "settings.notifications.prefs";

type Prefs = Record<string, { email: boolean; inApp: boolean }>;

function defaultPrefs(): Prefs {
  return Object.fromEntries(
    CATEGORIES.map((c) => [c.key, { email: c.defaults.email, inApp: c.defaults.inApp }]),
  );
}

function loadPrefs(): Prefs {
  if (typeof window === "undefined") return defaultPrefs();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultPrefs();
    return { ...defaultPrefs(), ...(JSON.parse(raw) as Prefs) };
  } catch {
    return defaultPrefs();
  }
}

function savePrefs(prefs: Prefs) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export default function NotificationsSettingsPage() {
  const [prefs, setPrefs] = useState<Prefs>(defaultPrefs);
  const [dirty, setDirty] = useState(false);
  const initialPrefs = useMemo(loadPrefs, []);

  useEffect(() => {
    setPrefs(initialPrefs);
  }, [initialPrefs]);

  const toggle = (key: string, channel: "email" | "inApp") => {
    setPrefs((prev) => ({
      ...prev,
      [key]: {
        email: prev[key]?.email ?? true,
        inApp: prev[key]?.inApp ?? true,
        [channel]: !(prev[key]?.[channel] ?? true),
      },
    }));
    setDirty(true);
  };

  const handleSave = () => {
    savePrefs(prefs);
    toast.success("Notification preferences saved");
    setDirty(false);
  };

  const handleReset = () => {
    setPrefs(defaultPrefs());
    setDirty(true);
  };

  return (
    <div className="space-y-6">
      <SettingsSection
        title="Notification preferences"
        description="Pick which events we send by email versus only show in-app."
        action={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleReset} className="rounded-full">
              Reset to defaults
            </Button>
            <Button onClick={handleSave} disabled={!dirty} size="sm" className="rounded-full">
              Save changes
            </Button>
          </div>
        }
      >
        <div className="border-foreground/10 bg-background overflow-hidden rounded-xl border">
          <div className="border-foreground/10 grid grid-cols-[1fr_70px_70px] items-center gap-2 border-b px-5 py-3 sm:grid-cols-[1.5fr_90px_90px]">
            <span className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
              Category
            </span>
            <span className="text-foreground/55 text-center font-mono text-[11px] tracking-wider uppercase">
              Email
            </span>
            <span className="text-foreground/55 text-center font-mono text-[11px] tracking-wider uppercase">
              In-app
            </span>
          </div>
          <ul className="divide-foreground/10 divide-y">
            {CATEGORIES.map((c) => {
              const p = prefs[c.key] ?? c.defaults;
              return (
                <li
                  key={c.key}
                  className="grid grid-cols-[1fr_70px_70px] items-center gap-2 px-5 py-4 sm:grid-cols-[1.5fr_90px_90px]"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="bg-foreground/8 text-foreground/70 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full">
                      <c.icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-foreground text-sm font-semibold">{c.label}</p>
                      <p className="text-foreground/55 mt-0.5 text-xs leading-relaxed">
                        {c.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex justify-center">
                    <Toggle checked={p.email} onChange={() => toggle(c.key, "email")} />
                  </div>
                  <div className="flex justify-center">
                    <Toggle checked={p.inApp} onChange={() => toggle(c.key, "inApp")} />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
        <p className="text-foreground/55 mt-4 text-xs leading-relaxed">
          Preferences are stored locally for now. Backend wiring required (
          <code className="font-mono">/users/me/notifications</code>) to sync across devices.
        </p>
      </SettingsSection>
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        checked ? "bg-brand" : "bg-foreground/15"
      }`}
    >
      <span
        aria-hidden
        className={`bg-card inline-block h-4 w-4 transform rounded-full shadow transition-transform ${
          checked ? "translate-x-[1.125rem]" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}
