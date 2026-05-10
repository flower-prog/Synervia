import Link from "next/link";

import { APP_NAME, ROUTES } from "@/lib/constants";

const HIGHLIGHTS = [
  "Streaming chat with tool calls",
  "Knowledge base over your docs",
  "Stripe billing & teams in a click",
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-background text-foreground min-h-screen lg:grid lg:grid-cols-[1.05fr_1fr]">
      {/* Left — brand panel (dark, hidden on mobile) */}
      <aside className="theme-dark bg-background text-foreground relative hidden flex-col justify-between overflow-hidden p-10 lg:flex lg:p-12">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="bg-grid absolute inset-0 opacity-[0.6]" />
          <div className="bg-brand/[0.18] absolute -top-32 -left-20 h-[420px] w-[420px] rounded-full blur-[120px]" />
          <div className="bg-brand/[0.10] absolute right-0 bottom-10 h-[320px] w-[420px] rounded-full blur-[140px]" />
        </div>

        <div className="relative z-10">
          <Link
            href={ROUTES.HOME}
            className="font-display text-foreground inline-flex items-center gap-2 text-lg font-bold tracking-tight"
          >
            <span aria-hidden className="bg-brand inline-block h-3 w-3 rounded-full" />
            {APP_NAME}
          </Link>
        </div>

        <div className="relative z-10 max-w-[28rem]">
          <span className="eyebrow-badge mb-8">An AI assistant that knows your work</span>
          <h2 className="text-display-lg text-foreground mb-6 leading-[1.05]">
            Ship the AI feature <span className="font-accent text-foreground/95">your team</span>{" "}
            actually wants.
          </h2>
          <p className="text-foreground/65 max-w-md text-base leading-relaxed">
            Auth, billing, vector search, agents — already wired. You ship the product, not the
            plumbing.
          </p>

          <ul className="mt-10 space-y-3">
            {HIGHLIGHTS.map((line) => (
              <li key={line} className="text-foreground/85 flex items-center gap-3 text-sm">
                <span aria-hidden className="bg-brand h-1.5 w-1.5 shrink-0 rounded-full" />
                {line}
              </li>
            ))}
          </ul>
        </div>

        <figure className="relative z-10 max-w-md">
          <blockquote className="font-display text-foreground/85 text-lg leading-snug">
            &ldquo;Replaced four SaaS tools and shipped our first AI feature in two weeks.&rdquo;
          </blockquote>
          <figcaption className="mt-4 flex items-center gap-3">
            <span className="bg-brand text-brand-foreground flex h-9 w-9 items-center justify-center rounded-full font-mono text-xs font-semibold">
              MC
            </span>
            <div>
              <p className="text-foreground text-sm font-semibold">Maya Chen</p>
              <p className="text-foreground/55 text-xs">CTO · Lumen Labs</p>
            </div>
          </figcaption>
        </figure>
      </aside>

      {/* Right — form panel (always light, regardless of system theme) */}
      <main id="main" className="theme-light bg-background text-foreground relative flex flex-col">
        <header className="flex h-16 items-center px-6 sm:px-10">
          <Link
            href={ROUTES.HOME}
            className="font-display text-foreground inline-flex items-center gap-2 text-base font-bold tracking-tight lg:hidden"
          >
            <span aria-hidden className="bg-brand inline-block h-2.5 w-2.5 rounded-full" />
            {APP_NAME}
          </Link>
        </header>

        <div className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10">
          <div className="w-full max-w-md">{children}</div>
        </div>

        <footer className="text-foreground/50 px-6 py-6 font-mono text-[11px] tracking-wider uppercase sm:px-10">
          © {new Date().getFullYear()} {APP_NAME}
        </footer>
      </main>
    </div>
  );
}
