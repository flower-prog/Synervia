"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from "@/components/ui";
import type { ToolCall } from "@/types";
import {
  Wrench,
  CheckCircle,
  Loader2,
  AlertCircle,
  Clock,
  Calendar,
  FileText,
  Search,
  Globe,
  Link,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CopyButton } from "./copy-button";

interface ToolCallCardProps {
  toolCall: ToolCall;
}

// --- Specialized renderers ---

function DateTimeResult({ result }: { result: string }) {
  // Parse "Current date: YYYY-MM-DD, Current time: HH:MM:SS"
  const dateMatch = result.match(/Current date:\s*(\d{4}-\d{2}-\d{2})/);
  const timeMatch = result.match(/Current time:\s*(\d{2}:\d{2}:\d{2})/);

  return (
    <div className="flex items-center gap-4 py-2">
      {dateMatch && (
        <div className="flex items-center gap-2">
          <Calendar className="text-primary h-5 w-5" />
          <div>
            <p className="text-muted-foreground text-xs">Date</p>
            <p className="text-sm font-semibold">{dateMatch[1]}</p>
          </div>
        </div>
      )}
      {timeMatch && (
        <div className="flex items-center gap-2">
          <Clock className="text-primary h-5 w-5" />
          <div>
            <p className="text-muted-foreground text-xs">Time</p>
            <p className="text-sm font-semibold">{timeMatch[1]}</p>
          </div>
        </div>
      )}
      {!dateMatch && !timeMatch && <p className="text-sm">{result}</p>}
    </div>
  );
}

interface RAGResultItem {
  index: number;
  source: string;
  page?: string;
  chunk?: string;
  collection?: string;
  score: string;
  content: string;
}

function parseRAGResults(result: string): RAGResultItem[] {
  const items: RAGResultItem[] = [];
  // Match: [1] Source: filename, page X, chunk Y [collection] (score: 0.xxx)\ncontent
  const pattern =
    /\[(\d+)\]\s*Source:\s*([^,\n]+?)(?:,\s*page\s*(\d+))?(?:,\s*chunk\s*(\d+))?(?:\s*\[([^\]]+)\])?\s*\(score:\s*([\d.]+)\)\n([\s\S]*?)(?=\n\[\d+\]|$)/g;
  let match;
  while ((match = pattern.exec(result)) !== null) {
    items.push({
      index: parseInt(match[1] ?? "0"),
      source: (match[2] ?? "").trim(),
      page: match[3],
      chunk: match[4],
      collection: match[5],
      score: match[6] ?? "",
      content: (match[7] ?? "").trim(),
    });
  }
  return items;
}

function RAGSearchResults({ result }: { result: string }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const items = parseRAGResults(result);

  if (items.length === 0) {
    if (result.includes("No relevant documents")) {
      return (
        <div className="text-muted-foreground flex items-center gap-2 py-2 text-sm">
          <Search className="h-4 w-4" />
          No relevant documents found
        </div>
      );
    }
    return null; // fallback to default renderer
  }

  // Group chunks by source filename so the same file doesn't render as N
  // duplicate cards. Preserve insertion order so the indices stay readable.
  const grouped = items.reduce<Map<string, RAGResultItem[]>>((acc, item) => {
    const key = item.source || "Unknown";
    const list = acc.get(key) ?? [];
    list.push(item);
    acc.set(key, list);
    return acc;
  }, new Map());
  const sourceCount = grouped.size;

  return (
    <div className="space-y-3 py-1">
      <div className="text-foreground/55 flex items-center gap-2 font-mono text-[10px] tracking-wider uppercase">
        <Search className="h-3 w-3" />
        <span>
          {items.length} chunk{items.length !== 1 ? "s" : ""}
        </span>
        <span>·</span>
        <span>
          {sourceCount} source{sourceCount !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="border-foreground/10 divide-foreground/8 divide-y overflow-hidden rounded-xl border">
        {Array.from(grouped.entries()).map(([source, chunks]) => (
          <RAGSourceGroup
            key={source}
            source={source}
            chunks={chunks}
            expandedIdx={expandedIdx}
            onToggle={(idx) => setExpandedIdx(expandedIdx === idx ? null : idx)}
          />
        ))}
      </div>
    </div>
  );
}

function RAGSourceGroup({
  source,
  chunks,
  expandedIdx,
  onToggle,
}: {
  source: string;
  chunks: RAGResultItem[];
  expandedIdx: number | null;
  onToggle: (idx: number) => void;
}) {
  const collection = chunks[0]?.collection;
  const bestScore = Math.max(...chunks.map((c) => parseFloat(c.score) || 0));
  return (
    <div>
      {/* Source header */}
      <div className="bg-foreground/[0.02] flex items-center gap-2 px-3 py-2">
        <FileText className="text-foreground/55 h-3.5 w-3.5 shrink-0" />
        <span className="text-foreground truncate text-xs font-medium" title={source}>
          {source}
        </span>
        <span className="text-foreground/45 ml-auto font-mono text-[10px] tracking-wider uppercase">
          {chunks.length} chunk{chunks.length !== 1 ? "s" : ""}
        </span>
        <ScoreDot score={bestScore} />
        {collection && (
          <span
            className="border-foreground/15 text-foreground/55 hidden shrink-0 rounded-full border px-1.5 py-0.5 font-mono text-[9px] tracking-wider uppercase sm:inline"
            title={`Collection: ${collection}`}
          >
            {collection}
          </span>
        )}
      </div>
      {/* Chunks */}
      <ul>
        {chunks.map((chunk) => {
          const isOpen = expandedIdx === chunk.index;
          return (
            <li key={chunk.index} className="border-foreground/8 border-t first:border-t-0">
              <button
                type="button"
                onClick={() => onToggle(chunk.index)}
                className="hover:bg-foreground/[0.02] flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors"
              >
                <span className="bg-foreground/8 text-foreground/65 mt-0.5 inline-flex h-5 min-w-[1.5rem] shrink-0 items-center justify-center rounded px-1 font-mono text-[10px] tabular-nums">
                  {chunk.index}
                </span>
                <div className="min-w-0 flex-1">
                  <p
                    className={cn(
                      "text-foreground/80 text-xs leading-relaxed",
                      !isOpen && "line-clamp-2",
                    )}
                  >
                    {chunk.content}
                  </p>
                  {(chunk.page || chunk.chunk) && (
                    <div className="text-foreground/45 mt-1 flex items-center gap-1.5 font-mono text-[10px] tracking-wider uppercase">
                      {chunk.page && <span>p.{chunk.page}</span>}
                      {chunk.chunk && (
                        <>
                          {chunk.page && <span>·</span>}
                          <span>chunk {chunk.chunk}</span>
                        </>
                      )}
                    </div>
                  )}
                </div>
                <div className="mt-0.5 flex shrink-0 items-center gap-1.5">
                  <span className="text-foreground/55 font-mono text-[10px] tabular-nums">
                    {parseFloat(chunk.score).toFixed(2)}
                  </span>
                  <ScoreDot score={parseFloat(chunk.score) || 0} />
                  <ChevronDown
                    className={cn(
                      "text-foreground/40 h-3.5 w-3.5 transition-transform",
                      isOpen && "rotate-180",
                    )}
                  />
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Tiny dot indicating chunk relevance — neutral palette, no warning colors. */
function ScoreDot({ score }: { score: number }) {
  // Map score to brand-tone opacity instead of red/yellow/green so the UI
  // reads as a quality signal, not an alert.
  const tone =
    score >= 0.7 ? "bg-foreground" : score >= 0.4 ? "bg-foreground/55" : "bg-foreground/25";
  return (
    <span
      className={cn("h-1.5 w-1.5 shrink-0 rounded-full", tone)}
      title={`Relevance: ${score.toFixed(2)}`}
    />
  );
}

interface WebResultItem {
  index: number;
  title: string;
  url: string;
  content: string;
}

function parseWebResults(result: string): WebResultItem[] {
  const items: WebResultItem[] = [];
  const pattern = /\[(\d+)\]\s*(.+?)\n\s*URL:\s*(\S+)\n\s*([\s\S]*?)(?=\n\[\d+\]|$)/g;
  let match;
  while ((match = pattern.exec(result)) !== null) {
    items.push({
      index: parseInt(match[1] ?? "0"),
      title: (match[2] ?? "").trim(),
      url: (match[3] ?? "").trim(),
      content: (match[4] ?? "").trim(),
    });
  }
  return items;
}

function WebSearchResults({ result }: { result: string }) {
  const items = parseWebResults(result);

  if (items.length === 0) {
    if (result.includes("No web results")) {
      return (
        <div className="text-muted-foreground flex items-center gap-2 py-2 text-sm">
          <Globe className="h-4 w-4" />
          No web results found
        </div>
      );
    }
    return null;
  }

  return (
    <div className="space-y-2 py-1">
      <div className="text-muted-foreground flex items-center gap-2 text-xs">
        <Globe className="h-3.5 w-3.5" />
        {items.length} web result{items.length !== 1 ? "s" : ""}
      </div>
      {items.map((item) => (
        <div key={item.index} className="bg-background rounded-md border p-2.5">
          <div className="flex items-start gap-2">
            <Badge variant="secondary" className="mt-0.5 shrink-0 px-1 py-0 text-[10px]">
              [{item.index}]
            </Badge>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium">{item.title}</p>
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary flex items-center gap-1 truncate text-[10px] hover:underline"
              >
                <Link className="h-2.5 w-2.5 shrink-0" />
                {item.url}
              </a>
              <p className="text-muted-foreground mt-1 line-clamp-2 text-xs">{item.content}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// --- Helpers ---

/** Pretty-print tool args. Handles three shapes:
 *  - object → JSON.stringify with indent
 *  - JSON-string (e.g. raw streaming payload) → parse then pretty-print
 *  - plain non-JSON string → return as-is
 */
function formatArgs(args: unknown): string {
  if (args === null || args === undefined) return "";
  if (typeof args === "string") {
    try {
      const parsed = JSON.parse(args);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return args;
    }
  }
  return JSON.stringify(args, null, 2);
}

function isEmptyArgs(args: unknown): boolean {
  if (args === null || args === undefined) return true;
  if (typeof args === "string") return args.trim() === "" || args.trim() === "{}";
  if (typeof args === "object") return Object.keys(args).length === 0;
  return false;
}

// --- Main component ---

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [showRaw, setShowRaw] = useState(false);

  const statusConfig = {
    pending: { icon: Loader2, color: "text-muted-foreground", animate: true },
    running: { icon: Loader2, color: "text-blue-500", animate: true },
    completed: { icon: CheckCircle, color: "text-green-500", animate: false },
    error: { icon: AlertCircle, color: "text-red-500", animate: false },
  };

  const {
    icon: StatusIcon,
    color,
    animate,
  } = statusConfig[toolCall.status] || statusConfig.pending;

  const resultText =
    toolCall.result !== undefined
      ? typeof toolCall.result === "string"
        ? toolCall.result
        : JSON.stringify(toolCall.result, null, 2)
      : "";

  // Check if we have a specialized renderer
  const isDateTime = toolCall.name === "get_current_datetime" && toolCall.status === "completed";
  const isRAGSearch =
    (toolCall.name === "search_knowledge_base" || toolCall.name === "search_documents") &&
    toolCall.status === "completed" &&
    typeof toolCall.result === "string";
  const isWebSearch =
    (toolCall.name === "web_search" || toolCall.name === "search_web") &&
    toolCall.status === "completed" &&
    typeof toolCall.result === "string";

  const hasSpecialRenderer = isDateTime || isRAGSearch || isWebSearch;

  return (
    <Card className="bg-muted/50">
      <CardHeader className="px-3 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isDateTime ? (
              <Clock className="text-primary h-4 w-4" />
            ) : isRAGSearch ? (
              <Search className="text-primary h-4 w-4" />
            ) : isWebSearch ? (
              <Globe className="text-primary h-4 w-4" />
            ) : (
              <Wrench className="text-muted-foreground h-4 w-4" />
            )}
            <CardTitle className="text-sm font-medium">
              {isDateTime
                ? "Current Date & Time"
                : isRAGSearch
                  ? "Knowledge Base Search"
                  : isWebSearch
                    ? "Web Search"
                    : toolCall.name}
            </CardTitle>
            {(isRAGSearch || isWebSearch) && toolCall.args?.query ? (
              <span className="text-muted-foreground max-w-[200px] truncate text-xs italic">
                &ldquo;{String(toolCall.args.query)}&rdquo;
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-1">
            {hasSpecialRenderer && toolCall.status === "completed" && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setShowRaw(!showRaw)}
                title={showRaw ? "Show formatted" : "Show raw"}
              >
                {showRaw ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </Button>
            )}
            <StatusIcon className={cn("h-4 w-4", color, animate && "animate-spin")} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-3 py-2">
        {/* Specialized rendering */}
        {toolCall.status === "completed" && !showRaw && isDateTime && (
          <DateTimeResult result={resultText} />
        )}
        {toolCall.status === "completed" && !showRaw && isRAGSearch && (
          <RAGSearchResults result={resultText} />
        )}
        {toolCall.status === "completed" && !showRaw && isWebSearch && (
          <WebSearchResults result={resultText} />
        )}

        {/* Raw/default rendering */}
        {(!hasSpecialRenderer || showRaw || toolCall.status !== "completed") && (
          <div className="space-y-3">
            {/* Arguments */}
            {isEmptyArgs(toolCall.args) ? (
              <p className="text-muted-foreground text-xs italic">No arguments</p>
            ) : (
              <div className="group relative">
                <div className="mb-1 flex items-center justify-between">
                  <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
                    Arguments
                  </p>
                  <CopyButton
                    text={formatArgs(toolCall.args)}
                    className="opacity-0 group-hover:opacity-100"
                  />
                </div>
                <pre className="border-foreground/10 bg-background/60 scrollbar-thin overflow-x-auto rounded-lg border p-2.5 font-mono text-[11px] leading-relaxed">
                  {formatArgs(toolCall.args)}
                </pre>
              </div>
            )}

            {/* Result */}
            {toolCall.result !== undefined && resultText !== "" && (
              <div className="group relative">
                <div className="mb-1 flex items-center justify-between">
                  <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
                    Result
                  </p>
                  <CopyButton text={resultText} className="opacity-0 group-hover:opacity-100" />
                </div>
                <pre className="border-foreground/10 bg-background/60 max-h-48 scrollbar-thin overflow-x-auto overflow-y-auto rounded-lg border p-2.5 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap">
                  {resultText}
                </pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
