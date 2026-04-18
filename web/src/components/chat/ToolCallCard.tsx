"use client";

import { useState } from "react";
import { ChevronRight, ChevronDown, Check, X, Loader2 } from "lucide-react";
import { getToolMeta, getToolDisplayName } from "@/lib/tool-registry";
import type { ToolCallData } from "@/lib/types";

interface ToolCallCardProps {
  toolCall: ToolCallData;
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const meta = getToolMeta(toolCall.tool);

  const borderColor = meta?.borderColor ?? "border-l-slate-500";
  const Icon = meta?.icon;
  const displayName = getToolDisplayName(toolCall.tool);

  const statusIcon =
    toolCall.status === "running" ? (
      <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin" />
    ) : toolCall.status === "success" ? (
      <Check className="w-3.5 h-3.5 text-emerald-400" />
    ) : (
      <X className="w-3.5 h-3.5 text-rose-400" />
    );

  return (
    <div
      className={`bg-slate-900 border-l-2 ${borderColor} rounded-md my-2 ${
        toolCall.status === "running" ? "tool-running" : ""
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-slate-800/50 transition-colors rounded-md"
      >
        {Icon && <Icon className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
        <span className="text-xs font-medium text-slate-300 truncate flex-1">
          {displayName}
        </span>
        <div className="flex items-center gap-1.5 shrink-0">
          {statusIcon}
          {expanded ? (
            <ChevronDown className="w-3 h-3 text-slate-500" />
          ) : (
            <ChevronRight className="w-3 h-3 text-slate-500" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          <div className="border-t border-slate-800 pt-2">
            {toolCall.input && Object.keys(toolCall.input).length > 0 && (
              <div>
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">
                  Input
                </span>
                <pre className="mt-1 text-[11px] text-slate-400 font-mono bg-slate-950/60 rounded p-2 overflow-x-auto max-h-32 overflow-y-auto">
                  {JSON.stringify(toolCall.input, null, 2)}
                </pre>
              </div>
            )}

            {toolCall.result != null && (
              <div className="mt-2">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">
                  Result
                </span>
                <pre className="mt-1 text-[11px] text-slate-400 font-mono bg-slate-950/60 rounded p-2 overflow-x-auto max-h-48 overflow-y-auto">
                  {typeof toolCall.result === "string"
                    ? toolCall.result
                    : JSON.stringify(toolCall.result, null, 2)}
                </pre>
              </div>
            )}

            {toolCall.error && (
              <div className="mt-2">
                <span className="text-[10px] uppercase tracking-wider text-rose-500 font-medium">
                  Error
                </span>
                <pre className="mt-1 text-[11px] text-rose-400 font-mono bg-rose-950/20 rounded p-2 overflow-x-auto">
                  {toolCall.error}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
