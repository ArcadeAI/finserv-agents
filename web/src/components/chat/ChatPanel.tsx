"use client";

import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { SuggestionPills } from "./SuggestionPills";
import type { UIMessage } from "ai";
import type { MockMessage } from "@/lib/types";

interface ChatPanelProps {
  messages?: UIMessage[];
  mockMessages?: MockMessage[];
  isProcessing: boolean;
  onSend: (message: string) => void;
  agentRole?: string;
}

export function ChatPanel({
  messages,
  mockMessages,
  isProcessing,
  onSend,
  agentRole,
}: ChatPanelProps) {
  const isEmpty = (messages?.length ?? 0) === 0 && (mockMessages?.length ?? 0) === 0;

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {isEmpty ? (
        <SuggestionPills onSelect={onSend} agentRole={agentRole} />
      ) : (
        <MessageList
          messages={messages}
          mockMessages={mockMessages}
          isProcessing={isProcessing}
        />
      )}
      <ChatInput onSend={onSend} isDisabled={isProcessing} />
    </div>
  );
}
