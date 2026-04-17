"use client";

import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { SuggestionPills } from "./SuggestionPills";
import type { UIMessage } from "ai";

interface ChatPanelProps {
  messages: UIMessage[];
  error?: Error;
  isProcessing: boolean;
  onSend: (message: string) => void;
  agentRole?: string;
}

export function ChatPanel({
  messages,
  error,
  isProcessing,
  onSend,
  agentRole,
}: ChatPanelProps) {
  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {isEmpty ? (
        <SuggestionPills onSelect={onSend} agentRole={agentRole} />
      ) : (
        <MessageList
          messages={messages}
          isProcessing={isProcessing}
        />
      )}
      {error && (
        <div className="px-6 pb-3">
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            <p className="font-medium">Something went wrong.</p>
            <p className="mt-1 text-rose-200/80">
              {error.message || "The live chat request failed. Check the current setup and try again."}
            </p>
          </div>
        </div>
      )}
      <ChatInput onSend={onSend} isDisabled={isProcessing} />
    </div>
  );
}
