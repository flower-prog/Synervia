{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"use client";
{% raw %}
import { useEffect, useState } from "react";
import { Plus, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { KBList, CreateKBDialog } from "@/components/kb";
import { useKnowledgeBases } from "@/hooks";

export default function KBPage() {
  const { kbs, isLoading, fetchKBs, patchKB, deleteKB } = useKnowledgeBases();
  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    fetchKBs();
  }, [fetchKBs]);

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Database className="h-6 w-6" />
            Knowledge Bases
          </h1>
          <p className="text-sm text-muted-foreground">
            Manage your document collections used for AI retrieval.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New knowledge base
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : (
        <KBList
          kbs={kbs}
          onToggle={(id, active) => patchKB(id, { is_active: active })}
          onDelete={deleteKB}
        />
      )}

      <CreateKBDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => fetchKBs()}
      />
    </div>
  );
}
{% endraw %}
{%- endif %}
