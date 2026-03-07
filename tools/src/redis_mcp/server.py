"""
FinServ Agents — Financial Services MCP Server

Domain-specific tools for loan servicing agents. Portfolio data is served
from Redis (materialized from PostgreSQL) for sub-millisecond access.
Shift handoff context is stored and retrieved via Redis.

Deploy to Arcade Cloud:
  cd tools
  arcade deploy -e src/redis_mcp/server.py
"""

import json
import sys
from typing import Annotated, Optional

import redis as redis_lib

from arcade_mcp_server import Context, MCPApp

app = MCPApp(
    name="finserv_tools",
    version="0.2.0",
    instructions=(
        "Financial services tools for loan servicing agents. "
        "Use portfolio and borrower tools to review accounts. "
        "Use shift handoff tools to save and read context between agent shifts. "
        "Use activity logging to record actions taken on borrower cases."
    ),
)


def _redis(url: str) -> redis_lib.Redis:
    return redis_lib.from_url(url, decode_responses=True)


# ── Portfolio Tools (cached materialized views) ────────────────────────


@app.tool(
    name="get_portfolio_health",
    desc=(
        "Get the current portfolio health summary: active loans, total outstanding "
        "balance, DPD 30/60/90+ delinquency buckets, average credit score, and "
        "missed payments in the last 30 days. Data is pre-computed and cached "
        "in Redis for sub-millisecond access."
    ),
    requires_secrets=["REDIS_URL"],
)
def get_portfolio_health(context: Context) -> str:
    r = _redis(context.get_secret("REDIS_URL"))
    data = r.json().get("cache:portfolio_health", "$")
    if not data:
        return json.dumps({"error": "Portfolio data not yet materialized. Run the materialization job."})
    return json.dumps(data[0] if isinstance(data, list) else data, indent=2)


@app.tool(
    name="get_delinquent_accounts",
    desc=(
        "Get delinquent borrower accounts ranked by recovery likelihood score. "
        "Includes borrower details, loan info, payment consistency, and any "
        "open fraud signals. Cached in Redis from the latest PostgreSQL analysis."
    ),
    requires_secrets=["REDIS_URL"],
)
def get_delinquent_accounts(context: Context) -> str:
    r = _redis(context.get_secret("REDIS_URL"))
    data = r.json().get("cache:delinquent_accounts", "$")
    if not data:
        return json.dumps({"error": "Delinquency data not yet materialized."})
    return json.dumps(data[0] if isinstance(data, list) else data, indent=2)


@app.tool(
    name="get_borrower_profile",
    desc=(
        "Get the full 360-degree profile of a specific borrower: personal details, "
        "all loans, recent payment history, and fraud signals. Provide the borrower's "
        "name (e.g., 'Maria Santos', 'Robert Keane', 'Apex Industrial LLC')."
    ),
    requires_secrets=["REDIS_URL"],
)
def get_borrower_profile(
    context: Context,
    borrower_name: Annotated[str, "Full name of the borrower (e.g., 'Maria Santos')"],
) -> str:
    r = _redis(context.get_secret("REDIS_URL"))
    safe_name = borrower_name.lower().replace(" ", "_").replace(".", "")
    data = r.json().get(f"cache:borrower:{safe_name}", "$")
    if not data:
        return json.dumps({"error": f"Borrower '{borrower_name}' not found in cache. Available profiles are for demo characters only."})
    return json.dumps(data[0] if isinstance(data, list) else data, indent=2)


# ── Shift Handoff Tools ────────────────────────────────────────────────


@app.tool(
    name="save_shift_notes",
    desc=(
        "Save your shift handoff notes so the next CSM can pick up where you left off. "
        "Include a summary of what you worked on, which borrowers you reviewed, "
        "actions you took, items still pending, and anything urgent."
    ),
    requires_secrets=["REDIS_URL"],
)
def save_shift_notes(
    context: Context,
    agent_name: Annotated[str, "Your name (e.g., 'John' or 'Rob')"],
    shift: Annotated[str, "Your shift (e.g., 'Morning Shift' or 'Afternoon Shift')"],
    summary: Annotated[str, "Brief summary of what you worked on this shift"],
    borrowers_reviewed: Annotated[str, "JSON array of borrower names you reviewed"],
    actions_taken: Annotated[str, "JSON array of actions you completed"],
    pending_items: Annotated[str, "JSON array of items the next shift should address"],
    urgent_flags: Annotated[Optional[str], "JSON array of urgent items needing immediate attention"] = "[]",
    notes: Annotated[Optional[str], "Any additional notes for the next shift"] = "",
) -> str:
    r = _redis(context.get_secret("REDIS_URL"))

    def parse_list(s: str) -> list:
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return [item.strip() for item in s.split(",") if item.strip()]

    handoff = {
        "agent": agent_name,
        "shift": shift,
        "summary": summary,
        "borrowers_reviewed": parse_list(borrowers_reviewed),
        "actions_taken": parse_list(actions_taken),
        "pending_items": parse_list(pending_items),
        "urgent_flags": parse_list(urgent_flags),
        "notes": notes or "",
        "last_updated": __import__("datetime").datetime.now().isoformat(),
    }

    r.json().set("session:context", "$", handoff)
    return json.dumps({"saved": True, "agent": agent_name, "shift": shift})


@app.tool(
    name="get_shift_notes",
    desc=(
        "Read the previous shift's handoff notes. Shows what the other CSM "
        "worked on, which borrowers they reviewed, actions taken, and what's "
        "still pending for your shift."
    ),
    requires_secrets=["REDIS_URL"],
)
def get_shift_notes(context: Context) -> str:
    r = _redis(context.get_secret("REDIS_URL"))
    data = r.json().get("session:context", "$")
    if not data:
        return json.dumps({"message": "No shift notes found. You may be starting a fresh shift."})
    return json.dumps(data[0] if isinstance(data, list) else data, indent=2)


# ── Case Activity Log ──────────────────────────────────────────────────


@app.tool(
    name="log_case_activity",
    desc=(
        "Log an action you've taken on a borrower case. This creates an audit "
        "trail visible to all agents — emails sent, fraud flags raised, "
        "payment plans arranged, etc."
    ),
    requires_secrets=["REDIS_URL"],
)
def log_case_activity(
    context: Context,
    agent_name: Annotated[str, "Your name (e.g., 'John' or 'Rob')"],
    action: Annotated[str, "What you did (e.g., 'Sent payment reminder email')"],
    borrower: Annotated[Optional[str], "Borrower name if applicable"] = "",
    detail: Annotated[Optional[str], "Additional details"] = "",
) -> str:
    r = _redis(context.get_secret("REDIS_URL"))
    fields = {
        "agent": agent_name,
        "action": action,
    }
    if borrower:
        fields["borrower"] = borrower
    if detail:
        fields["detail"] = detail

    entry_id = r.xadd("agent:events", fields)
    return json.dumps({"logged": True, "event_id": entry_id, "action": action})


@app.tool(
    name="get_case_activity",
    desc=(
        "Read the recent case activity log — all actions taken by all agents "
        "across shifts. Shows who did what, when, and for which borrower."
    ),
    requires_secrets=["REDIS_URL"],
)
def get_case_activity(
    context: Context,
    count: Annotated[int, "Number of recent activities to retrieve"] = 20,
) -> str:
    r = _redis(context.get_secret("REDIS_URL"))
    try:
        entries = r.xrevrange("agent:events", count=count)
        result = [
            {"id": eid, "fields": fields}
            for eid, fields in entries
        ]
        return json.dumps({"activities": result, "count": len(result)}, indent=2)
    except Exception:
        return json.dumps({"activities": [], "count": 0, "message": "No activity log yet."})


# ── Entrypoint ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="0.0.0.0", port=8000)
