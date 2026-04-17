"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import type { UIMessage } from "ai";

interface MessageListProps {
  messages: UIMessage[];
  isProcessing: boolean;
}

export function MessageList({ messages, isProcessing }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  return (
    <div className="flex-1 overflow-y-auto py-4">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
        />
      ))}

      {isProcessing && <TypingIndicator />}
      <div ref={endRef} />
    </div>
  );
}
