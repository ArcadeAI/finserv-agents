import { streamText, convertToModelMessages, stepCountIs } from "ai";
import { model, getSystemPrompt } from "@/lib/claude";
import { createArcadeMCPClient } from "@/lib/mcp-client";

export async function POST(req: Request) {
  const { messages, agentRole } = await req.json();

  const mcpClient = await createArcadeMCPClient();
  const tools = await mcpClient.tools();

  const systemPrompt = getSystemPrompt(agentRole || "processing");

  const result = streamText({
    model,
    system: systemPrompt,
    messages: await convertToModelMessages(messages),
    tools,
    stopWhen: stepCountIs(10),
    onFinish: async () => {
      await mcpClient.close();
    },
    onError: async () => {
      await mcpClient.close();
    },
  });

  return result.toUIMessageStreamResponse();
}
