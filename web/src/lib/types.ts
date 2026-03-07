export type ToolCallStatus = "running" | "success" | "error";

export interface ToolCallData {
  id: string;
  tool: string;
  input: Record<string, unknown>;
  result?: unknown;
  status: ToolCallStatus;
  duration_ms?: number;
  error?: string;
}

export interface MockMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCallData[];
  timestamp: Date;
}

export interface ToolActivity {
  id: string;
  tool: string;
  status: ToolCallStatus;
  duration_ms?: number;
  timestamp: Date;
}
