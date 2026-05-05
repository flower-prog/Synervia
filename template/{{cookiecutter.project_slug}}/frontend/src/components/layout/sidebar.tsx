"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import { LayoutDashboard, MessageSquare{%- if cookiecutter.enable_rag %}, Database{%- endif %}{%- if cookiecutter.use_jwt %}, UserCircle{%- endif %}{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}, Building2{%- endif %}{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}, CreditCard{%- endif %} } from "lucide-react";
import { useSidebarStore } from "@/stores";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetClose } from "@/components/ui";

const navigation = [
  { name: "Dashboard", href: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { name: "Chat", href: ROUTES.CHAT, icon: MessageSquare },
{%- if cookiecutter.enable_rag and not (cookiecutter.enable_teams and cookiecutter.use_jwt) %}
  { name: "Knowledge Base", href: ROUTES.RAG, icon: Database },
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
  { name: "Knowledge Bases", href: ROUTES.KB, icon: Database },
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
  { name: "Organizations", href: ROUTES.ORGS, icon: Building2 },
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
  { name: "Billing", href: ROUTES.BILLING, icon: CreditCard },
{%- endif %}
{%- if cookiecutter.use_jwt %}
  { name: "Profile", href: ROUTES.PROFILE, icon: UserCircle },
{%- endif %}
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex-1 space-y-1 p-4">
      {navigation.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.name}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors",
              "min-h-[44px]",
              isActive
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-secondary/50 hover:text-secondary-foreground"
            )}
          >
            <item.icon className="h-5 w-5" />
            {item.name}
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center border-b px-4">
        <Link
          href={ROUTES.HOME}
          className="flex items-center gap-2 font-semibold"
          onClick={onNavigate}
        >
          <span>{"{{ cookiecutter.project_name }}"}</span>
        </Link>
      </div>
      <NavLinks onNavigate={onNavigate} />
    </div>
  );
}

export function Sidebar() {
  const { isOpen, close } = useSidebarStore();

  return (
    <Sheet open={isOpen} onOpenChange={close}>
      <SheetContent side="left" className="w-72 p-0">
        <SheetHeader className="h-14 px-4">
          <SheetTitle>{"{{ cookiecutter.project_name }}"}</SheetTitle>
          <SheetClose onClick={close} />
        </SheetHeader>
        <NavLinks onNavigate={close} />
      </SheetContent>
    </Sheet>
  );
}
