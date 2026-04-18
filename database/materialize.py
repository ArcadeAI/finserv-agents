#!/usr/bin/env python3
"""
FinServ materialization entrypoint.

Runs the full live data prep flow end to end:
1. Load structured borrower, loan, payment, and fraud records from PostgreSQL.
2. Upsert the same JSON documents into Redis under the existing key layout.
3. Ensure RedisVL-managed RediSearch indices exist for each entity namespace.
4. Rebuild the curated Redis view keys used by the demo's summary tools.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
import redis
from redisvl.index import SearchIndex

from redis_mcp.indexing import (
    BORROWER_ENTITY,
    FRAUD_SIGNAL_ENTITY,
    LOAN_ENTITY,
    PAYMENT_ENTITY,
    entity_key,
    index_spec,
    schema_path,
)
from runtime_config import (
    CASE_ACTIVITY_STREAM_KEY,
    DELINQUENT_ACCOUNTS_KEY,
    PORTFOLIO_HEALTH_KEY,
    SHIFT_NOTES_KEY,
    get_runtime_config,
)

BATCH_SIZE = 1000
SEED_NAMESPACE = uuid.UUID("8e7e9951-d2e3-4b88-95ac-e6c18cd1dfe1")
DEMO_NAMES = ["Maria Santos", "James Chen", "Apex Industrial LLC", "Robert Keane"]

psycopg2.extras.register_uuid()


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def stable_uuid(*parts: object) -> uuid.UUID:
    key = "::".join(str(part) for part in parts)
    return uuid.uuid5(SEED_NAMESPACE, key)


def json_default(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Not serializable: {type(value)}")


def connect_pg():
    settings = get_runtime_config()
    return psycopg2.connect(settings.database_url, cursor_factory=RealDictCursor)


def connect_redis():
    settings = get_runtime_config()
    return redis.from_url(settings.redis_url, decode_responses=True)


def _write_json_key(r, key: str, payload: dict[str, object]) -> None:
    clean = json.loads(json.dumps(payload, default=json_default))
    r.json().set(key, "$", clean)


def reset_demo_workflow_state(r) -> None:
    deleted = r.delete(SHIFT_NOTES_KEY, CASE_ACTIVITY_STREAM_KEY)
    print(
        "  Cleared demo workflow state "
        f"({deleted} key{'s' if deleted != 1 else ''} removed)"
    )


def load_borrowers(pg) -> list[dict[str, Any]]:
    with pg.cursor() as cur:
        cur.execute(
            """
            SELECT borrower_id, full_name, email, phone, borrower_type, company_name,
                   stated_income, credit_score, risk_tier, country, state, onboarded_at
            FROM borrowers
            ORDER BY full_name, borrower_id
        """
        )
        rows = cur.fetchall()

    return [
        {
            "borrower_id": str(row["borrower_id"]),
            "full_name": row["full_name"],
            "email": row["email"],
            "phone": row["phone"],
            "borrower_type": row["borrower_type"],
            "company_name": row["company_name"],
            "stated_income": _as_float(row["stated_income"]),
            "credit_score": _as_int(row["credit_score"]),
            "risk_tier": row["risk_tier"],
            "country": row["country"],
            "state": row["state"],
            "onboarded_at": _as_str(row["onboarded_at"]),
        }
        for row in rows
    ]


def load_loans(pg) -> list[dict[str, Any]]:
    with pg.cursor() as cur:
        cur.execute(
            """
            SELECT loan_id, borrower_id, loan_type, principal, interest_rate, term_months,
                   monthly_payment, outstanding_balance, status, originated_at, maturity_date
            FROM loans
            ORDER BY loan_id
        """
        )
        rows = cur.fetchall()

    return [
        {
            "loan_id": str(row["loan_id"]),
            "borrower_id": str(row["borrower_id"]),
            "loan_type": row["loan_type"],
            "principal": _as_float(row["principal"]),
            "interest_rate": _as_float(row["interest_rate"]),
            "term_months": _as_int(row["term_months"]),
            "monthly_payment": _as_float(row["monthly_payment"]),
            "outstanding_balance": _as_float(row["outstanding_balance"]),
            "status": row["status"],
            "originated_at": _as_str(row["originated_at"]),
            "maturity_date": _as_str(row["maturity_date"]),
        }
        for row in rows
    ]


def load_payments(pg) -> list[dict[str, Any]]:
    with pg.cursor() as cur:
        cur.execute(
            """
            SELECT payment_id, loan_id, borrower_id, amount, due_date, paid_date,
                   status, days_past_due, payment_method, created_at
            FROM payments
            ORDER BY payment_id
        """
        )
        rows = cur.fetchall()

    return [
        {
            "payment_id": str(row["payment_id"]),
            "loan_id": str(row["loan_id"]),
            "borrower_id": str(row["borrower_id"]),
            "amount": _as_float(row["amount"]),
            "due_date": _as_str(row["due_date"]),
            "paid_date": _as_str(row["paid_date"]),
            "status": row["status"],
            "days_past_due": _as_int(row["days_past_due"]),
            "payment_method": row["payment_method"],
            "created_at": _as_str(row["created_at"]),
        }
        for row in rows
    ]


def load_fraud_signals(pg) -> list[dict[str, Any]]:
    with pg.cursor() as cur:
        cur.execute(
            """
            SELECT signal_id, borrower_id, loan_id, signal_type, severity,
                   details, detected_at, status
            FROM fraud_signals
            ORDER BY signal_id
        """
        )
        rows = cur.fetchall()

    return [
        {
            "signal_id": str(row["signal_id"]),
            "borrower_id": str(row["borrower_id"]),
            "loan_id": str(row["loan_id"]) if row["loan_id"] else None,
            "signal_type": row["signal_type"],
            "severity": row["severity"],
            "details": row["details"],
            "detected_at": _as_str(row["detected_at"]),
            "status": row["status"],
        }
        for row in rows
    ]


def _entity_keys(entity: str, records: Sequence[dict[str, Any]]) -> list[str]:
    spec = index_spec(entity)
    return [entity_key(entity, str(record[spec.id_field])) for record in records]


def _delete_stale_entity_keys(
    r,
    entity: str,
    live_keys: set[str],
) -> int:
    spec = index_spec(entity)
    stale_keys: list[str] = []
    deleted = 0

    for key in r.scan_iter(match=f"{spec.redis_key_prefix}*", count=1000):
        if key not in live_keys:
            stale_keys.append(key)
            if len(stale_keys) >= BATCH_SIZE:
                deleted += r.delete(*stale_keys)
                stale_keys.clear()

    if stale_keys:
        deleted += r.delete(*stale_keys)

    return deleted


def _upsert_entity_records(
    r,
    entity: str,
    records: list[dict[str, Any]],
) -> None:
    index = SearchIndex.from_yaml(
        str(schema_path(entity)),
        redis_client=r,
        validate_on_load=True,
    )
    index.create(overwrite=False)

    keys = _entity_keys(entity, records)
    index.load(records, keys=keys, batch_size=BATCH_SIZE)
    deleted = _delete_stale_entity_keys(r, entity, set(keys))

    spec = index_spec(entity)
    print(
        f"  Upserted {len(keys)} {entity} records into {index.name} "
        f"({spec.key_prefix}:*)"
    )
    if deleted:
        print(f"    Removed {deleted} stale {entity} key{'s' if deleted != 1 else ''}")


def materialize_entity_data() -> None:
    print("Connecting to PostgreSQL...")
    pg = connect_pg()
    print("Connecting to Redis...")
    r = connect_redis()
    r.ping()
    print("Connected.\n")

    print("Loading entity records from PostgreSQL...")
    borrowers = load_borrowers(pg)
    loans = load_loans(pg)
    payments = load_payments(pg)
    fraud_signals = load_fraud_signals(pg)
    pg.close()

    print("Upserting entity documents into Redis...")
    _upsert_entity_records(r, BORROWER_ENTITY, borrowers)
    _upsert_entity_records(r, LOAN_ENTITY, loans)
    _upsert_entity_records(r, PAYMENT_ENTITY, payments)
    _upsert_entity_records(r, FRAUD_SIGNAL_ENTITY, fraud_signals)

    print("\nRedis entity materialization complete.")


def materialize_portfolio_health(pg, r) -> None:
    cur = pg.cursor()

    cur.execute(
        """
        SELECT status, COUNT(*) AS count, SUM(outstanding_balance) AS total_balance
        FROM loans
        WHERE status != 'PAID_OFF'
        GROUP BY status
        ORDER BY count DESC
    """
    )
    status_rows = [dict(row) for row in cur.fetchall()]

    cur.execute(
        """
        SELECT COUNT(*) AS active_loans,
               SUM(outstanding_balance) AS total_outstanding,
               AVG(outstanding_balance) AS avg_balance
        FROM loans
        WHERE status != 'PAID_OFF'
    """
    )
    overall = dict(cur.fetchone())

    cur.execute(
        """
        SELECT AVG(b.credit_score) AS avg_credit_score
        FROM borrowers b
        JOIN loans l ON b.borrower_id = l.borrower_id
        WHERE l.status != 'PAID_OFF'
    """
    )
    credit = dict(cur.fetchone())

    cur.execute(
        """
        SELECT COUNT(*) AS missed_count
        FROM payments
        WHERE status IN ('MISSED', 'LATE')
          AND due_date >= CURRENT_DATE - INTERVAL '30 days'
    """
    )
    missed = dict(cur.fetchone())

    payload = {
        "active_loans": overall["active_loans"],
        "total_outstanding": overall["total_outstanding"],
        "avg_balance": overall["avg_balance"],
        "avg_credit_score": round(credit["avg_credit_score"]) if credit["avg_credit_score"] else 0,
        "missed_payments_30d": missed["missed_count"],
        "status_breakdown": {
            row["status"]: {"count": row["count"], "total_balance": row["total_balance"]}
            for row in status_rows
        },
        "materialized_at": datetime.now(UTC).isoformat(),
    }

    _write_json_key(r, PORTFOLIO_HEALTH_KEY, payload)
    print(f"  Materialized {PORTFOLIO_HEALTH_KEY}")


def materialize_delinquent_accounts(pg, r) -> None:
    cur = pg.cursor()
    demo_borrower_ids = [stable_uuid("borrower", "demo", name) for name in DEMO_NAMES]

    cur.execute(
        """
        SELECT COUNT(*) AS total_delinquent
        FROM loans
        WHERE status IN ('DELINQUENT_30', 'DELINQUENT_60', 'DELINQUENT_90', 'DEFAULT')
    """
    )
    total_delinquent = cur.fetchone()["total_delinquent"]

    cur.execute(
        """
        WITH payment_stats AS (
            SELECT p.borrower_id, p.loan_id,
                COUNT(*) FILTER (WHERE p.status = 'PAID') AS paid_count,
                COUNT(*) FILTER (WHERE p.status IN ('LATE', 'MISSED')) AS delinquent_count,
                COUNT(*) AS total_payments,
                MAX(p.days_past_due) AS max_dpd
            FROM payments p
            GROUP BY p.borrower_id, p.loan_id
        )
        SELECT b.borrower_id, b.full_name, b.email, b.borrower_type, b.credit_score,
            l.loan_type, l.outstanding_balance, l.status AS loan_status,
            ps.paid_count, ps.delinquent_count, ps.max_dpd,
            CASE WHEN ps.total_payments > 0
                 THEN ROUND(ps.paid_count::numeric / ps.total_payments * 100, 1)
                 ELSE 0 END AS payment_consistency_pct,
            CASE WHEN ps.total_payments > 0
                 THEN ROUND(
                    (ps.paid_count::numeric / ps.total_payments * 70) +
                    (LEAST(b.credit_score, 850)::numeric / 850 * 30), 1)
                 ELSE 0 END AS recovery_score
        FROM loans l
        JOIN borrowers b ON l.borrower_id = b.borrower_id
        LEFT JOIN payment_stats ps
               ON l.loan_id = ps.loan_id AND l.borrower_id = ps.borrower_id
        WHERE l.status IN ('DELINQUENT_30', 'DELINQUENT_60', 'DELINQUENT_90', 'DEFAULT')
          AND b.borrower_id = ANY(%s)
        ORDER BY recovery_score DESC
    """,
        (demo_borrower_ids,),
    )
    accounts = [dict(row) for row in cur.fetchall()]

    if accounts:
        borrower_ids = [account["borrower_id"] for account in accounts]
        cur.execute(
            """
            SELECT borrower_id, signal_type, severity, status AS signal_status
            FROM fraud_signals
            WHERE status = 'OPEN'
              AND borrower_id = ANY(%s)
        """,
            (borrower_ids,),
        )
        fraud_map = {}
        for row in cur.fetchall():
            fraud_map[row["borrower_id"]] = dict(row)

        for account in accounts:
            account["fraud_signal"] = fraud_map.get(account["borrower_id"])

    payload = {
        "accounts": accounts,
        "visible_accounts": len(accounts),
        "total_delinquent": total_delinquent,
        "materialized_at": datetime.now(UTC).isoformat(),
    }

    _write_json_key(r, DELINQUENT_ACCOUNTS_KEY, payload)
    print(f"  Materialized {DELINQUENT_ACCOUNTS_KEY}")


def materialize_views() -> None:
    print("Connecting to PostgreSQL...")
    pg = connect_pg()
    print("Connecting to Redis...")
    r = connect_redis()
    r.ping()
    print("Connected.\n")

    print("Resetting demo workflow state...")
    reset_demo_workflow_state(r)

    print("Materializing portfolio health...")
    materialize_portfolio_health(pg, r)

    print("Materializing delinquent accounts...")
    materialize_delinquent_accounts(pg, r)

    pg.close()
    print("\nDerived view materialization complete!")


def main() -> None:
    print("Materializing FinServ live data...")
    print("")
    materialize_entity_data()
    print("")
    print("Building derived Redis views...")
    materialize_views()


if __name__ == "__main__":
    main()
