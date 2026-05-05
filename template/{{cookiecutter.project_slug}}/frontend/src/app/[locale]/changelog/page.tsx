{%- if cookiecutter.enable_changelog %}
import { LandingNav } from "@/components/layout/landing-nav";
import { APP_NAME } from "@/lib/constants";

// Add your releases here — newest first
const releases = [
  {
    version: "1.0.0",
    date: "2025-01-01",
    title: "Initial Release",
    description: `${APP_NAME} is live. `,
    changes: [
      { type: "feat", text: "AI agent with streaming responses" },
      { type: "feat", text: "Multi-tenant organization management" },
      { type: "feat", text: "Billing and subscription management" },
    ],
  },
];

const typeColors: Record<string, string> = {
  feat: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  fix: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  improvement: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  chore: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300",
};

export default function ChangelogPage() {
  return (
    <>
      <LandingNav />
      <main className="mx-auto max-w-3xl px-4 py-16">
        <h1 className="mb-2 text-4xl font-bold">Changelog</h1>
        <p className="mb-12 text-lg text-muted-foreground">
          New updates and improvements to {APP_NAME}.
        </p>
        <div className="space-y-12">
          {releases.map((release) => (
            <article key={release.version} className="border-l-2 border-primary pl-6">
              <div className="mb-4 flex items-center gap-3">
                <span className="rounded-full bg-primary px-3 py-1 text-sm font-semibold text-primary-foreground">
                  v{release.version}
                </span>
                <time className="text-sm text-muted-foreground">{release.date}</time>
              </div>
              <h2 className="mb-2 text-xl font-semibold">{release.title}</h2>
              {release.description && (
                <p className="mb-4 text-muted-foreground">{release.description}</p>
              )}
              <ul className="space-y-2">
                {release.changes.map((change, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span
                      className={`mt-0.5 rounded px-1.5 py-0.5 text-xs font-medium ${
                        typeColors[change.type] ?? typeColors.chore
                      }`}
                    >
                      {change.type}
                    </span>
                    <span>{change.text}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </main>
    </>
  );
}
{%- else %}
export default function ChangelogPage() {
  return null;
}
{%- endif %}
