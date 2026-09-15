-- ── 5. SPLITS TABLE (For Splitwise Feature) ──────────────────
CREATE TABLE IF NOT EXISTS splits (
    split_id      TEXT PRIMARY KEY,
    expense_id    TEXT NOT NULL REFERENCES expenses(expense_id) ON DELETE CASCADE,
    payer_id      TEXT NOT NULL REFERENCES users(user_id),
    owed_by_id    TEXT NOT NULL REFERENCES users(user_id),
    amount        NUMERIC(10,2) NOT NULL,
    screenshot_url TEXT,
    status        TEXT DEFAULT 'pending', -- 'pending' or 'paid'
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_splits_payer ON splits(payer_id);
CREATE INDEX IF NOT EXISTS idx_splits_owed ON splits(owed_by_id);
