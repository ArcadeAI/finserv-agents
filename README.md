# FinServ Agents

AI-powered loan servicing agents demonstrating **agent shift handoff** with shared context via [Redis](https://redis.io) and governed MCP tool execution via [Arcade](https://arcade.dev).

Two CSM agents — **John** (morning shift) and **Rob** (afternoon shift) — work the same portfolio of delinquent borrowers. John researches accounts, sends outreach, and flags issues. Rob picks up where John left off, reading the shared handoff context from Redis without starting from scratch.

![Shift Handoff Demo](web/public/shift-handoff-demo.png)

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Next.js App                               │
│                                                                  │
│   ┌─────────────────┐              ┌──────────────────────┐      │
│   │   Agent Chat    │              │  Shift Handoff Panel │      │
│   │  (John or Rob)  │              │  (live Redis state)  │      │
│   └────────┬────────┘              └──────────┬───────────┘      │
│            │                                  │                  │
│      Arcade MCP Gateway                 Direct Redis read        │
│            │                           (sidecar, polling)        │
│    ┌───────┴────────┐                                            │
│    │ FinServ Tools  │ ← ngrok ← local Redis :6379               │
│    │ (governed MCP) │                                            │
│    └────────────────┘                                            │
│            │                                                     │
│   PostgreSQL :5432 (materialized into Redis cache)               │
└──────────────────────────────────────────────────────────────────┘
```

**How it works:**

1. Loan data lives in PostgreSQL (borrowers, loans, payments, fraud signals)
2. A materialization step pre-computes portfolio views and caches them in Redis
3. Agents access data through domain-specific MCP tools via Arcade (governed, audited)
4. Shift handoff context is stored in Redis and visible in the UI in real-time
5. The UI panel reads Redis directly (sidecar) for live updates

## MCP Tools

All tools are domain-specific financial services operations. No raw database primitives — the agent speaks the language of loan servicing, not Redis commands.

### Portfolio Tools (cached in Redis, materialized from PostgreSQL)

| Tool | What It Does |
|---|---|
| `get_portfolio_health` | Active loans, total outstanding, DPD 30/60/90+ buckets, credit score avg, missed payments |
| `get_delinquent_accounts` | Ranked delinquent borrowers with recovery scores and fraud cross-reference |
| `get_borrower_profile` | Full 360 view: borrower details, loans, payment history, fraud signals |

### Shift Handoff Tools (Redis-backed context)

| Tool | What It Does |
|---|---|
| `save_shift_notes` | Save shift handoff: summary, borrowers reviewed, actions taken, pending items, urgent flags |
| `get_shift_notes` | Read the previous shift's handoff notes |
| `log_case_activity` | Log an action on a borrower case (email sent, fraud flagged, payment plan arranged) |
| `get_case_activity` | Read the activity log across all shifts |

## Quick Start

### Prerequisites

- Node.js 18+, Python 3.10+, Docker, [ngrok](https://ngrok.com), [Arcade CLI](https://docs.arcade.dev)

### 1. Install

```bash
make install
```

### 2. Start PostgreSQL + Redis, seed data, materialize to Redis

```bash
make setup
```

This starts PostgreSQL and Redis in Docker, seeds loan data (500 borrowers, 800 loans, 14k+ payments), and materializes portfolio views into Redis for cached access.

### 3. Expose Redis via ngrok

```bash
ngrok tcp 6379
```

### 4. Deploy to Arcade

```bash
arcade login
arcade secret set REDIS_URL="redis://<ngrok-host>:<ngrok-port>"
make deploy
```

### 5. Create Arcade Gateway

In the [Arcade Dashboard](https://api.arcade.dev/dashboard/gateways):
1. Create a gateway
2. Add the `finserv_tools` toolkit
3. Copy the gateway URL

### 6. Configure `.env`

```bash
cp .env.example .env
```

```
ANTHROPIC_API_KEY=sk-ant-...
ARCADE_API_KEY=arc_...
ARCADE_GATEWAY_URL=https://api.arcade.dev/mcp/<your-gateway>
ARCADE_USER_ID=you@arcade.dev
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/loanops
REDIS_URL=redis://localhost:6379
```

### 7. Run

```bash
make dev
```

## Shift Handoff Demo

Open two browser tabs:

| Tab | URL | Agent |
|---|---|---|
| Morning Shift | `http://localhost:3000?agent=john` | **John** — reviews accounts, sends outreach, flags issues |
| Afternoon Shift | `http://localhost:3000?agent=rob` | **Rob** — picks up where John left off |

### Demo Flow

**John (morning):**
1. "I'm starting my shift — give me the portfolio health check"
2. "Show me the delinquent accounts I need to work on"
3. "Pull up Maria Santos' profile — I want to send her a reminder"
4. "Flag Robert Keane's account for fraud"
5. "Save my shift notes for Rob"

**Rob (afternoon):**
1. "What did John work on this morning?" (reads shift notes + activity log)
2. "Follow up on the items John left pending"
3. "Check if Maria Santos needs another touch"

The **Shift Handoff** panel on the right updates live as each agent works — showing the shared context, actions taken, and pending items.

### Demo Characters

| Name | Pattern | Outstanding | Key Detail |
|---|---|---|---|
| Maria Santos | Reliable late payer | $12,400 | Always pays 5-12 days late |
| James Chen | Occasional miss | $34,200 | One prior miss, quickly resolved |
| Apex Industrial LLC | First-ever delinquency | $287,000 | Business account, 22 DPD |
| Robert Keane | Deteriorating + fraud | $18,900 | OPEN income mismatch signal |

## Project Structure

```
finserv-agents/
├── web/                              # Next.js frontend + API routes
│   ├── src/app/                      # Pages, /api/chat, /api/redis/context
│   ├── src/components/chat/          # Chat UI
│   ├── src/components/layout/        # AppShell, Header, ContextPanel
│   └── src/lib/                      # Claude config, MCP client
├── tools/                            # MCP server (Python, arcade-mcp-server)
│   └── src/redis_mcp/server.py       # Domain-specific FinServ tools → Arcade Cloud
├── database/                         # Schema, seed data, materialization
│   ├── schema.sql
│   ├── seed_data.py
│   ├── materialize.py                # Pre-compute Postgres → Redis cache
│   └── embeddings.json
├── docker-compose.yml                # PostgreSQL + Redis 8
├── Makefile
└── .env.example
```

## Commands

| Command | Description |
|---|---|
| `make install` | Install all dependencies |
| `make setup` | Start Docker, seed Postgres, materialize to Redis |
| `make materialize` | Re-materialize Postgres views into Redis |
| `make dev` | Start Next.js dev server |
| `make deploy` | Deploy MCP server to Arcade Cloud |
| `make clean` | Tear down Docker volumes |
