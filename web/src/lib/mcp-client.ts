import { createMCPClient } from "@ai-sdk/mcp";

/**
 * Create an MCP client connected to the Arcade MCP Gateway.
 * Uses @ai-sdk/mcp which handles StreamableHTTP transport.
 */
export async function createArcadeMCPClient() {
  const gatewayUrl = process.env.ARCADE_GATEWAY_URL;
  const apiKey = process.env.ARCADE_API_KEY;
  const userId = process.env.ARCADE_USER_ID;

  if (!gatewayUrl) throw new Error("ARCADE_GATEWAY_URL is not set");
  if (!apiKey) throw new Error("ARCADE_API_KEY is not set");
  if (!userId) throw new Error("ARCADE_USER_ID is not set — use a stable identifier for the Arcade user context");

  const client = await createMCPClient({
    transport: {
      type: "http",
      url: gatewayUrl,
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Arcade-User-Id": userId,
      },
    },
  });

  return client;
}
