"use client";

export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 px-6 py-3">
      <div className="flex items-center gap-1.5 bg-slate-800/60 rounded-2xl rounded-bl-md px-4 py-3">
        <div className="typing-dot w-1.5 h-1.5 rounded-full bg-slate-400" />
        <div className="typing-dot w-1.5 h-1.5 rounded-full bg-slate-400" />
        <div className="typing-dot w-1.5 h-1.5 rounded-full bg-slate-400" />
        <span className="text-xs text-slate-500 ml-2">Thinking...</span>
      </div>
    </div>
  );
}
