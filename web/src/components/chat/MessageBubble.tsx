"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ToolCallCard } from "./ToolCallCard";
import type { ToolCallData } from "@/lib/types";
import type { UIMessage } from "ai";

interface MessageBubbleProps {
  role: "user" | "assistant" | "system";
  content?: string;
  parts?: UIMessage["parts"];
  mockToolCalls?: ToolCallData[];
}

function extractTextFromParts(parts?: UIMessage["parts"]): string {
  if (!parts) return "";
  return parts
    .filter((p) => p.type === "text")
    .map((p) => (p as { type: "text"; text: string }).text)
    .join("");
}

function extractToolCallsFromParts(
  parts?: UIMessage["parts"]
): ToolCallData[] {
  if (!parts) return [];
  return parts
    .filter((p) => p.type === "dynamic-tool" || p.type.startsWith("tool-"))
    .map((p) => {
      const inv = p as {
        type: string;
        toolCallId: string;
        toolName?: string;
        state: string;
        input?: unknown;
        output?: unknown;
        errorText?: string;
      };
      const toolName = inv.toolName ?? inv.type.replace("tool-", "");
      return {
        id: inv.toolCallId,
        tool: toolName,
        input: (inv.input ?? {}) as Record<string, unknown>,
        result: inv.output,
        status:
          inv.state === "output-available"
            ? ("success" as const)
            : inv.state === "error"
              ? ("error" as const)
              : ("running" as const),
        error: inv.errorText,
      };
    });
}

export function MessageBubble({
  role,
  content,
  parts,
  mockToolCalls,
}: MessageBubbleProps) {
  const isUser = role === "user";

  if (isUser) {
    const text = content || extractTextFromParts(parts);
    return (
      <div className="flex justify-end px-6 py-2">
        <div className="max-w-[75%] bg-indigo-600 text-white rounded-2xl rounded-br-md px-4 py-2.5">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
        </div>
      </div>
    );
  }

  const toolCalls =
    mockToolCalls && mockToolCalls.length > 0
      ? mockToolCalls
      : extractToolCallsFromParts(parts);
  const text = content || extractTextFromParts(parts);

  return (
    <div className="flex justify-start px-6 py-2">
      <div className="max-w-full min-w-0">
        {toolCalls.map((tc) => (
          <ToolCallCard key={tc.id} toolCall={tc} />
        ))}

        {text && (
          <div className="bg-slate-800/60 rounded-2xl rounded-bl-md px-4 py-2.5 mt-1">
            <div className="agent-markdown text-sm text-slate-100 leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {text}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
