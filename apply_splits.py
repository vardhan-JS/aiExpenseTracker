import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

sql = """
CREATE TABLE IF NOT EXISTS splits (
    split_id      TEXT PRIMARY KEY,
    expense_id    TEXT NOT NULL REFERENCES expenses(expense_id) ON DELETE CASCADE,
    payer_id      TEXT NOT NULL REFERENCES users(user_id),
    owed_by_id    TEXT NOT NULL REFERENCES users(user_id),
    amount        NUMERIC(10,2) NOT NULL,
    screenshot_url TEXT,
    status        TEXT DEFAULT 'pending',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_splits_payer ON splits(payer_id);
CREATE INDEX IF NOT EXISTS idx_splits_owed ON splits(owed_by_id);
"""

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    print("✅ Splitwise database tables updated successfully!")
except Exception as e:
    print(f"❌ Error updating database: {e}")
finally:
    if 'conn' in locals():
        conn.close()
