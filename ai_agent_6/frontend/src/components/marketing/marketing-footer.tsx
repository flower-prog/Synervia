import Link from "next/link";

interface FooterColumn {
  title: string;
  links: { label: string; href: string }[];
}

interface MarketingFooterProps {
  brand: string;
  tagline?: string;
  /** Status badge text (e.g. "All systems operational"). Translated by caller. */
  operationalLabel?: string;
  columns: FooterColumn[];
  legal?: { label: string; href: string }[];
}

export function MarketingFooter({
  brand,
  tagline,
  operationalLabel = "All systems operational",
  columns,
  legal = [],
}: MarketingFooterProps) {
  return (
    <footer className="theme-light bg-background text-foreground border-foreground/10 border-t">
      <div className="mx-auto w-full max-w-7xl px-6 py-16 md:px-10 md:py-24">
        <div className="grid gap-12 md:grid-cols-[1.5fr_2fr]">
          <div>
            <Link
              href="/"
              className="font-display text-foreground flex items-center gap-2 text-xl font-bold tracking-tight"
            >
              <span aria-hidden className="bg-brand inline-block h-3 w-3 rounded-full" />
              {brand}
            </Link>
            {tagline && (
              <p className="text-foreground/65 mt-4 max-w-sm text-sm leading-relaxed">{tagline}</p>
            )}
            <p className="text-foreground/45 mt-8 font-mono text-xs">
              <span className="bg-brand mr-2 inline-block h-1.5 w-1.5 animate-pulse rounded-full align-middle" />
              {operationalLabel}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-10 md:grid-cols-3">
            {columns.map((col) => (
              <div key={col.title}>
                <h3 className="eyebrow text-foreground/50 mb-4">{col.title}</h3>
                <ul className="space-y-3">
                  {col.links.map((l) => (
                    <li key={l.href}>
                      <Link
                        href={l.href}
                        className="text-foreground/75 hover:text-foreground text-sm transition-colors"
                      >
                        {l.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="border-foreground/10 mt-16 flex flex-wrap items-center justify-between gap-4 border-t pt-8">
          <p className="text-foreground/45 text-xs">
            © {new Date().getFullYear()} {brand}
          </p>
          {legal.length > 0 && (
            <ul className="flex flex-wrap gap-6">
              {legal.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    className="text-foreground/45 hover:text-foreground/75 text-xs transition-colors"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </footer>
  );
}
