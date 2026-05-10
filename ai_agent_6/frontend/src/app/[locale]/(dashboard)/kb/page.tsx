"use client";

import { useEffect, useState } from "react";
import { Database, Plus } from "lucide-react";

import { CreateKBDialog, KBList } from "@/components/kb";
import { EmptyState, LoadingState } from "@/components/states";
import { useKnowledgeBases } from "@/hooks";

export default function KBPage() {
  const { kbs, isLoading, fetchKBs, deleteKB } = useKnowledgeBases();
  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    fetchKBs();
  }, [fetchKBs]);

  return (
    <div className="mx-auto w-full max-w-3xl space-y-8">
      <header className="space-y-2">
        <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          Knowledge bases
        </p>
        <h1 className="font-display text-foreground text-3xl font-bold tracking-tight sm:text-4xl">
          Documents your assistant can use
        </h1>
        <p className="text-foreground/65 max-w-xl text-sm">
          Group related documents into a knowledge base. Open one to upload files, then toggle in
          chat which ones the agent should search.
        </p>
        <div className="pt-2">
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            New knowledge base
          </button>
        </div>
      </header>

      {isLoading ? (
        <LoadingState variant="skeleton-list" rows={4} />
      ) : kbs.length === 0 ? (
        <EmptyState
          icon={Database}
          title="No knowledge bases yet"
          description="Create one to give your assistant access to documents from collections."
          cta={{ label: "Create knowledge base", onClick: () => setCreateOpen(true) }}
        />
      ) : (
        <KBList kbs={kbs} onDelete={deleteKB} />
      )}

      <CreateKBDialog open={createOpen} onOpenChange={setCreateOpen} onCreated={() => fetchKBs()} />
    </div>
  );
}
