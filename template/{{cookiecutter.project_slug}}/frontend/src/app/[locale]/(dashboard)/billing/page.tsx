{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"use client";
{% raw %}
import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { BillingCard } from "@/components/billing";
import { useOrganizations, useMembers } from "@/hooks";
import { Skeleton } from "@/components/ui/skeleton";

export default function BillingPage() {
  const { activeOrg, fetchOrgs } = useOrganizations();
  const { members, total, fetchMembers } = useMembers(activeOrg?.id ?? "");
  const searchParams = useSearchParams();

  useEffect(() => {
    fetchOrgs();
  }, [fetchOrgs]);

  useEffect(() => {
    if (activeOrg?.id) fetchMembers();
  }, [activeOrg?.id, fetchMembers]);

  useEffect(() => {
    if (searchParams.get("success") === "1") {
      toast.success("Subscription updated successfully!");
    }
  }, [searchParams]);

  if (!activeOrg) {
    return (
      <div className="mx-auto max-w-xl space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Billing</h1>
        <p className="text-sm text-muted-foreground">
          Manage your subscription for <strong>{activeOrg.name}</strong>.
        </p>
      </div>
      <BillingCard org={activeOrg} memberCount={total} />
    </div>
  );
}
{% endraw %}
{%- endif %}
