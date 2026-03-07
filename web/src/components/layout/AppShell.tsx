"use client";

import { Header } from "./Header";
import { ContextPanel } from "./ContextPanel";
import type { ReactNode } from "react";

interface AppShellProps {
  chatPanel: ReactNode;
  isLive: boolean;
  agentRole: string;
  onNewChat: () => void;
}

export function AppShell({ chatPanel, isLive, agentRole, onNewChat }: AppShellProps) {
  return (
    <div className="h-screen flex flex-col bg-slate-950 overflow-hidden">
      <Header isLive={isLive} agentRole={agentRole} onNewChat={onNewChat} />
      <div className="flex-1 min-h-0 flex">
        <div className="flex-1 min-w-0 flex justify-center">
          <div className="w-full max-w-3xl flex flex-col min-h-0">
            {chatPanel}
          </div>
        </div>
        <div className="w-[360px] shrink-0 border-l border-slate-800/60 flex flex-col overflow-hidden">
          <ContextPanel agentRole={agentRole} />
        </div>
      </div>
    </div>
  );
}
