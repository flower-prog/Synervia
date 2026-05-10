"use client";

import { useEffect } from "react";
import { Database, Lock, Sparkles, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui";
import { Checkbox } from "@/components/ui/checkbox";
import { useKnowledgeBases, useConversations } from "@/hooks";
import { useConversationStore, useKBSelectionStore } from "@/stores";
import { cn } from "@/lib/utils";
import type { KBScope, KnowledgeBase } from "@/types";

const SCOPE_META: Record<KBScope, { label: string; icon: LucideIcon }> = {
  personal: { label: "Personal", icon: Lock },
  org: { label: "Organization", icon: Users },
  app: { label: "App-wide", icon: Sparkles },
};

const SECTION_ORDER: KBScope[] = ["personal", "org", "app"];

/**
 * Popover for picking which knowledge bases the agent should search.
 *
 * Mirrors the visual treatment of <ChatSettings>: a small chip in the chat
 * footer that opens a popover. Selection is held in <useKBSelectionStore>
 * (localStorage-persisted) so it survives refresh and applies to the next
 * outbound message — which means it works *before* the conversation row
 * exists, the bug the side-panel approach had.
 */
export function KBSelector() {
  const { kbs, isLoading, fetchKBs } = useKnowledgeBases();
  const { currentConversationId, conversations } = useConversationStore();
  const { updateActiveKBs } = useConversations();

  const activeKBIds = useKBSelectionStore((s) => s.activeKBIds);
  const toggleKB = useKBSelectionStore((s) => s.toggle);
  const hydrate = useKBSelectionStore((s) => s.hydrateFromConversation);

  // Lazy-load KBs the first time the popover opens; cheap, won't refetch on
  // every open since the hook keeps state across renders.
  useEffect(() => {
    if (kbs.length === 0 && !isLoading) fetchKBs();
  }, [kbs.length, isLoading, fetchKBs]);

  // Hydrate from a saved conversation so its persisted selection wins over
  // the local draft on open.
  const conversation = conversations.find((c) => c.id === currentConversationId);
  useEffect(() => {
    if (currentConversationId && conversation) {
      hydrate(conversation.active_knowledge_base_ids ?? null);
    }
  }, [currentConversationId, conversation, hydrate]);

  const activeIds = new Set<string>(activeKBIds);
  const grouped = kbs.reduce<Record<KBScope, KnowledgeBase[]>>(
    (acc, kb) => {
      (acc[kb.scope] ??= []).push(kb);
      return acc;
    },
    { personal: [], org: [], app: [] },
  );

  const handleToggle = async (kb: KnowledgeBase, checked: boolean) => {
    toggleKB(kb.id);
    if (currentConversationId) {
      const next = checked ? [...activeKBIds, kb.id] : activeKBIds.filter((id) => id !== kb.id);
      await updateActiveKBs(currentConversationId, next);
    }
  };

  const sections = SECTION_ORDER.filter((s) => grouped[s].length > 0);
  const activeCount = activeIds.size;
  const hasAny = kbs.length > 0;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Knowledge bases"
          className={cn(
            "text-foreground/55 hover:bg-foreground/5 hover:text-foreground inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-mono text-[11px] tracking-wider uppercase transition-colors",
            activeCount > 0 && "text-foreground",
          )}
        >
          <Database className="h-3.5 w-3.5" />
          {activeCount === 0 ? "KB" : `${activeCount} KB${activeCount === 1 ? "" : "s"}`}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-0">
        <div className="border-foreground/10 border-b px-3 py-2">
          <p className="text-foreground text-xs font-semibold">Knowledge bases</p>
          <p className="text-foreground/55 mt-0.5 text-[11px] leading-relaxed">
            Picked KBs are searched on every message you send.
          </p>
        </div>

        <div className="max-h-80 scrollbar-thin overflow-y-auto p-2">
          {isLoading && kbs.length === 0 ? (
            <p className="text-foreground/55 px-2 py-3 text-xs">Loading…</p>
          ) : !hasAny ? (
            <p className="text-foreground/55 px-2 py-3 text-xs">
              No knowledge bases yet — create one on the Knowledge Bases page.
            </p>
          ) : (
            sections.map((scope) => {
              const meta = SCOPE_META[scope];
              return (
                <section key={scope} className="mb-2 last:mb-0">
                  <div className="text-foreground/55 mb-1 flex items-center gap-1.5 px-2 font-mono text-[10px] tracking-wider uppercase">
                    <meta.icon className="h-3 w-3" />
                    {meta.label}
                  </div>
                  <ul className="space-y-0.5">
                    {grouped[scope].map((kb) => {
                      const isActive = activeIds.has(kb.id);
                      return (
                        <li key={kb.id}>
                          <label className="hover:bg-foreground/[0.04] flex cursor-pointer items-start gap-2.5 rounded-md px-2 py-1.5 transition-colors">
                            <Checkbox
                              checked={isActive}
                              onCheckedChange={(c) => handleToggle(kb, c as boolean)}
                              className="mt-0.5 shrink-0"
                            />
                            <div className="min-w-0">
                              <p className="text-foreground truncate text-xs leading-tight font-medium">
                                {kb.name}
                              </p>
                              {kb.description && (
                                <p className="text-foreground/55 mt-0.5 line-clamp-1 text-[11px]">
                                  {kb.description}
                                </p>
                              )}
                            </div>
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              );
            })
          )}
        </div>

        <div className="border-foreground/10 text-foreground/45 flex items-center justify-between border-t px-3 py-1.5 font-mono text-[10px] tracking-wider uppercase">
          <span>
            {activeCount} of {kbs.length} active
          </span>
          {!currentConversationId && hasAny && (
            <span className="text-foreground/55">draft · saves on send</span>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
