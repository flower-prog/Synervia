{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"use client";
{% raw %}
import { useCallback, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import type { KnowledgeBase, KnowledgeBaseList, CreateKnowledgeBaseInput } from "@/types";

export function useKnowledgeBases() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchKBs = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.get<KnowledgeBaseList>("/kb");
      setKbs(data.items);
    } catch {
      toast.error("Failed to load knowledge bases");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createKB = useCallback(
    async (input: CreateKnowledgeBaseInput): Promise<KnowledgeBase | null> => {
      try {
        const kb = await apiClient.post<KnowledgeBase>("/kb", input);
        setKbs((prev) => [kb, ...prev]);
        toast.success("Knowledge base created");
        return kb;
      } catch {
        toast.error("Failed to create knowledge base");
        return null;
      }
    },
    []
  );

  const patchKB = useCallback(async (id: string, patch: Partial<Pick<KnowledgeBase, "name" | "description" | "is_active">>) => {
    try {
      const updated = await apiClient.patch<KnowledgeBase>(`/kb/${id}`, patch);
      setKbs((prev) => prev.map((k) => (k.id === id ? updated : k)));
      toast.success("Knowledge base updated");
      return updated;
    } catch {
      toast.error("Failed to update knowledge base");
      return null;
    }
  }, []);

  const deleteKB = useCallback(async (id: string) => {
    try {
      await apiClient.delete(`/kb/${id}`);
      setKbs((prev) => prev.filter((k) => k.id !== id));
      toast.success("Knowledge base deleted");
    } catch {
      toast.error("Failed to delete knowledge base");
    }
  }, []);

  return { kbs, isLoading, fetchKBs, createKB, patchKB, deleteKB };
}
{% endraw %}
{%- endif %}
