"use client";

import { ArrowUpRight, BookOpen, Code2, FileSearch, Sparkles } from "lucide-react";

const PROMPTS = [
  {
    icon: FileSearch,
    title: "Summarize my docs",
    prompt: "Summarize the key points from my latest indexed documents.",
  },
  {
    icon: BookOpen,
    title: "Explain a concept",
    prompt: "Explain how vector search and RAG work together — keep it under 200 words.",
  },
  {
    icon: Code2,
    title: "Write some code",
    prompt: "Write a Python function that hashes a password with bcrypt and verifies it.",
  },
  {
    icon: Sparkles,
    title: "Brainstorm",
    prompt: "Give me 5 ideas for an onboarding email sequence for a developer tool.",
  },
];

interface ChatEmptyStateProps {
  onPick: (prompt: string) => void;
  agentLabel?: string;
}

export function ChatEmptyState({ onPick, agentLabel = "pydantic_ai" }: ChatEmptyStateProps) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col items-center justify-center px-4 py-10 text-center md:py-16">
      <span className="eyebrow-badge mb-6">Powered by {agentLabel}</span>
      <h2 className="font-display text-foreground text-3xl font-bold tracking-tight md:text-4xl">
        How can I help today?
      </h2>
      <p className="text-foreground/65 mt-3 max-w-md text-sm md:text-base">
        Try one of these to see streaming, tool calls, and citations in action.
      </p>

      <div className="mt-8 grid w-full gap-2.5 sm:grid-cols-2">
        {PROMPTS.map((p) => (
          <button
            key={p.title}
            type="button"
            onClick={() => onPick(p.prompt)}
            className="lift group border-foreground/10 hover:border-foreground/30 bg-card flex items-start gap-3 rounded-2xl border p-4 text-left transition-colors"
          >
            <span className="bg-brand/15 text-foreground flex h-9 w-9 shrink-0 items-center justify-center rounded-full">
              <p.icon className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-foreground text-sm font-semibold">{p.title}</p>
              <p className="text-foreground/55 mt-0.5 line-clamp-2 text-xs">{p.prompt}</p>
            </div>
            <ArrowUpRight className="text-foreground/30 group-hover:text-foreground mt-1 h-4 w-4 shrink-0 transition-colors" />
          </button>
        ))}
      </div>

      <div className="text-foreground/45 mt-8 inline-flex items-center gap-2 font-mono text-[11px] tracking-wider uppercase">
        <span>Tip:</span>
        <kbd className="border-foreground/15 bg-card text-foreground/65 rounded-md border px-1.5 py-0.5 text-[10px]">
          ⌘K
        </kbd>
        <span>for command palette</span>
      </div>
    </div>
  );
}
