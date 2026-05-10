"use client";

import { useState } from "react";
import { Settings2 } from "lucide-react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui";
import { cn } from "@/lib/utils";

export type ThinkingEffort = "off" | "low" | "medium" | "high";

interface ChatSettingsProps {
  /** Initial temperature (0–2). null = use server default. */
  initialTemperature?: number | null;
  /** Initial thinking effort. "off" = disabled. */
  initialThinkingEffort?: ThinkingEffort;
  /** Called when temperature changes. null = use server default. */
  onTemperatureChange: (value: number | null) => void;
  /** Called when thinking effort changes. null = disabled. */
  onThinkingEffortChange: (value: "low" | "medium" | "high" | null) => void;
}

const EFFORT_OPTIONS: { label: string; value: ThinkingEffort; hint: string }[] = [
  { label: "Off", value: "off", hint: "Direct answer, no reasoning" },
  { label: "Low", value: "low", hint: "Quick reasoning" },
  { label: "Medium", value: "medium", hint: "Balanced" },
  { label: "High", value: "high", hint: "Deep, slower" },
];

export function ChatSettings({
  initialTemperature = null,
  initialThinkingEffort = "off",
  onTemperatureChange,
  onThinkingEffortChange,
}: ChatSettingsProps) {
  // null sentinel = "use server default" — distinct from any numeric value.
  const [temperature, setTemperature] = useState<number | null>(initialTemperature);
  const [effort, setEffort] = useState<ThinkingEffort>(initialThinkingEffort);

  const overridden = temperature !== null || effort !== "off";

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Chat settings"
          data-chat-settings-trigger
          className={cn(
            "text-foreground/55 hover:bg-foreground/5 hover:text-foreground inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-mono text-[11px] tracking-wider uppercase transition-colors",
            overridden && "text-foreground",
          )}
        >
          <Settings2 className="h-3.5 w-3.5" />
          {overridden ? "Custom" : "Defaults"}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-4">
        {/* Temperature */}
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <label htmlFor="chat-temp" className="text-foreground text-xs font-semibold">
              Temperature
            </label>
            <span className="text-foreground/55 font-mono text-[11px] tabular-nums">
              {temperature === null ? "default" : temperature.toFixed(2)}
            </span>
          </div>
          <input
            id="chat-temp"
            type="range"
            min={0}
            max={2}
            step={0.05}
            value={temperature ?? 0.7}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              setTemperature(v);
              onTemperatureChange(v);
            }}
            className="accent-brand bg-foreground/15 h-1 w-full cursor-pointer appearance-none rounded-full"
          />
          <div className="text-foreground/45 flex justify-between font-mono text-[10px]">
            <span>focused · 0</span>
            <span>creative · 2</span>
          </div>
          {temperature !== null && (
            <button
              type="button"
              onClick={() => {
                setTemperature(null);
                onTemperatureChange(null);
              }}
              className="text-foreground/55 hover:text-foreground text-[11px] underline-offset-2 hover:underline"
            >
              Reset to server default
            </button>
          )}
        </div>

        {/* Thinking effort */}
        <div className="mt-5 space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-foreground text-xs font-semibold">Thinking effort</span>
            <span className="text-foreground/45 text-[10px]">model-dependent</span>
          </div>
          <div className="grid grid-cols-4 gap-1">
            {EFFORT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  setEffort(opt.value);
                  onThinkingEffortChange(opt.value === "off" ? null : opt.value);
                }}
                className={cn(
                  "rounded-md px-2 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
                  effort === opt.value
                    ? "bg-foreground text-background"
                    : "border-foreground/15 text-foreground/55 hover:text-foreground border",
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <p className="text-foreground/55 text-[11px]">
            {EFFORT_OPTIONS.find((o) => o.value === effort)?.hint}
          </p>
        </div>

        <p className="text-foreground/45 mt-5 text-[10px] leading-relaxed">
          Model needs to support each capability — temperature applies to most chat models; thinking
          is ignored if the selected model can&apos;t reason. Settings persist for the current chat
          session.
        </p>
      </PopoverContent>
    </Popover>
  );
}
