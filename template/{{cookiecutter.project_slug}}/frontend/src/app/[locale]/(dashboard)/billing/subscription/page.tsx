{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"use client";
{% raw %}
import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { SubscriptionPanel } from "@/components/billing";
import { usePlans, useBilling } from "@/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function SubscriptionPage() {
  const searchParams = useSearchParams();
  const { plans, isLoading: plansLoading } = usePlans();
  const { startCheckout, isLoading: checkoutLoading } = useBilling();

  useEffect(() => {
    if (searchParams.get("success") === "1") {
      toast.success("Subscription updated successfully!");
    }
  }, [searchParams]);

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold">Subscription</h1>
        <p className="text-sm text-muted-foreground">Manage your plan and billing settings.</p>
      </div>

      <SubscriptionPanel />

      {!plansLoading && plans.length > 0 && (
        <div>
          <h2 className="mb-4 text-lg font-semibold">Available Plans</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {plans.map((plan) => (
              <Card key={plan.id} className="flex flex-col">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{plan.display_name}</CardTitle>
                    {plan.is_active && <Badge>Active</Badge>}
                  </div>
                  <CardDescription>{plan.description ?? ""}</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col justify-between gap-4">
                  <div className="space-y-1 text-sm text-muted-foreground">
                    {plan.prices
                      .filter((p) => p.is_active)
                      .map((price) => (
                        <div key={price.id}>
                          {(price.unit_amount / 100).toLocaleString("en-US", {
                            style: "currency",
                            currency: price.currency.toUpperCase(),
                          })}{" "}
                          / {price.interval}
                        </div>
                      ))}
                    {plan.monthly_credits_base > 0 && (
                      <div>{plan.monthly_credits_base.toLocaleString()} credits / month</div>
                    )}
                  </div>
                  <div className="space-y-2">
                    {plan.prices
                      .filter((p) => p.is_active)
                      .map((price) => (
                        <Button
                          key={price.id}
                          className="w-full"
                          variant="outline"
                          disabled={checkoutLoading}
                          onClick={() =>
                            startCheckout({
                              price_id: price.id,
                              success_url: window.location.href + "?success=1",
                              cancel_url: window.location.href,
                            })
                          }
                        >
                          Select {price.interval === "month" ? "Monthly" : "Annual"}
                        </Button>
                      ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
{% endraw %}
{%- else %}
export default function SubscriptionPage() {
  return null;
}
{%- endif %}
