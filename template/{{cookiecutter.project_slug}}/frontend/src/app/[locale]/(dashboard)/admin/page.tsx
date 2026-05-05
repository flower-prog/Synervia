{%- if cookiecutter.use_jwt %}
"use client";
{% raw %}
import Link from "next/link";
import { MessageSquare, Star, Users } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const sections = [
  {
    title: "Users",
    description: "Manage accounts, roles, and impersonation.",
    icon: Users,
    href: "/admin/users",
  },
  {
    title: "Conversations",
    description: "Browse all user conversations and messages.",
    icon: MessageSquare,
    href: "/admin/conversations",
  },
  {
    title: "Ratings",
    description: "View message quality ratings and feedback.",
    icon: Star,
    href: "/admin/ratings",
  },
];

export default function AdminPage() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Admin Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Manage users, conversations, and application settings.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sections.map(({ title, description, icon: Icon, href }) => (
          <Card key={href} className="flex flex-col">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Icon className="h-5 w-5 text-muted-foreground" />
                {title}
              </CardTitle>
              <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 flex items-end">
              <Button asChild variant="outline" className="w-full">
                <Link href={href}>Open</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
{% endraw %}
{%- else %}
export default function AdminPage() {
  return null;
}
{%- endif %}
