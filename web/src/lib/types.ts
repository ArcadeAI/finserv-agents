export type ToolCallStatus = "running" | "success" | "error";

export interface ToolCallData {
  id: string;
  tool: string;
  input: Record<string, unknown>;
  result?: unknown;
  status: ToolCallStatus;
  error?: string;
}
