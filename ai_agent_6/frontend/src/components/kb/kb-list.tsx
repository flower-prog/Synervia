"use client";

import Link from "next/link";
import { ChevronRight, Lock, Sparkles, Trash2, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import type { KBScope, KnowledgeBase } from "@/types";

interface KBListProps {
  kbs: KnowledgeBase[];
  onDelete: (id: string) => void;
  canDelete?: boolean;
}

interface ScopeMeta {
  label: string;
  icon: LucideIcon;
  description: string;
}

const SCOPE_META: Record<KBScope, ScopeMeta> = {
  personal: {
    label: "Personal",
    icon: Lock,
    description: "Only you can see and edit these.",
  },
  org: {
    label: "Organization",
    icon: Users,
    description: "Shared with your active organization.",
  },
  app: {
    label: "App-wide",
    icon: Sparkles,
    description: "Available to everyone in this workspace.",
  },
};

const SECTION_ORDER: KBScope[] = ["personal", "org", "app"];

export function KBList({ kbs, onDelete, canDelete = true }: KBListProps) {
  const grouped = kbs.reduce<Record<KBScope, KnowledgeBase[]>>(
    (acc, kb) => {
      (acc[kb.scope] ??= []).push(kb);
      return acc;
    },
    { personal: [], org: [], app: [] },
  );

  if (!kbs.length) return null;

  const sections = SECTION_ORDER.filter((s) => grouped[s].length > 0);

  return (
    <div className="space-y-8">
      {sections.map((scope) => {
        const meta = SCOPE_META[scope];
        return (
          <section key={scope} className="space-y-3">
            <div className="flex items-baseline justify-between gap-3">
              <div>
                <h3 className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
                  {meta.label}
                </h3>
                <p className="text-foreground/45 mt-0.5 text-xs">{meta.description}</p>
              </div>
              <span className="text-foreground/45 font-mono text-[10px] tracking-wider uppercase">
                {grouped[scope].length}
              </span>
            </div>

            <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-2xl border">
              {grouped[scope].map((kb) => (
                <KBRow
                  key={kb.id}
                  kb={kb}
                  scopeIcon={meta.icon}
                  canDelete={canDelete}
                  onDelete={() => onDelete(kb.id)}
                />
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

interface KBRowProps {
  kb: KnowledgeBase;
  scopeIcon: LucideIcon;
  canDelete: boolean;
  onDelete: () => void;
}

function KBRow({ kb, scopeIcon: ScopeIcon, canDelete, onDelete }: KBRowProps) {
  return (
    <li className="group hover:bg-foreground/[0.02] relative flex items-center gap-4 px-4 py-3.5 transition-colors first:rounded-t-2xl last:rounded-b-2xl">
      {/* Whole-row link, placed absolute. Visible content uses pointer-events:
          none so clicks fall through to the link; the action buttons re-enable
          pointer events on themselves so they stay independently clickable. */}
      <Link
        href={`/kb/${kb.id}`}
        className="focus-visible:ring-foreground/20 absolute inset-0 rounded-[inherit] focus-visible:ring-2 focus-visible:outline-none"
        aria-label={`Open ${kb.name}`}
      />

      {/* Scope icon */}
      <span
        className={cn(
          "bg-foreground/8 text-foreground/65 group-hover:bg-foreground/12 pointer-events-none relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-colors",
        )}
      >
        <ScopeIcon className="h-4 w-4" />
      </span>

      {/* Name + description */}
      <div className="pointer-events-none relative min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-foreground truncate text-sm font-medium">{kb.name}</p>
          {kb.is_default && (
            <span className="border-foreground/15 text-foreground/55 inline-flex shrink-0 items-center rounded-full border px-1.5 py-0.5 font-mono text-[9px] tracking-wider uppercase">
              Default
            </span>
          )}
        </div>
        {kb.description ? (
          <p className="text-foreground/55 mt-0.5 line-clamp-1 text-xs">{kb.description}</p>
        ) : (
          <p className="text-foreground/35 mt-0.5 truncate font-mono text-[10px] tracking-wider uppercase">
            {kb.collection_name}
          </p>
        )}
      </div>

      {/* Actions — pointer-events-auto re-enables clicks above the link */}
      <div className="pointer-events-none relative flex items-center gap-1">
        {canDelete && !kb.is_default && (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (
                confirm(
                  `Delete "${kb.name}"? This will remove the knowledge base and all its documents.`,
                )
              ) {
                onDelete();
              }
            }}
            className="text-foreground/45 hover:bg-destructive/10 hover:text-destructive pointer-events-auto inline-flex h-8 w-8 items-center justify-center rounded-lg opacity-0 transition-all group-hover:opacity-100 focus-visible:opacity-100"
            title="Delete knowledge base"
            aria-label="Delete knowledge base"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
        <ChevronRight className="text-foreground/30 group-hover:text-foreground/60 h-4 w-4 transition-colors" />
      </div>
    </li>
  );
}
