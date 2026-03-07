"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import type { UIMessage } from "ai";
import type { MockMessage } from "@/lib/types";

interface MessageListProps {
  messages?: UIMessage[];
  mockMessages?: MockMessage[];
  isProcessing: boolean;
}

export function MessageList({
  messages,
  mockMessages,
  isProcessing,
}: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, mockMessages, isProcessing]);

  return (
    <div className="flex-1 overflow-y-auto py-4">
      {messages?.map((msg) => (
        <MessageBubble
          key={msg.id}
          role={msg.role}
          parts={msg.parts}
        />
      ))}

      {mockMessages?.map((msg) => (
        <MessageBubble
          key={msg.id}
          role={msg.role}
          content={msg.content}
          mockToolCalls={msg.toolCalls}
        />
      ))}

      {isProcessing && <TypingIndicator />}
      <div ref={endRef} />
    </div>
  );
}
