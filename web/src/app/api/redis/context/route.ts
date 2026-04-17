import { NextResponse } from "next/server";
import Redis from "ioredis";

// Keep these two UI-only keys aligned with tools/src/redis_mcp/runtime_contract.py.
const SHIFT_NOTES_KEY = "workflow:shift_notes";
const CASE_ACTIVITY_STREAM_KEY = "stream:case_activity";

const redisUrl = process.env.REDIS_URL;
const redis = redisUrl
  ? new Redis(redisUrl, {
      maxRetriesPerRequest: 1,
      lazyConnect: true,
    })
  : null;

let connectPromise: Promise<void> | null = null;

redis?.on("end", () => {
  connectPromise = null;
});

redis?.on("error", () => {
  // The route returns a graceful empty payload when Redis is unavailable.
});

function emptyContextResponse(error?: string) {
  return NextResponse.json({
    context: null,
    events: [],
    ...(error ? { error } : {}),
  });
}

async function ensureConnected() {
  if (!redis) {
    throw new Error("REDIS_URL is not configured");
  }
  if (redis.status === "ready") return;

  if (!connectPromise) {
    connectPromise = redis.connect().catch((error: unknown) => {
      connectPromise = null;
      throw error;
    });
  }

  await connectPromise;
}

export async function GET() {
  try {
    await ensureConnected();
    const client = redis;
    if (!client) {
      throw new Error("REDIS_URL is not configured");
    }

    // Read shift handoff context from Redis JSON.
    let context = null;
    try {
      const raw = await client.call("JSON.GET", SHIFT_NOTES_KEY, "$") as string | null;
      if (raw) {
        const parsed = JSON.parse(raw);
        context = Array.isArray(parsed) ? parsed[0] : parsed;
      }
    } catch {
      const raw = await client.get(SHIFT_NOTES_KEY);
      if (raw) {
        try { context = JSON.parse(raw); } catch { context = raw; }
      }
    }

    // Read activity stream (last 20 entries).
    let events: { id: string; fields: Record<string, string> }[] = [];
    try {
      const entries = await client.xrevrange(
        CASE_ACTIVITY_STREAM_KEY,
        "+",
        "-",
        "COUNT",
        20
      );
      events = entries.map(([id, fields]) => {
        const obj: Record<string, string> = {};
        for (let i = 0; i < fields.length; i += 2) {
          obj[fields[i]] = fields[i + 1];
        }
        return { id, fields: obj };
      });
    } catch {
      // Stream doesn't exist yet
    }

    return NextResponse.json({
      context,
      events,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return emptyContextResponse(message);
  }
}
