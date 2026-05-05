{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system and cookiecutter.enable_teams %}
"use client";
{% raw %}
import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { CreditsPanel } from "@/components/billing";

export default function CreditsPage() {
  const searchParams = useSearchParams();

  useEffect(() => {
    if (searchParams.get("topup") === "1") {
      toast.success("Credits added to your account!");
    }
  }, [searchParams]);

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Credits</h1>
        <p className="text-sm text-muted-foreground">
          View your credit balance and transaction history.
        </p>
      </div>
      <CreditsPanel />
    </div>
  );
}
{% endraw %}
{%- else %}
export default function CreditsPage() {
  return null;
}
{%- endif %}
