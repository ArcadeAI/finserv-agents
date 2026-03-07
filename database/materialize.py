#!/usr/bin/env python3
"""
FinServ Agents — Materialize Postgres data into Redis

Pre-computes portfolio views from PostgreSQL and caches them in Redis
as materialized views for sub-millisecond agent access.
"""

import json
import os
from datetime import date, datetime
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor
import redis

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/loanops",
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


def json_default(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"Not serializable: {type(o)}")


def connect_pg():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)


def connect_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def materialize_portfolio_health(pg, r):
    """Portfolio-level metrics: active loans, DPD buckets, credit score, missed payments."""
    cur = pg.cursor()

    cur.execute("""
        SELECT status, COUNT(*) AS count, SUM(outstanding_balance) AS total_balance
        FROM loans WHERE status != 'PAID_OFF'
        GROUP BY status ORDER BY count DESC
    """)
    status_rows = [dict(row) for row in cur.fetchall()]

    cur.execute("""
        SELECT COUNT(*) AS active_loans,
               SUM(outstanding_balance) AS total_outstanding,
               AVG(outstanding_balance) AS avg_balance
        FROM loans WHERE status != 'PAID_OFF'
    """)
    overall = dict(cur.fetchone())

    cur.execute("""
        SELECT AVG(b.credit_score) AS avg_credit_score
        FROM borrowers b JOIN loans l ON b.borrower_id = l.borrower_id
        WHERE l.status != 'PAID_OFF'
    """)
    credit = dict(cur.fetchone())

    cur.execute("""
        SELECT COUNT(*) AS missed_count FROM payments
        WHERE status IN ('MISSED', 'LATE')
          AND due_date >= CURRENT_DATE - INTERVAL '30 days'
    """)
    missed = dict(cur.fetchone())

    data = {
        "active_loans": overall["active_loans"],
        "total_outstanding": overall["total_outstanding"],
        "avg_balance": overall["avg_balance"],
        "avg_credit_score": round(credit["avg_credit_score"]) if credit["avg_credit_score"] else 0,
        "missed_payments_30d": missed["missed_count"],
        "status_breakdown": {
            row["status"]: {"count": row["count"], "total_balance": row["total_balance"]}
            for row in status_rows
        },
        "materialized_at": datetime.now().isoformat(),
    }

    clean = json.loads(json.dumps(data, default=json_default))
    r.json().set("cache:portfolio_health", "$", clean)
    r.expire("cache:portfolio_health", 3600)
    print(f"  Materialized portfolio_health ({data['active_loans']} active loans)")


def materialize_delinquent_accounts(pg, r):
    """Ranked delinquent borrowers with recovery scores and fraud signals."""
    cur = pg.cursor()

    cur.execute("""
        WITH payment_stats AS (
            SELECT p.borrower_id, p.loan_id,
                COUNT(*) FILTER (WHERE p.status = 'PAID') AS paid_count,
                COUNT(*) FILTER (WHERE p.status IN ('LATE', 'MISSED')) AS delinquent_count,
                COUNT(*) AS total_payments,
                MAX(p.days_past_due) AS max_dpd,
                AVG(CASE WHEN p.status = 'LATE' THEN p.days_past_due ELSE 0 END) AS avg_late_days
            FROM payments p GROUP BY p.borrower_id, p.loan_id
        )
        SELECT b.full_name, b.email, b.borrower_type, b.credit_score,
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
        LEFT JOIN payment_stats ps ON l.loan_id = ps.loan_id AND l.borrower_id = ps.borrower_id
        WHERE l.status IN ('DELINQUENT_30', 'DELINQUENT_60', 'DELINQUENT_90', 'DEFAULT')
        ORDER BY recovery_score DESC
        LIMIT 20
    """)
    accounts = [dict(row) for row in cur.fetchall()]

    if accounts:
        names = [a["full_name"] for a in accounts]
        cur.execute("""
            SELECT b.full_name, fs.signal_type, fs.severity, fs.status AS signal_status
            FROM fraud_signals fs
            JOIN borrowers b ON fs.borrower_id = b.borrower_id
            WHERE fs.status = 'OPEN' AND b.full_name = ANY(%s)
        """, (names,))
        fraud_map = {}
        for row in cur.fetchall():
            fraud_map[row["full_name"]] = dict(row)
        for acct in accounts:
            acct["fraud_signal"] = fraud_map.get(acct["full_name"])

    data = {
        "accounts": accounts,
        "total_delinquent": len(accounts),
        "materialized_at": datetime.now().isoformat(),
    }

    clean = json.loads(json.dumps(data, default=json_default))
    r.json().set("cache:delinquent_accounts", "$", clean)
    r.expire("cache:delinquent_accounts", 3600)
    print(f"  Materialized delinquent_accounts ({len(accounts)} accounts)")


def materialize_borrower_profiles(pg, r):
    """Individual borrower profiles for the 4 demo characters."""
    cur = pg.cursor()
    demo_names = ["Maria Santos", "James Chen", "Apex Industrial LLC", "Robert Keane"]

    for name in demo_names:
        cur.execute("SELECT * FROM borrowers WHERE full_name = %s LIMIT 1", (name,))
        borrower = cur.fetchone()
        if not borrower:
            continue
        borrower = dict(borrower)
        bid = borrower["borrower_id"]

        cur.execute("SELECT * FROM loans WHERE borrower_id = %s ORDER BY originated_at DESC", (bid,))
        loans = [dict(row) for row in cur.fetchall()]

        cur.execute("""
            SELECT amount, due_date, paid_date, status, days_past_due, payment_method
            FROM payments WHERE borrower_id = %s AND due_date >= CURRENT_DATE - INTERVAL '12 months'
            ORDER BY due_date DESC LIMIT 24
        """, (bid,))
        payments = [dict(row) for row in cur.fetchall()]

        cur.execute("SELECT * FROM fraud_signals WHERE borrower_id = %s ORDER BY detected_at DESC", (bid,))
        fraud = [dict(row) for row in cur.fetchall()]

        profile = {
            "borrower": borrower,
            "loans": loans,
            "recent_payments": payments,
            "fraud_signals": fraud,
            "summary": {
                "total_loans": len(loans),
                "total_outstanding": sum(float(l["outstanding_balance"] or 0) for l in loans),
                "active_fraud_signals": sum(1 for f in fraud if f["status"] == "OPEN"),
            },
            "materialized_at": datetime.now().isoformat(),
        }

        safe_name = name.lower().replace(" ", "_").replace(".", "")
        r.json().set(f"cache:borrower:{safe_name}", "$", json.loads(json.dumps(profile, default=json_default)))
        r.expire(f"cache:borrower:{safe_name}", 3600)
        print(f"  Materialized borrower profile: {name}")


def main():
    print("Connecting to PostgreSQL...")
    pg = connect_pg()
    print("Connecting to Redis...")
    r = connect_redis()
    r.ping()
    print("Connected.\n")

    print("Materializing portfolio health...")
    materialize_portfolio_health(pg, r)

    print("Materializing delinquent accounts...")
    materialize_delinquent_accounts(pg, r)

    print("Materializing borrower profiles...")
    materialize_borrower_profiles(pg, r)

    pg.close()
    print("\nMaterialization complete!")
    print(f"  Redis keys: {r.keys('cache:*')}")


if __name__ == "__main__":
    main()
