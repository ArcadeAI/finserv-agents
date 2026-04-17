# FinServ Agents

A live loan-servicing demo built around **Redis**, **RedisVL**, and **Arcade**.

Two servicing agents share the same book of business:

- **John** works the morning shift
- **Rob** picks up the afternoon shift

They see the same borrower profiles, delinquency views, shift notes, and case activity in real time. Redis is the shared operational memory layer. RedisVL powers borrower search and retrieval. Arcade exposes the experience as a safe, curated MCP toolkit instead of raw database access.

![Shift Handoff Demo](web/public/shift-handoff-demo.png)

## What This Demo Shows

- A realistic **shift handoff** workflow between two agents
- A live **Redis-backed operational data plane** for both the app and the tools
- A constrained **tool-first AI workflow** through Arcade
- A simple but credible demo story: inspect portfolio health, drill into a borrower, take action, leave notes, and hand work to the next agent

## How It Works

The demo flow is straightforward:

1. **PostgreSQL** holds the source loan-servicing dataset.
2. A setup/materialization step writes that data into **Redis Cloud** as JSON documents and creates the RediSearch indices used by RedisVL.
3. **Arcade** deploys the `finserv_tools` MCP toolkit on top of that Redis data.
4. The **Next.js** app talks to Arcade, and the model uses those tools to answer questions and take workflow actions.
5. John and Rob both read and write the same live Redis state, so the handoff feels immediate.

## Components

- **PostgreSQL**
  Source system for borrowers, loans, payments, and fraud signals.

- **Redis Cloud**
  Stores:
  - borrower / loan / payment / fraud JSON documents
  - RediSearch indices defined by checked-in RedisVL schema YAML files
  - derived portfolio views
  - workflow keys for shift notes and case activity

- **RedisVL**
  Powers borrower lookup and related-record retrieval over RediSearch.

- **Arcade**
  Hosts the `finserv_tools` MCP toolkit used by the app.

- **Next.js**
  Local UI for chatting as John or Rob.

## Happy Path

If you are just trying to run the demo end to end, this is the path.

### 1. Prerequisites

You need:

- Node.js 18+
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker
- a Redis Cloud database
- an Arcade account
- an Anthropic API key

### 2. Install dependencies

```bash
make install
```

This creates `.env` from `.env.example` if needed, installs the web dependencies, and syncs the Python environments.

### 3. Fill in `.env`

At minimum, set:

```env
ANTHROPIC_API_KEY=...
ARCADE_API_KEY=...
ARCADE_USER_ID=you@example.com
REDIS_URL=rediss://default:password@redis.example.com:6380/0
```

Leave this blank until your Arcade gateway exists:

```env
ARCADE_GATEWAY_URL=
```

Notes:

- `DATABASE_URL` already defaults to the local Postgres container.
- `OPENAI_API_KEY` is optional and only used by the offline embeddings script.

### 4. Load the demo data

```bash
make setup
```

This:

- starts PostgreSQL
- applies the schema
- seeds the portfolio dataset
- writes entity data into Redis JSON
- creates the checked-in RedisVL / RediSearch indices
- rebuilds the derived Redis views
- clears old shift notes and activity for a clean run

### 5. Deploy the MCP tools to Arcade

```bash
arcade login
make deploy
```

This syncs `REDIS_URL` into Arcade secrets and deploys the toolkit from `tools/src/redis_mcp/server.py`.

Compatibility note:

- the toolkit is intentionally pinned to `redisvl==0.3.3`
- the tools runtime is pinned to `redis>=5.2.1,<6`
- `make deploy` uses the locked `tools/uv.lock` environment

### 6. Create your Arcade gateway

In the Arcade dashboard:

1. Create a gateway.
2. Attach the `finserv_tools` toolkit.
3. Copy the gateway URL into `ARCADE_GATEWAY_URL` in your local `.env`.

### 7. Start the app

```bash
make dev
```

Open:

- `http://localhost:3000?agent=john`
- `http://localhost:3000?agent=rob`

At that point the demo is live.

## Suggested Demo Flow

### John: morning shift

Try prompts like:

1. "Give me the portfolio health check."
2. "Show me the delinquent accounts I should work first."
3. "Pull up Maria Santos' profile."
4. "Log that I sent Maria a reminder."
5. "Save my shift notes for Rob."

### Rob: afternoon shift

Then switch to Rob and try:

1. "What did John work on today?"
2. "Show me the latest case activity."
3. "Follow up on the borrowers John left pending."

The right-hand panel should reflect the shared Redis state as both agents work.

## MCP Tools

The deployed toolkit exposes:

- `get_portfolio_health`
- `get_delinquent_accounts`
- `get_borrower_profile`
- `save_shift_notes`
- `get_shift_notes`
- `log_case_activity`
- `get_case_activity`

Under the hood:

- `get_borrower_profile` uses RedisVL queries over RediSearch
- portfolio summary tools read derived Redis JSON views
- handoff tools read and write Redis workflow keys directly

## Redis Layout

Main keys used by the demo:

- `finserv:borrower:{borrower_id}`
- `finserv:loan:{loan_id}`
- `finserv:payment:{payment_id}`
- `finserv:fraud_signal:{signal_id}`
- `view:portfolio_health`
- `view:delinquent_accounts`
- `workflow:shift_notes`
- `stream:case_activity`

RedisVL schema YAMLs live in `tools/src/redis_mcp/schemas/`.

## Useful Commands

| Command | What it does |
|---|---|
| `make install` | Install dependencies and create `.env` if missing |
| `make setup` | Full local bootstrap: Postgres, seed, Redis materialization |
| `make setup-indices` | Ensure the checked-in RedisVL search indices exist |
| `make materialize` | Reload entity data and rebuild Redis views |
| `make demo-reset` | Clear only shift notes and case activity |
| `make db-flush` | Drop FinServ search indices and flush the Redis DB |
| `make deploy` | Sync Arcade secrets and deploy the MCP toolkit |
| `make dev` | Start the local app |
| `make validate` | Run local validation checks |

## Troubleshooting

### Chat opens, but no tools are available

Check:

- `make deploy` completed successfully
- your Arcade gateway includes `finserv_tools`
- `ARCADE_GATEWAY_URL` points at the correct gateway

### Borrower lookups or views look stale

Run:

```bash
make materialize
```

### You want a completely fresh demo run

Run:

```bash
make db-flush
make setup
```

Warning: `make db-flush` is destructive for the Redis database selected by `REDIS_URL`.

## Project Structure

```text
finserv-agents/
├── web/                    # Next.js demo UI
├── tools/src/redis_mcp/    # MCP server and RedisVL retrieval layer
├── database/               # Schema, seed data, materialization scripts
├── docker-compose.yml      # Local PostgreSQL
├── Makefile
└── .env.example
```
