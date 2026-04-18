import { NextResponse } from "next/server";
import { streamText, convertToModelMessages, stepCountIs } from "ai";
import { model, getSystemPrompt } from "@/lib/claude";
import { createArcadeMCPClient } from "@/lib/mcp-client";

export async function POST(req: Request) {
  let mcpClient: Awaited<ReturnType<typeof createArcadeMCPClient>> | null = null;
  let closed = false;

  const closeClient = async () => {
    if (!mcpClient || closed) return;
    closed = true;
    try {
      await mcpClient.close();
    } catch {}
  };

  try {
    const { messages, agentRole } = await req.json();

    mcpClient = await createArcadeMCPClient();
    const tools = await mcpClient.tools();

    const systemPrompt = getSystemPrompt(agentRole || "processing");

    const result = streamText({
      model,
      system: systemPrompt,
      messages: await convertToModelMessages(messages),
      tools,
      stopWhen: stepCountIs(10),
      onFinish: closeClient,
      onError: closeClient,
    });

    return result.toUIMessageStreamResponse();
  } catch (error) {
    await closeClient();
    const message =
      error instanceof Error ? error.message : "Failed to initialize live chat.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
