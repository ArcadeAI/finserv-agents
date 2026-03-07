import { NextResponse } from "next/server";
import Redis from "ioredis";

const redis = new Redis(process.env.REDIS_URL || "redis://localhost:6379", {
  maxRetriesPerRequest: 1,
  lazyConnect: true,
});

let connected = false;
async function ensureConnected() {
  if (!connected) {
    try {
      await redis.connect();
      connected = true;
    } catch {
      // already connected or failed
      connected = true;
    }
  }
}

export async function GET() {
  try {
    await ensureConnected();

    // Read session context (Redis JSON stored as string by the MCP tools)
    let context = null;
    try {
      const raw = await redis.call("JSON.GET", "session:context", "$") as string | null;
      if (raw) {
        const parsed = JSON.parse(raw);
        context = Array.isArray(parsed) ? parsed[0] : parsed;
      }
    } catch {
      // Key doesn't exist or not a JSON key — try plain string
      const raw = await redis.get("session:context");
      if (raw) {
        try { context = JSON.parse(raw); } catch { context = raw; }
      }
    }

    // Read event stream (last 20 entries)
    let events: { id: string; fields: Record<string, string> }[] = [];
    try {
      const entries = await redis.xrevrange("agent:events", "+", "-", "COUNT", 20);
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

    let sessionKeys: string[] = [];
    try {
      const sKeys = await redis.keys("session:*");
      const cKeys = await redis.keys("cache:*");
      sessionKeys = [...sKeys, ...cKeys].sort();
    } catch {
      // ignore
    }

    return NextResponse.json({
      context,
      events,
      sessionKeys,
      timestamp: new Date().toISOString(),
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { context: null, events: [], sessionKeys: [], error: message, timestamp: new Date().toISOString() },
      { status: 200 }
    );
  }
}
