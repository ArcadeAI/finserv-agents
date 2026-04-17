"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Database,
  Activity,
  ClipboardList,
  Inbox,
  User,
  AlertTriangle,
  CheckCircle2,
  Clock,
} from "lucide-react";

interface RedisContext {
  context: Record<string, unknown> | null;
  events: { id: string; fields: Record<string, string> }[];
  error?: string;
}

interface ContextPanelProps {
  agentRole: string;
}

const timestampFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function formatTimestamp(value?: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return timestampFormatter.format(date);
}

export function ContextPanel({ agentRole }: ContextPanelProps) {
  const [data, setData] = useState<RedisContext | null>(null);
  const [loading, setLoading] = useState(true);

  const poll = useCallback(async () => {
    try {
      const res = await fetch("/api/redis/context");
      const json = await res.json();
      setData(json);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [poll]);

  const ctx = data?.context as Record<string, unknown> | null;
  const hasContext = ctx && Object.keys(ctx).length > 0;
  const hasEvents = data?.events && data.events.length > 0;
  const isEmpty = !hasContext && !hasEvents;

  const agentName = ctx?.agent as string | undefined;
  const shift = ctx?.shift as string | undefined;
  const summary = ctx?.summary as string | undefined;
  const borrowers = ctx?.borrowers_reviewed as string[] | undefined;
  const actions = ctx?.actions_taken as string[] | undefined;
  const pending = ctx?.pending_items as string[] | undefined;
  const urgent = ctx?.urgent_flags as string[] | undefined;
  const notes = ctx?.notes as string | undefined;
  const lastUpdated = ctx?.last_updated as string | undefined;
  const formattedLastUpdated = formatTimestamp(lastUpdated);

  return (
    <div className="flex flex-col h-full bg-slate-950">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 border-b border-slate-800/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-3.5 h-3.5 text-red-400" />
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Shift Handoff
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Database className="w-3 h-3 text-red-500/60" />
            <span className="text-[10px] text-slate-600">Redis</span>
            <div className={`w-1.5 h-1.5 rounded-full ${data?.error ? "bg-red-400" : "bg-emerald-400"}`} />
          </div>
        </div>
        {agentRole === "rob" && (
          <p className="text-[10px] text-slate-500 mt-1">
            Reading what John worked on this morning...
          </p>
        )}
        {agentRole === "john" && (
          <p className="text-[10px] text-slate-500 mt-1">
            Your progress is shared live with Rob
          </p>
        )}
      </div>

      <div className="flex-1 overflow-auto px-4 py-3 space-y-3">
        {isEmpty && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <Inbox className="w-8 h-8 text-slate-700 mb-3" />
            <p className="text-xs text-slate-500 font-medium">No handoff context yet</p>
            <p className="text-[11px] text-slate-600 mt-2 leading-relaxed">
              {agentRole === "john"
                ? "Start working on your cases. As you make progress, your context will appear here and be visible to Rob on the afternoon shift."
                : "John hasn't logged any context from his morning shift yet. Ask your agent to check Redis for any updates."}
            </p>
          </div>
        )}

        {/* Who wrote this context */}
        {hasContext && agentName && (
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${
            agentName === "John"
              ? "bg-teal-500/5 border-teal-500/20"
              : "bg-violet-500/5 border-violet-500/20"
          }`}>
            <User className={`w-3.5 h-3.5 ${agentName === "John" ? "text-teal-400" : "text-violet-400"}`} />
            <div>
              <span className={`text-[12px] font-semibold ${agentName === "John" ? "text-teal-400" : "text-violet-400"}`}>
                {agentName}
              </span>
              {shift && (
                <span className="text-[10px] text-slate-500 ml-1.5">{shift}</span>
              )}
            </div>
            {formattedLastUpdated && (
              <span className="text-[9px] text-slate-600 ml-auto flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" />
                {formattedLastUpdated}
              </span>
            )}
          </div>
        )}

        {/* Summary */}
        {summary && (
          <div className="border border-slate-800 rounded-lg p-3">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Summary
            </span>
            <p className="text-[12px] text-slate-300 mt-1 leading-relaxed">{summary}</p>
          </div>
        )}

        {/* Urgent Flags */}
        {urgent && urgent.length > 0 && (
          <div className="border border-amber-500/20 bg-amber-500/5 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
                Urgent
              </span>
            </div>
            <div className="space-y-1">
              {urgent.map((item, i) => (
                <p key={i} className="text-[11px] text-amber-200/80 pl-2 border-l-2 border-amber-500/30">
                  {item}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Borrowers Reviewed */}
        {borrowers && borrowers.length > 0 && (
          <div className="border border-slate-800 rounded-lg p-3">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Borrowers Reviewed
            </span>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {borrowers.map((name, i) => (
                <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700/50">
                  {name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Actions Taken */}
        {actions && actions.length > 0 && (
          <div className="border border-slate-800 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                Actions Completed
              </span>
            </div>
            <div className="space-y-1">
              {actions.map((item, i) => (
                <p key={i} className="text-[11px] text-slate-300 pl-2 border-l-2 border-emerald-500/20">
                  {item}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Pending Items */}
        {pending && pending.length > 0 && (
          <div className="border border-slate-800 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Clock className="w-3 h-3 text-blue-400" />
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                Pending for Next Shift
              </span>
            </div>
            <div className="space-y-1">
              {pending.map((item, i) => (
                <p key={i} className="text-[11px] text-slate-300 pl-2 border-l-2 border-blue-500/20">
                  {item}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Notes */}
        {notes && (
          <div className="border border-slate-800 rounded-lg p-3">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Notes
            </span>
            <p className="text-[12px] text-slate-400 mt-1 leading-relaxed italic">{notes}</p>
          </div>
        )}

        {/* Raw context for any extra fields */}
        {hasContext && (() => {
          const knownKeys = new Set(["agent", "shift", "last_updated", "summary", "borrowers_reviewed", "actions_taken", "pending_items", "urgent_flags", "notes"]);
          const extraKeys = Object.keys(ctx!).filter(k => !knownKeys.has(k));
          if (extraKeys.length === 0) return null;
          return (
            <div className="border border-slate-800 rounded-lg p-3">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                Additional Context
              </span>
              <pre className="mt-1 text-[10px] text-slate-400 font-mono bg-slate-900/60 rounded p-2 overflow-x-auto">
                {JSON.stringify(
                  Object.fromEntries(extraKeys.map(k => [k, ctx![k]])),
                  null, 2
                )}
              </pre>
            </div>
          );
        })()}

        {/* Event Stream */}
        {hasEvents && (
          <div className="border border-slate-800 rounded-lg overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-900/60 border-b border-slate-800">
              <Activity className="w-3 h-3 text-amber-400" />
              <span className="text-[11px] font-semibold text-slate-300">
                Activity Log
              </span>
              <span className="text-[9px] text-slate-600 ml-auto">
                {data!.events.length} events
              </span>
            </div>
            <div className="divide-y divide-slate-800/50 max-h-48 overflow-auto">
              {data!.events.map((event) => (
                <div key={event.id} className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-semibold ${
                      event.fields.agent === "John" ? "text-teal-400" : 
                      event.fields.agent === "Rob" ? "text-violet-400" : "text-slate-400"
                    }`}>
                      {event.fields.agent || "agent"}
                    </span>
                    <span className="text-[11px] text-slate-300 truncate flex-1">
                      {event.fields.action || Object.values(event.fields).join(" — ")}
                    </span>
                  </div>
                  {event.fields.borrower && (
                    <span className="text-[10px] text-slate-500 ml-0.5">
                      re: {event.fields.borrower}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="shrink-0 px-4 py-2 border-t border-slate-800/60">
        <span className="text-[9px] text-slate-600">
          {data?.error ? "Redis unavailable" : "Live from Redis Cloud"}
        </span>
      </div>
    </div>
  );
}
