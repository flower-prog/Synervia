"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileText,
  Loader2,
  Plug,
  Plus,
  RefreshCw,
  RotateCw,
  Trash2,
  Upload,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingState } from "@/components/states";
import { SyncSourceWizard } from "@/components/rag/sync-source-wizard";
import { useKBDetail } from "@/hooks";
import { cn } from "@/lib/utils";
import type { SyncSourceRead } from "@/lib/rag-api";
import type { KBDocument } from "@/types";

interface KBDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function KBDetailPage({ params }: KBDetailPageProps) {
  const { id } = use(params);
  const {
    kb,
    documents,
    syncSources,
    connectors,
    isLoading,
    isUploading,
    error,
    refresh,
    uploadDocument,
    deleteDocument,
    createSyncSource,
    triggerSyncSource,
    deleteSyncSource,
  } = useKBDetail(id);

  const [isDragging, setIsDragging] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [creatingSource, setCreatingSource] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Light polling while any document is still ingesting — the worker writes
  // status async, so we re-fetch every 4s until everything settled.
  useEffect(() => {
    const pending = documents.some((d) => d.status === "pending" || d.status === "processing");
    if (!pending) return;
    const interval = setInterval(() => refresh(), 4000);
    return () => clearInterval(interval);
  }, [documents, refresh]);

  const handleFiles = async (files: FileList | null) => {
    if (!files) return;
    for (const file of Array.from(files)) {
      try {
        await uploadDocument(file);
      } catch {
        // toast handled in the hook
      }
    }
  };

  if (isLoading && !kb) return <LoadingState />;

  if (error && !kb) {
    return (
      <div className="text-destructive flex h-64 items-center justify-center text-sm">{error}</div>
    );
  }

  if (!kb) return null;

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      {/* Breadcrumb */}
      <nav className="text-foreground/55 flex items-center gap-1 text-xs">
        <Link
          href="/kb"
          className="hover:text-foreground inline-flex items-center gap-1 transition-colors"
        >
          <ArrowLeft className="h-3 w-3" />
          Knowledge bases
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-foreground/80 truncate">{kb.name}</span>
      </nav>

      {/* Header */}
      <header className="space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
              {kb.scope === "personal"
                ? "Personal"
                : kb.scope === "org"
                  ? "Organization"
                  : "App-wide"}
              {kb.is_default && " · Default"}
            </p>
            <h1 className="font-display text-foreground mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
              {kb.name}
            </h1>
            {kb.description && (
              <p className="text-foreground/65 mt-1 max-w-2xl text-sm">{kb.description}</p>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={() => refresh()} className="gap-1.5">
            <RefreshCw className={cn("h-3.5 w-3.5", isLoading && "animate-spin")} />
            Refresh
          </Button>
        </div>
        <div className="text-foreground/45 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-wider uppercase">
          <span>collection · {kb.collection_name}</span>
          <span>·</span>
          <span>
            {documents.length} document{documents.length === 1 ? "" : "s"}
          </span>
        </div>
      </header>

      {/* Upload dropzone */}
      <section
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "relative rounded-2xl border-2 border-dashed p-8 text-center transition-colors",
          isDragging
            ? "border-brand bg-brand/5"
            : "border-foreground/15 hover:border-foreground/30 bg-card/40",
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={isUploading}
        />
        <div className="flex flex-col items-center gap-2">
          <div className="bg-foreground/8 text-foreground/65 flex h-12 w-12 items-center justify-center rounded-2xl">
            {isUploading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Upload className="h-5 w-5" />
            )}
          </div>
          <p className="text-foreground text-sm font-medium">
            {isUploading ? "Uploading…" : "Drop files here or click to browse"}
          </p>
          <p className="text-foreground/55 text-xs">PDFs, Office docs, Markdown, text, and more</p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="mt-2"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            Choose files
          </Button>
        </div>
      </section>

      {/* Sync sources */}
      <section className="space-y-3">
        <div className="flex items-baseline justify-between gap-3">
          <div>
            <h2 className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
              Sync sources
            </h2>
            <p className="text-foreground/45 mt-0.5 text-xs">
              Auto-pull documents from Google Drive, S3, and other connectors.
            </p>
          </div>
          {connectors.length > 0 && (
            <Button size="sm" variant="outline" onClick={() => setWizardOpen(true)}>
              <Plus className="mr-1 h-3.5 w-3.5" />
              Connect source
            </Button>
          )}
        </div>
        {syncSources.length === 0 ? (
          <div className="border-foreground/10 bg-card/30 rounded-xl border border-dashed p-6 text-center">
            <Plug className="text-foreground/30 mx-auto h-5 w-5" />
            <p className="text-foreground/55 mt-2 text-xs">
              {connectors.length === 0
                ? "No connectors are configured on this workspace yet."
                : "No sources connected. Add one to keep this knowledge base in sync automatically."}
            </p>
          </div>
        ) : (
          <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-xl border">
            {syncSources.map((source) => (
              <SyncSourceRow
                key={source.id}
                source={source}
                onTrigger={() => triggerSyncSource(source.id)}
                onDelete={() => deleteSyncSource(source.id)}
              />
            ))}
          </ul>
        )}
      </section>

      {/* Document list */}
      <section className="space-y-3">
        <h2 className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          Documents
        </h2>
        {documents.length === 0 ? (
          <div className="border-foreground/10 bg-card/30 rounded-xl border p-8 text-center">
            <FileText className="text-foreground/30 mx-auto h-6 w-6" />
            <p className="text-foreground/55 mt-2 text-sm">
              No documents yet. Upload some above to populate this knowledge base.
            </p>
          </div>
        ) : (
          <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-xl border">
            {documents.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} onDelete={() => deleteDocument(doc.id)} />
            ))}
          </ul>
        )}
      </section>

      {/* Reuse the rich /rag wizard — defaultCollection is pinned to this KB
          so the user only picks the connector and fills in its config. */}
      <SyncSourceWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        connectors={connectors}
        collections={[{ name: kb.collection_name }]}
        defaultCollection={kb.collection_name}
        submitting={creatingSource}
        onSubmit={async (data) => {
          setCreatingSource(true);
          try {
            await createSyncSource(data);
            setWizardOpen(false);
          } catch {
            // toast handled in the hook
          } finally {
            setCreatingSource(false);
          }
        }}
      />
    </div>
  );
}

function SyncSourceRow({
  source,
  onTrigger,
  onDelete,
}: {
  source: SyncSourceRead;
  onTrigger: () => void;
  onDelete: () => void;
}) {
  const lastSync = source.last_sync_at ? new Date(source.last_sync_at).toLocaleString() : "Never";
  const statusColor =
    source.last_sync_status === "completed"
      ? "text-green-700 bg-green-100 dark:bg-green-900/30 dark:text-green-300"
      : source.last_sync_status === "failed"
        ? "text-red-700 bg-red-100 dark:bg-red-900/30 dark:text-red-300"
        : source.last_sync_status === "running"
          ? "text-blue-700 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300"
          : "text-foreground/65 bg-foreground/8";
  return (
    <li className="hover:bg-foreground/[0.02] flex items-center gap-3 px-4 py-3 transition-colors">
      <div className="bg-foreground/8 text-foreground/65 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
        <Plug className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-foreground truncate text-sm font-medium">{source.name}</p>
          <span className="border-foreground/15 text-foreground/55 inline-flex shrink-0 items-center rounded-full border px-1.5 py-0.5 font-mono text-[9px] tracking-wider uppercase">
            {source.connector_type}
          </span>
        </div>
        <div className="text-foreground/55 mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-[10px] tracking-wider uppercase">
          <span>last sync · {lastSync}</span>
          {source.schedule_minutes && source.schedule_minutes > 0 && (
            <>
              <span>·</span>
              <span>every {source.schedule_minutes}m</span>
            </>
          )}
        </div>
      </div>
      {source.last_sync_status && (
        <Badge
          title={source.last_error ?? undefined}
          className={cn(
            "inline-flex shrink-0 items-center px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase",
            statusColor,
          )}
        >
          {source.last_sync_status}
        </Badge>
      )}
      <Button
        variant="ghost"
        size="sm"
        className="text-foreground/55 hover:text-foreground h-7 w-7 p-0"
        onClick={onTrigger}
        title="Trigger sync now"
      >
        <RotateCw className="h-3.5 w-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="text-foreground/55 hover:text-destructive h-7 w-7 p-0"
        onClick={() => {
          if (confirm(`Disconnect "${source.name}"?`)) onDelete();
        }}
        title="Remove source"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </li>
  );
}

function DocumentRow({ doc, onDelete }: { doc: KBDocument; onDelete: () => void }) {
  return (
    <li className="hover:bg-foreground/[0.02] flex items-center gap-3 px-4 py-3 transition-colors">
      <div className="bg-foreground/8 text-foreground/65 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
        <FileText className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-foreground truncate text-sm font-medium" title={doc.filename}>
          {doc.filename}
        </p>
        <div className="text-foreground/55 mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-[10px] tracking-wider uppercase">
          {doc.filesize !== null && <span>{formatBytes(doc.filesize)}</span>}
          {doc.filetype && (
            <>
              <span>·</span>
              <span className="truncate">{doc.filetype}</span>
            </>
          )}
          {doc.chunk_count > 0 && (
            <>
              <span>·</span>
              <span>{doc.chunk_count} chunks</span>
            </>
          )}
        </div>
      </div>
      <StatusBadge status={doc.status} message={doc.error_message} />
      <Button
        variant="ghost"
        size="sm"
        className="text-foreground/55 hover:text-destructive h-7 w-7 p-0"
        onClick={() => {
          if (confirm(`Remove "${doc.filename}" from this knowledge base?`)) onDelete();
        }}
        title="Remove document"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </li>
  );
}

function StatusBadge({ status, message }: { status: string; message: string | null }) {
  const config = {
    completed: {
      Icon: CheckCircle2,
      cls: "text-green-700 bg-green-100 dark:bg-green-900/30 dark:text-green-300",
      label: "Ready",
    },
    processing: {
      Icon: Loader2,
      cls: "text-blue-700 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300",
      label: "Processing",
      spin: true,
    },
    pending: {
      Icon: Clock,
      cls: "text-amber-700 bg-amber-100 dark:bg-amber-900/30 dark:text-amber-300",
      label: "Pending",
    },
    failed: {
      Icon: AlertCircle,
      cls: "text-red-700 bg-red-100 dark:bg-red-900/30 dark:text-red-300",
      label: "Failed",
    },
  } as const;
  const c = (config as Record<string, (typeof config)[keyof typeof config]>)[status] ?? {
    Icon: Clock,
    cls: "text-foreground/65 bg-foreground/8",
    label: status,
    spin: false,
  };
  return (
    <Badge
      title={message ?? undefined}
      className={cn(
        "inline-flex shrink-0 items-center gap-1 px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase",
        c.cls,
      )}
    >
      <c.Icon className={cn("h-3 w-3", "spin" in c && c.spin && "animate-spin")} />
      {c.label}
    </Badge>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
