"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import type { UIMessage } from "ai";
import { AppShell } from "@/components/layout/AppShell";
import { ChatPanel } from "@/components/chat/ChatPanel";
import type { MockMessage } from "@/lib/types";

// ── Mock data ──────────────────────────────────────────────────────────
const MOCK_MESSAGES: MockMessage[] = [
  {
    id: "1",
    role: "user",
    content: "Good morning. Give me my portfolio health check.",
    timestamp: new Date("2026-03-03T09:01:00"),
  },
  {
    id: "2",
    role: "assistant",
    content: `Your portfolio looks healthy this morning. Here's the breakdown:

| Metric | Value |
|---|---|
| Active Loans | 2,847 |
| Total Outstanding | $184.2M |
| Current | 91.4% |
| DPD 30+ | 3.2% (91 loans) |
| DPD 60+ | 1.1% (31 loans) |
| DPD 90+ | 0.4% (12 loans) |
| Avg Credit Score | 712 |
| Missed Payments (30d) | 47 |

**Key observations:**
- DPD 30+ is slightly above your 3.0% target — driven primarily by 4 business accounts that entered delinquency this week
- **Apex Industrial LLC** is your largest exposure at $287K, currently 22 DPD on their first-ever missed payment
- **Robert Keane** has an open fraud signal for income mismatch — recommend immediate review

Would you like me to drill into the delinquent borrowers or send outreach to the high-recovery ones?`,
    toolCalls: [
      {
        id: "tc-1",
        tool: "get_portfolio_summary",
        input: {},
        result: { active_loans: 2847, total_outstanding: 184200000 },
        status: "success" as const,
        duration_ms: 1240,
      },
    ],
    timestamp: new Date("2026-03-03T09:01:02"),
  },
];

function storageKey(role: string) {
  return `finserv-chat-${role}`;
}

function saveMessages(role: string, messages: UIMessage[]) {
  try {
    localStorage.setItem(storageKey(role), JSON.stringify(messages));
  } catch {}
}

function loadMessages(role: string): UIMessage[] {
  try {
    const stored = localStorage.getItem(storageKey(role));
    if (stored) return JSON.parse(stored);
  } catch {}
  return [];
}

function clearStoredMessages(role: string) {
  try {
    localStorage.removeItem(storageKey(role));
  } catch {}
}

// ── Mock Mode ──────────────────────────────────────────────────────────
function MockPage({ agentRole }: { agentRole: string }) {
  const [mockMessages, setMockMessages] = useState<MockMessage[]>(MOCK_MESSAGES);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSend = useCallback((text: string) => {
    const userMsg: MockMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMockMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);
    setTimeout(() => setIsProcessing(false), 2000);
  }, []);

  return (
    <AppShell
      isLive={false}
      agentRole={agentRole}
      onNewChat={() => setMockMessages(MOCK_MESSAGES)}
      chatPanel={
        <ChatPanel
          mockMessages={mockMessages}
          isProcessing={isProcessing}
          onSend={handleSend}
          agentRole={agentRole}
        />
      }
    />
  );
}

// ── Live Mode ──────────────────────────────────────────────────────────
function LivePage({ agentRole }: { agentRole: string }) {
  const [initialMessages, setInitialMessages] = useState<UIMessage[] | undefined>(undefined);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const saved = loadMessages(agentRole);
    if (saved.length > 0) setInitialMessages(saved);
    setLoaded(true);
  }, [agentRole]);

  if (!loaded) return null;
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
    () => new DefaultChatTransport({ api: "/api/chat" }),
    []
  );

  const { messages, sendMessage, status, setMessages } = useChat({
    transport,
    body: { agentRole },
    ...(initialMessages && initialMessages.length > 0
      ? { messages: initialMessages }
      : {}),
  });

  useEffect(() => {
    if (messages.length > 0) saveMessages(agentRole, messages);
  }, [messages, agentRole]);

  const isProcessing = status === "streaming" || status === "submitted";

  const handleSend = useCallback(
    (text: string) => { sendMessage({ text }); },
    [sendMessage]
  );

  const handleNewChat = useCallback(() => {
    setMessages([]);
    clearStoredMessages(agentRole);
  }, [setMessages, agentRole]);

  return (
    <AppShell
      isLive={true}
      agentRole={agentRole}
      onNewChat={handleNewChat}
      chatPanel={
        <ChatPanel
          messages={messages}
          isProcessing={isProcessing}
          onSend={handleSend}
          agentRole={agentRole}
        />
      }
    />
  );
}

// ── Entry ──────────────────────────────────────────────────────────────
export function ClientApp({ isLive, agentRole }: { isLive: boolean; agentRole: string }) {
  return isLive ? <LivePage agentRole={agentRole} /> : <MockPage agentRole={agentRole} />;
}
