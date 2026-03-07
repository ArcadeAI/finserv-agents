"use client";

const JOHN_SUGGESTIONS = [
  {
    text: "I'm starting my morning shift. Pull up the portfolio health and delinquent accounts so I can prioritize my day. Save the initial shift context.",
    desc: "Step 1 — Review portfolio and begin shift",
  },
  {
    text: "Pull up Maria Santos' full profile. She's at DPD 30 and I need to understand her payment pattern before I call her. Log that I'm researching her case.",
    desc: "Step 2 — Research a specific borrower",
  },
  {
    text: "I just spoke with Maria. She said she'll pay by Friday — it's a childcare timing issue. Log the call and update the shift notes with this. Also note that Apex Industrial needs a follow-up call this afternoon — I didn't get to them.",
    desc: "Step 3 — Log actions and flag pending work",
  },
  {
    text: "Robert Keane has a fraud signal. Pull his profile so I can review it. This needs to be escalated — flag it as urgent in the shift notes for Rob.",
    desc: "Step 4 — Investigate and escalate fraud",
  },
  {
    text: "I'm heading off shift. Save my complete handoff: I spoke with Maria (paying Friday), researched Keane's fraud flag (needs escalation), and Apex Industrial still needs their first outreach call. Rob should start with Keane's fraud case.",
    desc: "Step 5 — End-of-shift handoff for Rob",
  },
];

const ROB_SUGGESTIONS = [
  {
    text: "I'm starting my afternoon shift. Pull up John's shift notes and the activity log — I need to see what he worked on this morning before I start.",
    desc: "Step 1 — Read John's handoff context",
  },
  {
    text: "John flagged Robert Keane's fraud case as urgent. Pull up Keane's borrower profile so I can review and escalate it.",
    desc: "Step 2 — Handle urgent item from handoff",
  },
  {
    text: "John said Apex Industrial still needs their first outreach call. Pull their profile — I need to understand their situation before calling a $287K business account.",
    desc: "Step 3 — Pick up pending work John didn't finish",
  },
  {
    text: "Log everything I've done this afternoon and save my shift notes. I handled the Keane fraud escalation and called Apex Industrial. Maria Santos should pay by Friday per John's conversation — just needs a check-in if she doesn't.",
    desc: "Step 4 — Save handoff for tomorrow's shift",
  },
];

interface SuggestionPillsProps {
  onSelect: (text: string) => void;
  agentRole?: string;
}

export function SuggestionPills({ onSelect, agentRole }: SuggestionPillsProps) {
  const isJohn = agentRole !== "rob";
  const suggestions = isJohn ? JOHN_SUGGESTIONS : ROB_SUGGESTIONS;

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6">
      <div className="text-center mb-10">
        <h2 className="text-2xl font-semibold text-slate-100 tracking-tight">
          {isJohn ? "Good morning, John" : "Good afternoon, Rob"}
        </h2>
        <p className="text-sm text-slate-400 mt-2 max-w-md leading-relaxed">
          {isJohn
            ? "Work through your delinquent cases this morning. Your progress will be handed off to Rob for the afternoon shift."
            : "Read John's handoff, then pick up where he left off. Start with whatever he flagged as urgent."}
        </p>
      </div>

      <div className="w-full max-w-xl space-y-2.5">
        {suggestions.map((s, i) => (
          <button
            key={s.text}
            onClick={() => onSelect(s.text)}
            className="w-full text-left px-4 py-3 rounded-xl border border-slate-800 bg-slate-900/40 hover:bg-slate-800/60 hover:border-slate-700 transition-all group"
          >
            <div className="flex gap-3">
              <span className="text-[11px] font-bold text-slate-600 shrink-0 mt-0.5">
                {i + 1}
              </span>
              <div>
                <span className="text-[13px] text-slate-300 group-hover:text-slate-100 transition-colors leading-snug">
                  {s.text}
                </span>
                <span className="block text-[11px] text-slate-600 mt-1">
                  {s.desc}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
