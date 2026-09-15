-- ── 1. USERS TABLE ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    contact       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── 2. EXPENSES TABLE ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS expenses (
    expense_id  TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    amount      NUMERIC(10,2) NOT NULL,
    category    TEXT NOT NULL DEFAULT 'Other',
    description TEXT NOT NULL DEFAULT 'Expense',
    date        TIMESTAMPTZ DEFAULT NOW(),
    source      TEXT DEFAULT 'text',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 3. INDEXES ───────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_expenses_user_id  ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date     ON expenses(date DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);

-- ── 4. VERIFY ────────────────────────────────────────────────
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';

-- ── DONE ─────────────────────────────────────────────────────
-- Both tables created. Now update .env with your Neon DATABASE_URL.
