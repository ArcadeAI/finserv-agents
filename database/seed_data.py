#!/usr/bin/env python3
"""
FinServ Agents — Seed Data Generator

Generates realistic loan portfolio data for PostgreSQL:
  - 500 borrowers (70% individual, 30% business)
  - 800 loans across types
  - 50,000+ payments spanning 24 months
  - 4 named demo characters for reliable demo playback
  - 100 recovery narratives
  - 15 fraud signals
"""

import json
import os
import uuid
import random
from datetime import date, timedelta, datetime
from decimal import Decimal

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values
from faker import Faker

# Register UUID adapter so psycopg2 can handle uuid.UUID objects
psycopg2.extras.register_uuid()

fake = Faker()
Faker.seed(42)
random.seed(42)

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/loanops",
)

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

LOAN_TYPES = ["PERSONAL", "MORTGAGE", "AUTO", "BUSINESS", "LINE_OF_CREDIT"]
PAYMENT_METHODS = ["ACH", "WIRE", "CHECK", "AUTO_DEBIT"]

# ── Named demo characters ──────────────────────────────────────────────

DEMO_CHARACTERS = [
    {
        "full_name": "Maria Santos",
        "email": "maria.santos@email.com",
        "phone": "(555) 234-5678",
        "borrower_type": "INDIVIDUAL",
        "company_name": None,
        "stated_income": 72000,
        "credit_score": 695,
        "risk_tier": "NEAR_PRIME",
        "state": "TX",
        "loan_type": "PERSONAL",
        "principal": 15000,
        "interest_rate": 8.5,
        "term_months": 36,
        "monthly_payment": 473.51,
        "outstanding_balance": 12400,
        "status": "DELINQUENT_30",
        "pattern": "reliable_late",  # Always pays 5-12 days late
    },
    {
        "full_name": "James Chen",
        "email": "james.chen@email.com",
        "phone": "(555) 345-6789",
        "borrower_type": "INDIVIDUAL",
        "company_name": None,
        "stated_income": 95000,
        "credit_score": 720,
        "risk_tier": "PRIME",
        "state": "CA",
        "loan_type": "AUTO",
        "principal": 42000,
        "interest_rate": 5.2,
        "term_months": 60,
        "monthly_payment": 795.33,
        "outstanding_balance": 34200,
        "status": "DELINQUENT_30",
        "pattern": "occasional_miss",  # Misses one, catches up
    },
    {
        "full_name": "Apex Industrial LLC",
        "email": "accounts@apexindustrial.com",
        "phone": "(555) 456-7890",
        "borrower_type": "BUSINESS",
        "company_name": "Apex Industrial LLC",
        "stated_income": 2400000,
        "credit_score": 740,
        "risk_tier": "PRIME",
        "state": "OH",
        "loan_type": "BUSINESS",
        "principal": 350000,
        "interest_rate": 6.8,
        "term_months": 84,
        "monthly_payment": 5470.12,
        "outstanding_balance": 287000,
        "status": "DELINQUENT_30",
        "pattern": "first_delinquency",  # First-ever miss at 22 DPD
    },
    {
        "full_name": "Robert Keane",
        "email": "robert.keane@email.com",
        "phone": "(555) 567-8901",
        "borrower_type": "INDIVIDUAL",
        "company_name": None,
        "stated_income": 110000,
        "credit_score": 640,
        "risk_tier": "SUBPRIME",
        "state": "FL",
        "loan_type": "PERSONAL",
        "principal": 25000,
        "interest_rate": 12.5,
        "term_months": 48,
        "monthly_payment": 665.82,
        "outstanding_balance": 18900,
        "status": "DELINQUENT_60",
        "pattern": "deteriorating",  # 3rd miss in 6 months + fraud signal
    },
]

# ── Recovery narrative templates ────────────────────────────────────────

RECOVERY_NARRATIVES = [
    "Borrower lost job due to company downsizing. Entered 3-month forbearance. {method} outreach after 45 days. Secured new employment and resumed payments. Full recovery in {days} days.",
    "Medical emergency caused 60-day delinquency. {method} outreach expressing empathy and offering hardship program. Borrower enrolled in modified payment plan. {outcome} after {days} days.",
    "Small business seasonal cash flow issue. Borrower proactively communicated. {method} to discuss restructuring options. Temporary interest-only payments for 6 months. Recovered in {days} days.",
    "Borrower forgot to update auto-debit after bank change. Simple oversight. {method} resolved immediately. Payment received within {days} days of contact.",
    "Divorce proceedings caused financial disruption. {method} outreach with sensitivity. Offered payment deferral for 2 months. Borrower {outcome} after {days} days of resolution process.",
    "Borrower relocated for work, payments slipped during transition. {method} outreach. Updated payment details and caught up within {days} days.",
    "Identity theft victim — fraudulent charges disrupted cash flow. {method} outreach, connected with fraud team. Cleared within {days} days, payments resumed.",
    "Business borrower lost major client (30% of revenue). {method} discussion about restructuring. Converted to interest-only for 12 months. {outcome} after {days} days.",
    "Borrower hospitalized for extended period. Family member contacted via {method}. Entered hardship forbearance. Resumed payments after {days} days.",
    "Tax lien caused temporary cash freeze. {method} outreach explaining options. Borrower resolved lien and resumed payments within {days} days.",
    "Seasonal worker with predictable income gaps. {method} to establish seasonal payment adjustment. Pattern resolved through structured skip-payment months. {outcome} in {days} days.",
    "Borrower experienced natural disaster damage to property. {method} outreach with FEMA assistance info. Insurance proceeds applied to catch up in {days} days.",
    "Student loan borrower overwhelmed by multiple payments. {method} outreach offering consolidation advice. Restructured payment schedule. {outcome} after {days} days.",
    "Business borrower's AR collections delayed by 60 days. {method} outreach. Provided bridge forbearance. Full catch-up once receivables cleared in {days} days.",
    "Borrower disputed charges on account. {method} resolution process initiated. Dispute resolved, payments resumed within {days} days.",
]

OUTREACH_METHODS = ["Email", "Phone call", "SMS followed by phone call", "Certified letter", "In-person meeting"]
OUTCOMES = ["RECOVERED", "DEFAULT", "RESTRUCTURED", "SETTLED"]
DELINQUENCY_PATTERNS = [
    "reliable_late_payer", "occasional_miss", "seasonal_gap",
    "sudden_hardship", "gradual_deterioration", "one_time_oversight",
    "business_cash_flow", "medical_emergency", "job_loss",
    "fraud_victim", "divorce_disruption",
]


def connect():
    return psycopg2.connect(DB_URL)


def generate_borrowers(conn, count=496):
    """Generate random borrowers + 4 demo characters = 500 total."""
    borrowers = []
    # Demo characters first
    for char in DEMO_CHARACTERS:
        bid = uuid.uuid4()
        char["_id"] = bid
        borrowers.append((
            bid,
            char["full_name"],
            char["email"],
            char["phone"],
            char["borrower_type"],
            char["company_name"],
            char["stated_income"],
            char["credit_score"],
            char["risk_tier"],
            "US",
            char["state"],
            date(2024, 1, 15),
        ))

    # Random borrowers
    for _ in range(count):
        is_business = random.random() < 0.3
        credit = random.gauss(700, 60)
        credit = max(550, min(850, int(credit)))
        if credit >= 720:
            tier = "PRIME"
        elif credit >= 660:
            tier = "NEAR_PRIME"
        else:
            tier = "SUBPRIME"

        borrowers.append((
            uuid.uuid4(),
            fake.company() if is_business else fake.name(),
            fake.company_email() if is_business else fake.email(),
            fake.phone_number(),
            "BUSINESS" if is_business else "INDIVIDUAL",
            fake.company() if is_business else None,
            round(random.uniform(40000, 500000) if not is_business else random.uniform(200000, 5000000), 2),
            credit,
            tier,
            "US",
            random.choice(US_STATES),
            fake.date_between(start_date="-3y", end_date="-6m"),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """INSERT INTO borrowers
               (borrower_id, full_name, email, phone, borrower_type,
                company_name, stated_income, credit_score, risk_tier,
                country, state, onboarded_at)
               VALUES %s ON CONFLICT DO NOTHING""",
            borrowers,
        )
    conn.commit()
    print(f"  Inserted {len(borrowers)} borrowers")
    return borrowers


def generate_loans(conn, borrowers):
    """Generate ~800 loans, including demo character loans."""
    loans = []
    borrower_ids = [b[0] for b in borrowers]

    # Demo character loans
    for char in DEMO_CHARACTERS:
        lid = uuid.uuid4()
        char["_loan_id"] = lid
        originated = date(2024, 2, 1)
        term = char["term_months"]
        loans.append((
            lid,
            char["_id"],
            char["loan_type"],
            char["principal"],
            char["interest_rate"],
            term,
            char["monthly_payment"],
            char["outstanding_balance"],
            char["status"],
            originated,
            originated + timedelta(days=30 * term),
        ))

    # Random loans — aim for ~796 more
    statuses = ["CURRENT"] * 70 + ["DELINQUENT_30"] * 12 + ["DELINQUENT_60"] * 6 + \
               ["DELINQUENT_90"] * 3 + ["DEFAULT"] * 2 + ["PAID_OFF"] * 7

    for _ in range(796):
        bid = random.choice(borrower_ids)
        ltype = random.choice(LOAN_TYPES)

        if ltype == "MORTGAGE":
            principal = round(random.uniform(150000, 800000), 2)
            rate = round(random.uniform(3.5, 7.5), 3)
            term = random.choice([180, 240, 360])
        elif ltype == "AUTO":
            principal = round(random.uniform(15000, 65000), 2)
            rate = round(random.uniform(3.0, 9.0), 3)
            term = random.choice([36, 48, 60, 72])
        elif ltype == "BUSINESS":
            principal = round(random.uniform(50000, 500000), 2)
            rate = round(random.uniform(5.0, 12.0), 3)
            term = random.choice([36, 60, 84, 120])
        elif ltype == "LINE_OF_CREDIT":
            principal = round(random.uniform(5000, 100000), 2)
            rate = round(random.uniform(8.0, 18.0), 3)
            term = random.choice([12, 24, 36])
        else:  # PERSONAL
            principal = round(random.uniform(2000, 50000), 2)
            rate = round(random.uniform(5.0, 15.0), 3)
            term = random.choice([12, 24, 36, 48, 60])

        monthly = round(principal * (rate / 100 / 12) / (1 - (1 + rate / 100 / 12) ** (-term)), 2)
        status = random.choice(statuses)
        originated = fake.date_between(start_date="-3y", end_date="-3m")
        maturity = originated + timedelta(days=30 * term)

        if status == "PAID_OFF":
            outstanding = 0
        elif status == "CURRENT":
            months_elapsed = (date.today() - originated).days // 30
            outstanding = round(max(0, principal - monthly * months_elapsed * 0.4), 2)
        else:
            months_elapsed = (date.today() - originated).days // 30
            outstanding = round(max(0, principal - monthly * months_elapsed * 0.3), 2)

        loans.append((
            uuid.uuid4(), bid, ltype, principal, rate, term,
            monthly, outstanding, status, originated, maturity,
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """INSERT INTO loans
               (loan_id, borrower_id, loan_type, principal, interest_rate,
                term_months, monthly_payment, outstanding_balance, status,
                originated_at, maturity_date)
               VALUES %s ON CONFLICT DO NOTHING""",
            loans,
        )
    conn.commit()
    print(f"  Inserted {len(loans)} loans")
    return loans


def generate_payments(conn, loans):
    """Generate 50,000+ payments spanning 24 months."""
    today = date.today()
    payments = []
    batch_size = 5000

    for loan in loans:
        loan_id = loan[0]
        borrower_id = loan[1]
        monthly = float(loan[6])
        status = loan[8]
        originated = loan[9]

        # Determine pattern based on loan status
        if status == "PAID_OFF":
            pattern = "perfect"
        elif status == "CURRENT":
            pattern = random.choices(
                ["perfect", "reliable_late"],
                weights=[85, 15],
            )[0]
        elif status in ("DELINQUENT_30", "DELINQUENT_60"):
            pattern = random.choices(
                ["reliable_late", "occasional_miss", "deteriorating"],
                weights=[40, 40, 20],
            )[0]
        else:
            pattern = "deteriorating"

        # Check if this is a demo character loan
        for char in DEMO_CHARACTERS:
            if loan_id == char.get("_loan_id"):
                pattern = char["pattern"]
                break

        # Generate monthly payments from origination to today
        payment_date = originated + timedelta(days=30)
        month_idx = 0

        while payment_date <= today:
            due = payment_date

            if pattern == "perfect":
                paid = due - timedelta(days=random.randint(0, 2))
                pstatus = "PAID"
                dpd = 0
            elif pattern == "reliable_late":
                late_days = random.randint(5, 12)
                paid = due + timedelta(days=late_days)
                pstatus = "LATE"
                dpd = late_days
            elif pattern == "occasional_miss":
                if month_idx % 7 == 5:  # Miss every ~7th payment
                    paid = None
                    pstatus = "MISSED"
                    dpd = 30
                else:
                    late_days = random.randint(0, 3)
                    paid = due + timedelta(days=late_days)
                    pstatus = "PAID" if late_days == 0 else "LATE"
                    dpd = late_days
            elif pattern == "first_delinquency":
                if month_idx >= 22:  # First miss after 22 months
                    paid = None
                    pstatus = "MISSED"
                    dpd = 22
                else:
                    paid = due - timedelta(days=random.randint(0, 1))
                    pstatus = "PAID"
                    dpd = 0
            elif pattern == "deteriorating":
                if month_idx < 12:
                    late_days = random.randint(0, 5)
                    paid = due + timedelta(days=late_days)
                    pstatus = "PAID" if late_days == 0 else "LATE"
                    dpd = late_days
                elif month_idx % 3 == 0:
                    paid = None
                    pstatus = "MISSED"
                    dpd = 30 + random.randint(0, 15)
                else:
                    late_days = random.randint(10, 25)
                    paid = due + timedelta(days=late_days)
                    pstatus = "LATE"
                    dpd = late_days
            else:
                paid = due
                pstatus = "PAID"
                dpd = 0

            if paid and paid > today:
                paid = None
                if pstatus == "PAID":
                    pstatus = "MISSED"
                dpd = max(dpd, (today - due).days)

            payments.append((
                uuid.uuid4(),
                loan_id,
                borrower_id,
                round(monthly, 2),
                due,
                paid,
                pstatus,
                dpd,
                random.choice(PAYMENT_METHODS) if paid else None,
                datetime.combine(due, datetime.min.time()),
            ))

            # Flush in batches
            if len(payments) >= batch_size:
                _insert_payments(conn, payments)
                payments = []

            payment_date += timedelta(days=30)
            month_idx += 1

    if payments:
        _insert_payments(conn, payments)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM payments")
        total = cur.fetchone()[0]
    print(f"  Inserted {total} payments total")


def _insert_payments(conn, payments):
    with conn.cursor() as cur:
        execute_values(
            cur,
            """INSERT INTO payments
               (payment_id, loan_id, borrower_id, amount, due_date,
                paid_date, status, days_past_due, payment_method, created_at)
               VALUES %s ON CONFLICT DO NOTHING""",
            payments,
        )
    conn.commit()


def generate_recovery_narratives(conn, count=100):
    """Generate recovery history narratives."""
    narratives = []
    for _ in range(count):
        template = random.choice(RECOVERY_NARRATIVES)
        method = random.choice(OUTREACH_METHODS)
        outcome = random.choices(OUTCOMES, weights=[50, 10, 25, 15])[0]
        days = random.randint(7, 180)

        narrative = template.format(method=method, outcome=outcome.lower(), days=days)

        narratives.append((
            uuid.uuid4(),
            random.choice(["INDIVIDUAL", "BUSINESS"]),
            random.choice(DELINQUENCY_PATTERNS),
            method,
            outcome,
            days,
            narrative,
            None,  # embedding — populated later
            datetime.now() - timedelta(days=random.randint(30, 730)),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """INSERT INTO recovery_history
               (id, borrower_type, delinquency_pattern, outreach_method,
                outcome, days_to_resolution, narrative, embedding, created_at)
               VALUES %s ON CONFLICT DO NOTHING""",
            narratives,
        )
    conn.commit()
    print(f"  Inserted {len(narratives)} recovery narratives")


def generate_fraud_signals(conn):
    """Generate 15 fraud signals. Robert Keane's is OPEN."""
    signals = []

    # Robert Keane's OPEN fraud signal
    robert_id = DEMO_CHARACTERS[3]["_id"]
    robert_loan = DEMO_CHARACTERS[3]["_loan_id"]
    signals.append((
        uuid.uuid4(),
        robert_id,
        robert_loan,
        "INCOME_MISMATCH",
        "HIGH",
        "Stated income of $110,000 does not match verified income of $62,000 from tax records. "
        "Discrepancy of 77%. Employment verification returned inconsistent dates.",
        datetime.now() - timedelta(days=5),
        "OPEN",
    ))

    # 14 more signals for random borrowers (mostly CLEARED)
    with conn.cursor() as cur:
        cur.execute("SELECT borrower_id FROM borrowers ORDER BY random() LIMIT 14")
        random_borrowers = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT loan_id, borrower_id FROM loans ORDER BY random() LIMIT 14")
        random_loans = cur.fetchall()

    signal_types = ["INCOME_MISMATCH", "IDENTITY_INCONSISTENCY", "VELOCITY", "GEO_ANOMALY"]
    severities = ["HIGH", "MEDIUM", "LOW"]
    cleared_statuses = ["CLEARED"] * 10 + ["INVESTIGATING"] * 2 + ["CONFIRMED_FRAUD"] * 2

    details_templates = [
        "Address verification returned different state than application. Resolved: borrower relocated.",
        "Multiple applications from same IP within 24 hours. Investigated: shared household.",
        "Credit pull showed different SSN variant. Resolved: data entry error at bureau.",
        "Income documentation showed inconsistent employer. Cleared after HR verification.",
        "Unusual payment velocity detected — 3 large payments in 48 hours. Cleared: refinancing.",
        "Geographic anomaly: login from overseas IP. Cleared: borrower traveling.",
        "Identity document scan flagged. Resolved: poor image quality on upload.",
        "Stated employment not found in database. Cleared: new company not yet indexed.",
        "Payment method changed 3 times in one week. Investigated: bank migration.",
        "Credit score dropped 80 points in 30 days. Monitored: medical bills impacting score.",
        "Application SSN linked to a minor. Confirmed fraud: identity theft of family member.",
        "Duplicate application with different income amounts. Investigating discrepancy.",
        "Employer phone number routes to personal cell. Cleared: sole proprietor.",
        "Address matched to commercial property. Cleared: home-based business.",
    ]

    for i in range(14):
        bid = random_loans[i][1] if i < len(random_loans) else random_borrowers[i]
        lid = random_loans[i][0] if i < len(random_loans) else None
        signals.append((
            uuid.uuid4(),
            bid,
            lid,
            random.choice(signal_types),
            random.choice(severities),
            details_templates[i],
            datetime.now() - timedelta(days=random.randint(10, 365)),
            cleared_statuses[i],
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """INSERT INTO fraud_signals
               (signal_id, borrower_id, loan_id, signal_type, severity,
                details, detected_at, status)
               VALUES %s ON CONFLICT DO NOTHING""",
            signals,
        )
    conn.commit()
    print(f"  Inserted {len(signals)} fraud signals")


def load_prebaked_embeddings(conn):
    """Load pre-generated embeddings from embeddings.json and update recovery_history."""
    import hashlib
    embeddings_path = os.path.join(os.path.dirname(__file__), "embeddings.json")
    if not os.path.exists(embeddings_path):
        print("  No embeddings.json found — skipping. Run 'make embed' to generate.")
        return

    with open(embeddings_path) as f:
        data = json.load(f)

    # Build lookup: narrative_hash -> embedding
    emb_map = {item["narrative_hash"]: item["embedding"] for item in data}

    # Fetch narratives and match by hash
    with conn.cursor() as cur:
        cur.execute("SELECT id, narrative FROM recovery_history WHERE embedding IS NULL")
        rows = cur.fetchall()

    updated = 0
    with conn.cursor() as cur:
        for row_id, narrative in rows:
            key = hashlib.sha256(narrative.encode()).hexdigest()[:16]
            if key in emb_map:
                vec_str = "[" + ",".join(str(x) for x in emb_map[key]) + "]"
                cur.execute(
                    "UPDATE recovery_history SET embedding = %s WHERE id = %s",
                    (vec_str, row_id),
                )
                updated += 1
    conn.commit()
    print(f"  Loaded {updated} pre-baked embeddings (of {len(rows)} narratives)")


def main():
    print("Connecting to PostgreSQL...")
    conn = connect()
    print("Connected.\n")

    print("Generating borrowers...")
    borrowers = generate_borrowers(conn)

    print("Generating loans...")
    loans = generate_loans(conn, borrowers)

    print("Generating payments (this may take a moment)...")
    generate_payments(conn, loans)

    print("Generating recovery narratives...")
    generate_recovery_narratives(conn)

    print("Loading pre-baked pgvector embeddings...")
    load_prebaked_embeddings(conn)

    print("Generating fraud signals...")
    generate_fraud_signals(conn)

    conn.close()
    print("\nSeed data generation complete!")


if __name__ == "__main__":
    main()
