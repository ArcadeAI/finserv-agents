import {
  BarChart3,
  ClipboardList,
  BookMarked,
  MessageSquare,
  type LucideIcon,
  User,
} from "lucide-react";

export interface ToolMeta {
  name: string;
  displayName: string;
  icon: LucideIcon;
  borderColor: string;
}

export const TOOLS: ToolMeta[] = [
  {
    name: "get_portfolio_health",
    displayName: "Portfolio Health",
    icon: BarChart3,
    borderColor: "border-l-blue-500",
  },
  {
    name: "get_delinquent_accounts",
    displayName: "Delinquent Accounts",
    icon: BarChart3,
    borderColor: "border-l-blue-500",
  },
  {
    name: "get_borrower_profile",
    displayName: "Borrower Profile",
    icon: User,
    borderColor: "border-l-blue-500",
  },
  {
    name: "save_shift_notes",
    displayName: "Save Shift Notes",
    icon: BookMarked,
    borderColor: "border-l-amber-500",
  },
  {
    name: "get_shift_notes",
    displayName: "Get Shift Notes",
    icon: BookMarked,
    borderColor: "border-l-amber-500",
  },
  {
    name: "log_case_activity",
    displayName: "Log Case Activity",
    icon: MessageSquare,
    borderColor: "border-l-emerald-500",
  },
  {
    name: "get_case_activity",
    displayName: "Get Case Activity",
    icon: ClipboardList,
    borderColor: "border-l-emerald-500",
  },
];

/**
 * Match a tool name from Arcade to our registry by checking if it contains the
 * normalized internal tool name.
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
  return toolName
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .trim();
}
