{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
"use client";
{% raw %}
import { useEffect, useState } from "react";
import { use } from "react";
import { UserPlus, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { MembersTable, InviteMemberDialog } from "@/components/teams";
import { useMembers, useInvitations, useAuth } from "@/hooks";
import { useRouter } from "next/navigation";
import type { OrgRole } from "@/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function OrgMembersPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { user } = useAuth();
  const { members, total, isLoading, fetchMembers, changeRole, removeMember } = useMembers(id);
  const { invitations, fetchInvitations, revokeInvitation } = useInvitations(id);
  const [inviteOpen, setInviteOpen] = useState(false);

  useEffect(() => {
    fetchMembers();
    fetchInvitations();
  }, [fetchMembers, fetchInvitations]);

  const currentMember = members.find((m) => m.user_id === user?.id);
  const canManage = currentMember?.role === "owner" || currentMember?.role === "admin";
  const pendingInvitations = invitations.filter((i) => i.status === "pending");

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/orgs")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Members</h1>
          <p className="text-sm text-muted-foreground">{total} member{total !== 1 ? "s" : ""}</p>
        </div>
        {canManage && (
          <Button size="sm" onClick={() => setInviteOpen(true)}>
            <UserPlus className="mr-2 h-4 w-4" />
            Invite
          </Button>
        )}
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <MembersTable
              members={members}
              currentUserId={user?.id ?? ""}
              canManage={canManage}
              onRoleChange={(userId, role: OrgRole) => changeRole(userId, role)}
              onRemove={removeMember}
            />
          )}
        </CardContent>
      </Card>

      {pendingInvitations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Pending invitations</CardTitle>
            <CardDescription>Invites that haven&apos;t been accepted yet</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {pendingInvitations.map((inv) => (
              <div key={inv.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                <div>
                  <p className="text-sm font-medium">{inv.email}</p>
                  <Badge variant="outline" className="mt-0.5 text-[10px]">{inv.role}</Badge>
                </div>
                {canManage && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => revokeInvitation(inv.token)}
                  >
                    Revoke
                  </Button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <InviteMemberDialog open={inviteOpen} onOpenChange={setInviteOpen} orgId={id} />
    </div>
  );
}
{% endraw %}
{%- endif %}
