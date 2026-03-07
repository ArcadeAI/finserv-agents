"use client";

import { Shield, Plus, User } from "lucide-react";

interface HeaderProps {
  isLive: boolean;
  agentRole: string;
  onNewChat: () => void;
}

const AGENTS: Record<string, { name: string; shift: string; color: string; bg: string; border: string; dot: string }> = {
  john: {
    name: "John",
    shift: "Morning Shift",
    color: "text-teal-400",
    bg: "bg-teal-500/10",
    border: "border-teal-500/20",
    dot: "bg-teal-400",
  },
  rob: {
    name: "Rob",
    shift: "Afternoon Shift",
    color: "text-violet-400",
    bg: "bg-violet-500/10",
    border: "border-violet-500/20",
    dot: "bg-violet-400",
  },
};

export function Header({ isLive, agentRole, onNewChat }: HeaderProps) {
  const agent = AGENTS[agentRole] ?? AGENTS.john;

  return (
    <header className="h-12 bg-slate-950 border-b border-slate-800/60 flex items-center justify-between px-5 shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-slate-100 tracking-tight">
            FinServ Agents
          </span>
        </div>

        <div className="h-4 w-px bg-slate-800" />

        <div
          className={`flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold ${agent.bg} ${agent.color} border ${agent.border}`}
        >
          <User className="w-3 h-3" />
          {agent.name}
          <span className="text-[10px] font-normal opacity-70">{agent.shift}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <div
            className={`w-1.5 h-1.5 rounded-full ${
              isLive ? "bg-emerald-400" : "bg-amber-400"
            }`}
          />
          <span className="text-[11px] text-slate-500">
            {isLive ? "Live" : "Demo"}
          </span>
        </div>
      </div>

      <button
        onClick={onNewChat}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all"
      >
        <Plus className="w-3.5 h-3.5" />
        New Chat
      </button>
    </header>
  );
}
