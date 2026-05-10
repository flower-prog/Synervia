import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";

interface FinalCtaProps {
  /** Headline supports `<em>` for italic accent. */
  title: ReactNode;
  description?: string;
  primary: { label: string; href: string };
  secondary?: { label: string; href: string };
}

export function FinalCta({ title, description, primary, secondary }: FinalCtaProps) {
  return (
    <div className="border-foreground/15 bg-brand text-brand-foreground relative overflow-hidden rounded-3xl border px-8 py-20 text-center md:px-16 md:py-28">
      <h2 className="text-display-xl [&_em]:font-accent mx-auto max-w-3xl [&_em]:font-normal [&_em]:italic">
        {title}
      </h2>
      {description && (
        <p className="text-brand-foreground/75 mx-auto mt-6 max-w-xl text-lg">{description}</p>
      )}
      <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
        <Link
          href={primary.href}
          className="bg-brand-foreground text-brand hover:bg-brand-foreground/90 group inline-flex items-center gap-3 rounded-full py-2 pr-2 pl-6 text-base font-medium transition-colors"
        >
          <span>{primary.label}</span>
          <span className="bg-brand text-brand-foreground flex h-9 w-9 items-center justify-center rounded-full transition-transform group-hover:rotate-45">
            <ArrowUpRight className="h-4 w-4" />
          </span>
        </Link>
        {secondary && (
          <Link
            href={secondary.href}
            className="border-brand-foreground/30 text-brand-foreground hover:bg-brand-foreground/10 inline-flex items-center gap-2 rounded-full border px-5 py-2 text-base font-medium transition-colors"
          >
            {secondary.label}
          </Link>
        )}
      </div>
    </div>
  );
}
