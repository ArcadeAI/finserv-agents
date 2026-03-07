-- FinServ Agents — PostgreSQL Schema
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ── Borrowers ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS borrowers (
    borrower_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name      TEXT NOT NULL,
    email          TEXT,
    phone          TEXT,
    borrower_type  TEXT CHECK (borrower_type IN ('INDIVIDUAL','BUSINESS')),
    company_name   TEXT,
    stated_income  DECIMAL(12,2),
    credit_score   INT,
    risk_tier      TEXT CHECK (risk_tier IN ('PRIME','NEAR_PRIME','SUBPRIME')),
    country        TEXT DEFAULT 'US',
    state          TEXT,
    onboarded_at   DATE DEFAULT CURRENT_DATE
);

-- ── Loans ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS loans (
    loan_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    borrower_id       UUID REFERENCES borrowers(borrower_id),
    loan_type         TEXT CHECK (loan_type IN ('PERSONAL','MORTGAGE','AUTO','BUSINESS','LINE_OF_CREDIT')),
    principal         DECIMAL(15,2),
    interest_rate     DECIMAL(5,3),
    term_months       INT,
    monthly_payment   DECIMAL(10,2),
    outstanding_balance DECIMAL(15,2),
    status            TEXT CHECK (status IN ('CURRENT','DELINQUENT_30','DELINQUENT_60','DELINQUENT_90','DEFAULT','PAID_OFF')),
    originated_at     DATE,
    maturity_date     DATE
);

-- ── Payment Ledger ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS payments (
    payment_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loan_id        UUID REFERENCES loans(loan_id),
    borrower_id    UUID REFERENCES borrowers(borrower_id),
    amount         DECIMAL(10,2),
    due_date       DATE,
    paid_date      DATE,
    status         TEXT CHECK (status IN ('PAID','LATE','MISSED','GRACE','WAIVED')),
    days_past_due  INT DEFAULT 0,
    payment_method TEXT CHECK (payment_method IN ('ACH','WIRE','CHECK','AUTO_DEBIT')),
    created_at     TIMESTAMP DEFAULT NOW()
);

-- ── Recovery History with pgvector embeddings ──────────────────────────

CREATE TABLE IF NOT EXISTS recovery_history (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    borrower_type        TEXT,
    delinquency_pattern  TEXT,
    outreach_method      TEXT,
    outcome              TEXT CHECK (outcome IN ('RECOVERED','DEFAULT','RESTRUCTURED','SETTLED')),
    days_to_resolution   INT,
    narrative            TEXT,
    embedding            VECTOR(1536),
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recovery_embedding ON recovery_history USING hnsw (embedding vector_cosine_ops);

-- ── Fraud Signals ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fraud_signals (
    signal_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    borrower_id  UUID REFERENCES borrowers(borrower_id),
    loan_id      UUID REFERENCES loans(loan_id),
    signal_type  TEXT CHECK (signal_type IN ('INCOME_MISMATCH','IDENTITY_INCONSISTENCY','VELOCITY','GEO_ANOMALY')),
    severity     TEXT CHECK (severity IN ('HIGH','MEDIUM','LOW')),
    details      TEXT,
    detected_at  TIMESTAMP DEFAULT NOW(),
    status       TEXT CHECK (status IN ('OPEN','INVESTIGATING','CLEARED','CONFIRMED_FRAUD')) DEFAULT 'OPEN'
);

-- ── Indexes ────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_loans_borrower ON loans(borrower_id);
CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status);
CREATE INDEX IF NOT EXISTS idx_payments_loan ON payments(loan_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_due_date ON payments(due_date);
CREATE INDEX IF NOT EXISTS idx_fraud_borrower ON fraud_signals(borrower_id);
CREATE INDEX IF NOT EXISTS idx_fraud_status ON fraud_signals(status);
