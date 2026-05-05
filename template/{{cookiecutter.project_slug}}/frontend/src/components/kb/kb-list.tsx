{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"use client";
{% raw %}
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Trash2 } from "lucide-react";
import type { KnowledgeBase } from "@/types";

interface KBListProps {
  kbs: KnowledgeBase[];
  onToggle: (id: string, active: boolean) => void;
  onDelete: (id: string) => void;
  canDelete?: boolean;
}

const scopeColors: Record<string, string> = {
  personal: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  organization: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  app: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
};

export function KBList({ kbs, onToggle, onDelete, canDelete = true }: KBListProps) {
  const grouped = kbs.reduce<Record<string, KnowledgeBase[]>>((acc, kb) => {
    if (!acc[kb.scope]) acc[kb.scope] = [];
    acc[kb.scope].push(kb);
    return acc;
  }, {});

  const sections = [
    { key: "personal", label: "Personal" },
    { key: "organization", label: "Organization" },
    { key: "app", label: "App-wide" },
  ].filter((s) => grouped[s.key]?.length);

  if (!kbs.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No knowledge bases yet. Create one to get started.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {sections.map(({ key, label }) => (
        <div key={key}>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            {label}
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {grouped[key].map((kb) => (
              <Card key={kb.id} className="relative">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-sm font-medium truncate">{kb.name}</CardTitle>
                      {kb.description && (
                        <CardDescription className="mt-0.5 text-xs line-clamp-2">
                          {kb.description}
                        </CardDescription>
                      )}
                    </div>
                    <Badge className={`shrink-0 text-[10px] px-1.5 py-0.5 ${scopeColors[kb.scope]}`}>
                      {kb.scope}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="flex items-center justify-between pt-0">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={kb.is_active}
                      onCheckedChange={(checked) => onToggle(kb.id, checked)}
                    />
                    <span className="text-xs text-muted-foreground">
                      {kb.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  {canDelete && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                      onClick={() => onDelete(kb.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
{% endraw %}
{%- endif %}
