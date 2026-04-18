"""
FinServ Agents — Financial Services MCP Server

Public demo tools remain curated and business-oriented:
  - derived portfolio views are read from Redis Cloud
  - borrower drill-down is assembled via RedisVL over Redis Search
  - shift workflow state is stored directly in Redis Cloud

Deploy from repo root:
  make deploy
"""

import json
import sys
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any, Optional

import redis as redis_lib

from arcade_mcp_server import Context, MCPApp

from redis_mcp.runtime_contract import (
    CASE_ACTIVITY_STREAM_KEY,
    DELINQUENT_ACCOUNTS_KEY,
    PORTFOLIO_HEALTH_KEY,
    SHIFT_NOTES_KEY,
)
from redis_mcp.redisvl_gateway import get_redisvl_gateway

app = MCPApp(
    name="finserv_tools",
    version="0.3.0",
    instructions=(
        "Financial services tools for loan servicing agents. "
        "Use the portfolio tools for health checks, delinquent case prioritization, "
        "and borrower drill-down. Use the shift handoff and activity tools to persist "
        "cross-shift context and case actions."
    ),
)


@lru_cache(maxsize=8)
def _redis(url: str) -> redis_lib.Redis:
    return redis_lib.from_url(url, decode_responses=True)


def _read_json_key(r: redis_lib.Redis, key: str) -> dict[str, Any] | None:
    data = r.json().get(key, "$")
    if not data:
        return None
    return data[0] if isinstance(data, list) else data


def _redisvl_gateway(context: Context):
    return get_redisvl_gateway(context.get_secret("REDIS_URL"))


def _sort_payments(payments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        payments,
        key=lambda row: (
            str(row.get("due_date") or ""),
            str(row.get("created_at") or ""),
        ),
        reverse=True,
    )


def _float_or_zero(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


# ── Portfolio Tools ─────────────────────────────────────────────────────


@app.tool(
    name="get_portfolio_health",
    desc=(
        "Get the current portfolio health summary: active loans, total outstanding "
        "balance, delinquency buckets, average credit score, and missed payments "
        "in the last 30 days."
    ),
    requires_secrets=["REDIS_URL"],
)
def get_portfolio_health(context: Context) -> str:
    r = _redis(context.get_secret("REDIS_URL"))
    data = _read_json_key(r, PORTFOLIO_HEALTH_KEY)
    if not data:
        return json.dumps({"error": "Portfolio view not yet materialized. Run the setup/materialize job."})
    return json.dumps(data, indent=2)


@app.tool(
    name="get_delinquent_accounts",
    desc=(
        "Get delinquent borrower accounts ranked by recovery likelihood score. "
        "Includes borrower details, loan info, payment consistency, and any "
        "open fraud signals."
    ),
    requires_secrets=["REDIS_URL"],
)
def get_delinquent_accounts(context: Context) -> str:
    r = _redis(context.get_secret("REDIS_URL"))
    data = _read_json_key(r, DELINQUENT_ACCOUNTS_KEY)
    if not data:
        return json.dumps({"error": "Delinquency view not yet materialized. Run the setup/materialize job."})
    return json.dumps(data, indent=2)


@app.tool(
    name="get_borrower_profile",
    desc=(
        "Get the full 360-degree profile of a specific borrower: borrower details, "
        "all loans, recent payment history, and fraud signals. Provide the borrower's "
        "name (e.g., 'Maria Santos', 'Robert Keane', 'Apex Industrial LLC')."
    ),
    requires_secrets=["REDIS_URL"],
)
def get_borrower_profile(
    context: Context,
    borrower_name: Annotated[str, "Full name of the borrower (e.g., 'Maria Santos')"],
) -> str:
    gateway = _redisvl_gateway(context)
    snapshot = gateway.borrower_snapshot(borrower_name)
    borrower = snapshot["borrower"]
    if not borrower:
        return json.dumps({"error": f"Borrower '{borrower_name}' was not found in Redis."})

    borrower_id = borrower.get("borrower_id")
    if not isinstance(borrower_id, str) or not borrower_id:
        return json.dumps({"error": f"Borrower '{borrower_name}' is missing borrower_id in Redis."})

    loans = snapshot["loans"]
    payments = snapshot["payments"]
    fraud_signals = snapshot["fraud_signals"]
    recent_payments = _sort_payments(payments)[:24]

    profile = {
        "borrower": borrower,
        "loans": loans,
        "recent_payments": recent_payments,
        "fraud_signals": fraud_signals,
        "summary": {
            "total_loans": len(loans),
            "total_outstanding": sum(_float_or_zero(loan.get("outstanding_balance")) for loan in loans),
            "active_fraud_signals": sum(1 for signal in fraud_signals if signal.get("status") == "OPEN"),
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }

    return json.dumps(profile, indent=2)


# ── Shift Handoff Tools ─────────────────────────────────────────────────


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
    borrowers_reviewed: Annotated[list[str], "Borrower names you reviewed"],
    actions_taken: Annotated[list[str], "Actions you completed"],
    pending_items: Annotated[list[str], "Items the next shift should address"],
    urgent_flags: Annotated[list[str] | None, "Urgent items needing immediate attention"] = None,
    notes: Annotated[Optional[str], "Any additional notes for the next shift"] = "",
) -> str:
    r = _redis(context.get_secret("REDIS_URL"))

    handoff = {
        "agent": agent_name,
        "shift": shift,
        "summary": summary,
        "borrowers_reviewed": borrowers_reviewed,
        "actions_taken": actions_taken,
        "pending_items": pending_items,
        "urgent_flags": urgent_flags or [],
        "notes": notes or "",
        "last_updated": datetime.now(UTC).isoformat(),
    }

    r.json().set(SHIFT_NOTES_KEY, "$", handoff)
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
    data = _read_json_key(r, SHIFT_NOTES_KEY)
    if not data:
        return json.dumps({"message": "No shift notes found. You may be starting a fresh shift."})
    return json.dumps(data, indent=2)


# ── Case Activity Log ───────────────────────────────────────────────────


@app.tool(
    name="log_case_activity",
    desc=(
        "Log an action you've taken on a borrower case. This creates an audit "
        "trail visible to all agents — emails sent, fraud flags raised, "
        "payment plans arranged, and other servicing actions."
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

    entry_id = r.xadd(CASE_ACTIVITY_STREAM_KEY, fields)
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
        entries = r.xrevrange(
            CASE_ACTIVITY_STREAM_KEY,
            count=max(1, min(count, 100)),
        )
        result = [{"id": entry_id, "fields": fields} for entry_id, fields in entries]
        return json.dumps({"activities": result, "count": len(result)}, indent=2)
    except Exception:
        return json.dumps({"activities": [], "count": 0, "message": "No activity log yet."})


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="0.0.0.0", port=8000)
