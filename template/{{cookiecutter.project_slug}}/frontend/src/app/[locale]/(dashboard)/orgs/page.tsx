{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
"use client";
{% raw %}
import { useEffect, useState } from "react";
import { Plus, Building2, Settings, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CreateOrgDialog } from "@/components/teams";
import { useOrganizations } from "@/hooks";
import { useRouter, useSearchParams } from "next/navigation";

export default function OrgsPage() {
  const { orgs, fetchOrgs, switchOrg } = useOrganizations();
  const [createOpen, setCreateOpen] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    fetchOrgs();
    if (searchParams.get("create") === "1") setCreateOpen(true);
  }, [fetchOrgs, searchParams]);

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Organizations</h1>
          <p className="text-sm text-muted-foreground">
            Manage your organizations and switch between them.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New organization
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {orgs.map((org) => (
          <Card key={org.id} className="relative cursor-pointer hover:bg-muted/30 transition-colors">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  {org.name}
                </CardTitle>
                {org.is_personal && <Badge variant="secondary" className="text-[10px]">Personal</Badge>}
              </div>
            </CardHeader>
            <CardContent className="flex items-center justify-between pt-0">
              <p className="text-xs text-muted-foreground capitalize">{org.subscription_tier}</p>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 px-2 text-xs"
                  onClick={() => { switchOrg(org.id); router.push("/dashboard"); }}
                >
                  <Users className="h-3.5 w-3.5" />
                  Switch
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 px-2 text-xs"
                  onClick={() => router.push(`/orgs/${org.id}/members`)}
                >
                  <Settings className="h-3.5 w-3.5" />
                  Manage
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {orgs.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed py-12 text-center">
          <Building2 className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">No organizations yet</p>
          <Button variant="outline" size="sm" onClick={() => setCreateOpen(true)}>
            Create your first organization
          </Button>
        </div>
      )}

      <CreateOrgDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => fetchOrgs()}
      />
    </div>
  );
}
{% endraw %}
{%- endif %}
