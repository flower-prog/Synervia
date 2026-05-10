import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, Mail } from "lucide-react";

import type { Locale } from "@/i18n";
import { ROUTES } from "@/lib/constants";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Check your email",
    description: "We sent you a sign-in link.",
    path: "/magic-link-sent",
    locale,
    noindex: true,
  });
}

interface PageProps {
  searchParams: Promise<{ email?: string }>;
}

export default async function MagicLinkSentPage({ searchParams }: PageProps) {
  const { email } = await searchParams;

  return (
    <div className="space-y-7 text-center">
      <div className="bg-brand/15 mx-auto flex h-14 w-14 items-center justify-center rounded-full">
        <Mail className="text-foreground h-6 w-6" />
      </div>

      <div className="space-y-2">
        <span className="eyebrow text-foreground/55">Magic link</span>
        <h1 className="text-display-md text-foreground">Check your email</h1>
        <p className="text-foreground/70 text-sm">
          We sent a sign-in link
          {email ? (
            <>
              {" "}
              to <span className="text-foreground font-medium">{email}</span>
            </>
          ) : null}
          . Click the link in the email to continue. The link expires in 15 minutes.
        </p>
      </div>

      <div className="border-foreground/10 bg-foreground/[0.03] rounded-2xl border px-5 py-4 text-left">
        <p className="text-foreground/70 text-xs leading-relaxed">
          Don&apos;t see it? Check your spam folder, or{" "}
          <Link
            href={ROUTES.LOGIN}
            className="text-foreground hover:text-foreground/80 font-medium underline-offset-4 hover:underline"
          >
            try again
          </Link>
          .
        </p>
      </div>

      <Link
        href={ROUTES.LOGIN}
        className="text-foreground/55 hover:text-foreground inline-flex items-center gap-2 text-sm font-medium"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to sign in
      </Link>
    </div>
  );
}
