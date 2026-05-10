"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Download, ExternalLink, ThumbsUp, ThumbsDown } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiClient } from "@/lib/api-client";
import type { MessageRatingListResponse, RatingSummary } from "@/types";

const PAGE_SIZE = 50;

type RatingFilter = "all" | "positive" | "negative";

export default function AdminRatingsPage() {
  const [summary, setSummary] = useState<RatingSummary | null>(null);
  const [ratings, setRatings] = useState<MessageRatingListResponse | null>(null);
  const [filter, setFilter] = useState<RatingFilter>("all");
  const [commentsOnly, setCommentsOnly] = useState(false);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [exportFormat, setExportFormat] = useState<"json" | "csv">("csv");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const ratingsParams = new URLSearchParams({
        skip: String(page * PAGE_SIZE),
        limit: String(PAGE_SIZE),
        with_comments_only: String(commentsOnly),
      });
      if (filter !== "all") {
        ratingsParams.set("rating_filter", filter === "positive" ? "1" : "-1");
      }

      const [summaryData, ratingsData] = await Promise.all([
        apiClient.get<RatingSummary>("/admin/ratings/summary?days=30"),
        apiClient.get<MessageRatingListResponse>(`/admin/ratings?${ratingsParams}`),
      ]);
      setSummary(summaryData);
      setRatings(ratingsData);
    } catch {
      /* ignore — errors shown via empty state */
    } finally {
      setLoading(false);
    }
  }, [page, filter, commentsOnly]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = () => {
    const params = new URLSearchParams({ export_format: exportFormat });
    if (filter !== "all") params.set("rating_filter", filter === "positive" ? "1" : "-1");
    if (commentsOnly) params.set("with_comments_only", "true");
    window.open(`/api/v1/admin/ratings/export?${params}`, "_blank");
  };

  const totalPages = ratings ? Math.ceil(ratings.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Response Ratings</h1>
          <p className="text-muted-foreground text-sm">
            Message quality feedback from users over the last 30 days.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={exportFormat} onValueChange={(v) => setExportFormat(v as "json" | "csv")}>
            <SelectTrigger className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="csv">CSV</SelectItem>
              <SelectItem value="json">JSON</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      {loading && !summary ? (
        <div className="grid gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : summary ? (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Ratings</CardDescription>
              <CardTitle className="text-3xl tabular-nums">{summary.total_ratings}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Likes</CardDescription>
              <CardTitle className="flex items-center gap-2 text-3xl text-green-600 tabular-nums">
                <ThumbsUp className="h-5 w-5" />
                {summary.like_count}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Dislikes</CardDescription>
              <CardTitle className="text-destructive flex items-center gap-2 text-3xl tabular-nums">
                <ThumbsDown className="h-5 w-5" />
                {summary.dislike_count}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Average Rating</CardDescription>
              <CardTitle className="text-3xl tabular-nums">
                {summary.average_rating.toFixed(2)}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      ) : null}

      {/* Chart */}
      {summary && summary.ratings_by_day.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ratings Over Time</CardTitle>
            <CardDescription>Daily like/dislike counts.</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={summary.ratings_by_day}
                margin={{ top: 4, right: 4, bottom: 4, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
                <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "6px",
                  }}
                />
                <Bar dataKey="likes" fill="#22c55e" name="Likes" radius={[4, 4, 0, 0]} />
                <Bar
                  dataKey="dislikes"
                  fill="hsl(var(--destructive))"
                  name="Dislikes"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Select
          value={filter}
          onValueChange={(v) => {
            setFilter(v as RatingFilter);
            setPage(0);
          }}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Ratings</SelectItem>
            <SelectItem value="positive">Likes Only</SelectItem>
            <SelectItem value="negative">Dislikes Only</SelectItem>
          </SelectContent>
        </Select>
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={commentsOnly}
            onCheckedChange={(v) => {
              setCommentsOnly(!!v);
              setPage(0);
            }}
          />
          With comments only
        </label>
      </div>

      {/* Ratings table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Rating</TableHead>
              <TableHead>Comment</TableHead>
              <TableHead>Message</TableHead>
              <TableHead>User</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading
              ? Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={6}>
                      <Skeleton className="h-8 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              : ratings?.items.map((rating) => (
                  <TableRow key={rating.id}>
                    <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                      {new Date(rating.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {rating.rating === 1 ? (
                        <Badge variant="default" className="bg-green-600">
                          <ThumbsUp className="mr-1 h-3 w-3" />
                          Like
                        </Badge>
                      ) : (
                        <Badge variant="destructive">
                          <ThumbsDown className="mr-1 h-3 w-3" />
                          Dislike
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-sm">
                      {rating.comment || <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell className="text-muted-foreground max-w-xs truncate text-sm">
                      {rating.message_content || "—"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {rating.user_name || rating.user_email || "—"}
                    </TableCell>
                    <TableCell>
                      {rating.conversation_id && (
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/chat?id=${rating.conversation_id}`}>
                            <ExternalLink className="mr-1 h-3 w-3" />
                            View
                          </Link>
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
            {!loading && ratings?.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-muted-foreground py-8 text-center">
                  No ratings found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground text-sm">
            Page {page + 1} of {totalPages} &middot; {ratings?.total} total
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
