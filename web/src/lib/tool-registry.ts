import {
  Database,
  BarChart3,
  Search,
  User,
  Mail,
  FileText,
  CalendarDays,
  MessageSquare,
  ClipboardList,
  type LucideIcon,
} from "lucide-react";

export type ToolGroupId = "data" | "outreach" | "escalation";

export interface ToolMeta {
  name: string;
  displayName: string;
  description: string;
  icon: LucideIcon;
  borderColor: string;
  badgeColor: string;
  group: ToolGroupId;
}

export interface ToolGroupMeta {
  id: ToolGroupId;
  label: string;
  icon: LucideIcon;
}

export const TOOL_GROUPS: ToolGroupMeta[] = [
  { id: "data", label: "Database", icon: Database },
  { id: "outreach", label: "Google Workspace", icon: Mail },
  { id: "escalation", label: "Escalation", icon: MessageSquare },
];

export const TOOLS: ToolMeta[] = [
  {
    name: "get_portfolio_summary",
    displayName: "Portfolio Summary",
    description: "Aggregated health metrics across all loans",
    icon: Database,
    borderColor: "border-l-blue-500",
    badgeColor: "bg-blue-500/10 text-blue-400",
    group: "data",
  },
  {
    name: "analyze_delinquencies",
    displayName: "Analyze Delinquencies",
    description: "Ranked borrowers with recovery likelihood",
    icon: BarChart3,
    borderColor: "border-l-blue-500",
    badgeColor: "bg-blue-500/10 text-blue-400",
    group: "data",
  },
  {
    name: "semantic_search_recovery_patterns",
    displayName: "Recovery Search",
    description: "pgvector semantic search over past cases",
    icon: Search,
    borderColor: "border-l-blue-500",
    badgeColor: "bg-blue-500/10 text-blue-400",
    group: "data",
  },
  {
    name: "get_borrower_360",
    displayName: "Borrower 360\u00B0",
    description: "Full profile, loans, payments, fraud signals",
    icon: User,
    borderColor: "border-l-blue-500",
    badgeColor: "bg-blue-500/10 text-blue-400",
    group: "data",
  },
  {
    name: "gmail",
    displayName: "Gmail",
    description: "Send or draft personalized emails",
    icon: Mail,
    borderColor: "border-l-red-500",
    badgeColor: "bg-red-500/10 text-red-400",
    group: "outreach",
  },
  {
    name: "google_docs",
    displayName: "Google Docs",
    description: "Generate reports and briefings",
    icon: FileText,
    borderColor: "border-l-sky-500",
    badgeColor: "bg-sky-500/10 text-sky-400",
    group: "outreach",
  },
  {
    name: "google_calendar",
    displayName: "Google Calendar",
    description: "Schedule follow-up calls",
    icon: CalendarDays,
    borderColor: "border-l-amber-500",
    badgeColor: "bg-amber-500/10 text-amber-400",
    group: "outreach",
  },
  {
    name: "slack",
    displayName: "Slack",
    description: "Alert channels with incident details",
    icon: MessageSquare,
    borderColor: "border-l-purple-500",
    badgeColor: "bg-purple-500/10 text-purple-400",
    group: "escalation",
  },
  {
    name: "linear",
    displayName: "Linear",
    description: "Create review tasks and tickets",
    icon: ClipboardList,
    borderColor: "border-l-indigo-500",
    badgeColor: "bg-indigo-500/10 text-indigo-400",
    group: "escalation",
  },
];

/**
 * Match a tool name from Arcade (e.g. "LoanopsDatabase_GetPortfolioSummary")
 * to our registry by checking if the Arcade name contains our tool name keywords.
 */
export function getToolMeta(toolName: string): ToolMeta | undefined {
  const lower = toolName.toLowerCase().replace(/[_\s-]/g, "");
  return TOOLS.find((t) => {
    const key = t.name.toLowerCase().replace(/[_\s-]/g, "");
    return lower.includes(key) || key.includes(lower);
  });
}

/**
 * Get a human-readable display name for any Arcade tool name.
 */
export function getToolDisplayName(toolName: string): string {
  const meta = getToolMeta(toolName);
  if (meta) return meta.displayName;
  // Fallback: clean up the Arcade naming convention
  const parts = toolName.split("_");
  return parts[parts.length - 1]
    .replace(/([A-Z])/g, " $1")
    .trim();
}

export function getToolsByGroup(groupId: ToolGroupId): ToolMeta[] {
  return TOOLS.filter((t) => t.group === groupId);
}
