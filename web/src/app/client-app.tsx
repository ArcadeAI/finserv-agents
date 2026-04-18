"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import type { UIMessage } from "ai";
import { AppShell } from "@/components/layout/AppShell";
import { ChatPanel } from "@/components/chat/ChatPanel";

function storageKey(role: string) {
  return `finserv-chat-${role}`;
}

function saveMessages(role: string, messages: UIMessage[]) {
  try {
    localStorage.setItem(storageKey(role), JSON.stringify(messages));
  } catch {}
}

function clearStoredMessages(role: string) {
  try {
    localStorage.removeItem(storageKey(role));
  } catch {}
}

function subscribeToStoredMessages(role: string, onChange: () => void) {
  const key = storageKey(role);
  const handler = (event: StorageEvent) => {
    if (event.key === key) onChange();
  };

  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

function getStoredMessagesSnapshot(role: string): string {
  try {
    return localStorage.getItem(storageKey(role)) ?? "";
  } catch {
    return "";
  }
}

export function ClientApp({ agentRole }: { agentRole: string }) {
  const storedMessages = useSyncExternalStore(
    useCallback(
      (onStoreChange) => subscribeToStoredMessages(agentRole, onStoreChange),
      [agentRole]
    ),
    useCallback(() => getStoredMessagesSnapshot(agentRole), [agentRole]),
    () => ""
  );

  const initialMessages = useMemo(() => {
    if (!storedMessages) return undefined;
    try {
      return JSON.parse(storedMessages) as UIMessage[];
    } catch {
      return undefined;
    }
  }, [storedMessages]);

  return (
    <LiveChat
      key={`${agentRole}-${initialMessages?.length ?? 0}`}
      agentRole={agentRole}
      initialMessages={initialMessages}
    />
  );
}

function LiveChat({
  agentRole,
  initialMessages,
}: {
  agentRole: string;
  initialMessages?: UIMessage[];
}) {
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: "/api/chat",
        body: { agentRole },
      }),
    [agentRole]
  );

  const { messages, sendMessage, status, setMessages, error, clearError } = useChat({
    transport,
    ...(initialMessages && initialMessages.length > 0
      ? { messages: initialMessages }
      : {}),
  });

  useEffect(() => {
    if (messages.length > 0) {
      saveMessages(agentRole, messages);
      return;
    }
    clearStoredMessages(agentRole);
  }, [messages, agentRole]);

  const isProcessing = status === "streaming" || status === "submitted";

  const handleSend = useCallback(
    (text: string) => {
      clearError();
      sendMessage({ text });
    },
    [clearError, sendMessage]
  );

  const handleNewChat = useCallback(() => {
    clearError();
    setMessages([]);
    clearStoredMessages(agentRole);
  }, [clearError, setMessages, agentRole]);

  return (
    <AppShell
      agentRole={agentRole}
      onNewChat={handleNewChat}
      chatPanel={
        <ChatPanel
          messages={messages}
          error={error}
          isProcessing={isProcessing}
          onSend={handleSend}
          agentRole={agentRole}
        />
      }
    />
  );
}
