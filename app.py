"""
AI Expense Tracker — Flask + Neon PostgreSQL Backend
Database : Neon (free PostgreSQL cloud) via psycopg2
Auth     : Custom SHA-256 + Flask sessions  ← UNCHANGED
Frontend : templates/index.html             ← UNCHANGED

WHAT CHANGED vs Supabase version:
  supabase library     → psycopg2-binary
  create_client()      → psycopg2.connect(DATABASE_URL)
  supabase.table()...  → cursor.execute(SQL)
  SUPABASE_URL/KEY     → DATABASE_URL (single connection string)

WHAT DID NOT CHANGE (100% identical):
  All route URLs and HTTP methods
  All validation logic
  All session handling
  hash_password()
  generate_id()
  login_required()
  CSV export logic
  index.html (not touched)
"""

import os, io, csv, hashlib, uuid
from datetime import datetime
from functools import wraps
from collections import defaultdict
from dotenv import load_dotenv
from flask import Flask, request, jsonify, session, send_file, render_template
import psycopg2
import psycopg2.extras   # for dictionary cursor (returns rows as dicts)
from PIL import Image
import pytesseract

# ── Load .env ────────────────────────────────────────────────
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_secret_change_this")

# ════════════════════════════════════════════════════════════
#  CONFIGURATION
# ════════════════════════════════════════════════════════════
UPLOAD_FOLDER = 'static/uploads/splits'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ════════════════════════════════════════════════════════════
#  NEON DATABASE CONNECTION
#  Replaces: supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
#  One DATABASE_URL string contains everything
# ════════════════════════════════════════════════════════════
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError(
        "\n\n ERROR: DATABASE_URL not found!\n"
        " Create a .env file with:\n"
        " DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require\n"
        " Get it from: neon.tech → Your Project → Connection Details\n"
    )

def get_db():
    """
    Open and return a new Neon PostgreSQL connection.
    Replaces: supabase = create_client(URL, KEY)
    Uses DictCursor so rows come back as dictionaries — same as Supabase .data
    """
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# ── Startup check ────────────────────────────────────────────
try:
    _test = get_db()
    _test.close()
    print(f"\n Neon PostgreSQL connected successfully!")
    print(f" AI Expense Tracker → http://localhost:5000\n")
except Exception as e:
    print(f"\n ERROR: Cannot connect to Neon!\n {e}")
    print(" Check your DATABASE_URL in .env file\n")


# ════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS — 100% IDENTICAL to Supabase version
# ════════════════════════════════════════════════════════════

def hash_password(pw: str) -> str:
    """Convert plain password to SHA-256 hash."""
    return hashlib.sha256(pw.encode()).hexdigest()


def generate_id(length: int = 8) -> str:
    """Generate short unique ID like 'A3F8B2C1'."""
    return str(uuid.uuid4()).replace("-", "")[:length].upper()


def login_required(f):
    """Decorator: returns 401 if user not logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized — please log in"}), 401
        return f(*args, **kwargs)
    return decorated


def get_current_user_id() -> str:
    """Return logged-in user's ID from Flask session."""
    return session.get("user_id")


# ════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════════════════════════

@app.route("/api/register", methods=["POST"])
def register():
    """Register a new user. Stores hashed password in Neon PostgreSQL."""
    d        = request.json or {}
    name     = d.get("name",     "").strip()
    email    = d.get("email",    "").strip().lower()
    username = d.get("username", "").strip().lower()
    contact  = d.get("contact",  "").strip()
    password = d.get("password", "").strip()

    # ── Validate (IDENTICAL) ──────────────────────────────
    if not all([name, email, username, contact, password]):
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if not contact.isdigit() or len(contact) != 10:
        return jsonify({"error": "Contact must be a 10-digit number"}), 400

    # ── Check duplicates in Neon ──────────────────────────
    try:
        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Email already registered"}), 409

        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"error": "Username already taken"}), 409

        cursor.execute("SELECT user_id FROM users WHERE contact = %s", (contact,))
        if cursor.fetchone():
            return jsonify({"error": "Contact number already registered"}), 409

        # ── Insert into Neon ──────────────────────────────
        user_id = generate_id(8)
        cursor.execute("""
            INSERT INTO users
              (user_id, username, name, email, contact, password_hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, username, name, email, contact,
            hash_password(password), datetime.now()
        ))
        conn.commit()

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

    session["user_id"]  = user_id
    session["username"] = username
    session["name"]     = name

    return jsonify({
        "message": "Account created successfully",
        "user": {"name": name, "username": username, "user_id": user_id}
    }), 201


@app.route("/api/login", methods=["POST"])
def login():
    """Login with username, email, or contact number + password."""
    d          = request.json or {}
    identifier = d.get("identifier", "").strip().lower()
    password   = d.get("password",   "").strip()

    if not identifier or not password:
        return jsonify({"error": "Identifier and password are required"}), 400

    matched = None
    try:
        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM users
            WHERE username = %s OR email = %s OR contact = %s
            LIMIT 1
        """, (identifier, identifier, identifier))
        matched = cursor.fetchone()

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

    if not matched:
        return jsonify({"error": "No account found with that username, email, or contact"}), 404

    if matched["password_hash"] != hash_password(password):
        return jsonify({"error": "Incorrect password"}), 401

    session["user_id"]  = matched["user_id"]
    session["username"] = matched["username"]
    session["name"]     = matched["name"]

    return jsonify({
        "message": "Login successful",
        "user": {
            "name":     matched["name"],
            "username": matched["username"],
            "email":    matched["email"],
            "user_id":  matched["user_id"]
        }
    })


@app.route("/api/logout", methods=["POST"])
def logout():
    """Clear Flask session. IDENTICAL."""
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@app.route("/api/me", methods=["GET"])
@login_required
def me():
    """Return current user profile from Neon."""
    try:
        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT user_id, username, name, email, contact, created_at
            FROM users WHERE user_id = %s
        """, (get_current_user_id(),))
        user = cursor.fetchone()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    user = dict(user)
    user["created_at"] = str(user["created_at"])
    return jsonify(user)


# ════════════════════════════════════════════════════════════
#  EXPENSE ROUTES
# ════════════════════════════════════════════════════════════

@app.route("/api/expenses", methods=["GET"])
@login_required
def get_expenses():
    """Fetch all expenses for logged-in user, newest first."""
    try:
        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM expenses
            WHERE user_id = %s
            ORDER BY date DESC
        """, (get_current_user_id(),))
        rows = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    result = []
    for r in rows:
        r = dict(r)
        r["date"]       = str(r["date"])
        r["created_at"] = str(r.get("created_at", ""))
        r["amount"]     = float(r["amount"])
        result.append(r)
    return jsonify(result)


@app.route("/api/expenses", methods=["POST"])
@login_required
def add_expense():
    """Add a new expense to Neon PostgreSQL."""
    d = request.json or {}

    try:
        amount = float(d.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Amount must be a valid number"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than 0"}), 400

    expense = {
        "expense_id":  generate_id(12),
        "user_id":     get_current_user_id(),
        "amount":      round(amount, 2),
        "category":    d.get("category",    "Other"),
        "description": d.get("description", "Expense"),
        "date":        datetime.now(),
        "source":      d.get("source",      "text"),
    }

    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expenses
              (expense_id, user_id, amount, category, description, date, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            expense["expense_id"], expense["user_id"], expense["amount"],
            expense["category"],   expense["description"],
            expense["date"],       expense["source"]
        ))
        conn.commit()
    except Exception as e:
        return jsonify({"error": f"Failed to save expense: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

    expense["date"]   = str(expense["date"])
    expense["amount"] = float(expense["amount"])
    return jsonify({"message": "Expense saved", "expense": expense}), 201


@app.route("/api/users/usernames", methods=["GET"])
@login_required
def get_usernames():
    """Fetch all registered usernames for the splitwise dropdown."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users ORDER BY username ASC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([r[0] for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/expenses/split", methods=["POST"])
@login_required
def add_split_expense():
    """
    Split an expense among multiple users.
    Requires a screenshot upload to proceed.
    """
    if 'screenshot' not in request.files:
        return jsonify({"error": "Screenshot proof is required for splitting expenses"}), 400

    file = request.files['screenshot']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        amount = float(request.form.get("amount", 0))
        category = request.form.get("category", "Other")
        description = request.form.get("description", "Split Expense")
        split_with = request.form.get("split_with", "").split(",")
        split_with = [u.strip().lower() for u in split_with if u.strip()]
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount provided"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than 0"}), 400
    if not split_with:
        return jsonify({"error": "You must specify at least one person to split with"}), 400

    payer_id = get_current_user_id()

    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        user_ids = []
        for uname in split_with:
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (uname,))
            u = cursor.fetchone()
            if not u:
                return jsonify({"error": f"User '{uname}' not found"}), 404
            user_ids.append(u['user_id'])

        expense_id = generate_id(12)
        cursor.execute("""
            INSERT INTO expenses (expense_id, user_id, amount, category, description, date, source)
            VALUES (%s, %s, %s, %s, %s, NOW(), 'splitwise')
        """, (expense_id, payer_id, amount, category, description))

        num_people = len(user_ids) + 1
        split_amount = round(amount / num_people, 2)

        filename = f"split_{expense_id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        screenshot_url = f"/static/uploads/splits/{filename}"

        for owed_id in user_ids:
            split_id = generate_id(8)
            cursor.execute("""
                INSERT INTO splits (split_id, expense_id, payer_id, owed_by_id, amount, screenshot_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (split_id, expense_id, payer_id, owed_id, split_amount, screenshot_url))

        conn.commit()
        return jsonify({"message": "Expense split successfully!", "expense_id": expense_id}), 201

    except Exception as e:
        return jsonify({"error": f"Split error: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/api/splits", methods=["GET"])
@login_required
def get_splits():
    """Fetch all debts involving the current user."""
    uid = get_current_user_id()
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT s.*, u.username as owed_by_name, e.description as expense_desc
            FROM splits s
            JOIN users u ON s.owed_by_id = u.user_id
            JOIN expenses e ON s.expense_id = e.expense_id
            WHERE s.payer_id = %s AND s.status = 'pending'
        """, (uid,))
        i_owe_them = cursor.fetchall()

        cursor.execute("""
            SELECT s.*, u.username as payer_name, e.description as expense_desc
            FROM splits s
            JOIN users u ON s.payer_id = u.user_id
            JOIN expenses e ON s.expense_id = e.expense_id
            WHERE s.owed_by_id = %s AND s.status = 'pending'
        """, (uid,))
        they_owe_me = cursor.fetchall()

        conn.close()
        return jsonify({
            "owing_me": i_owe_them,
            "i_owing": they_owe_me
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/expenses/<expense_id>", methods=["DELETE"])
@login_required
def delete_expense(expense_id):
    """Delete a specific expense (only if it belongs to current user)."""
    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM expenses
            WHERE expense_id = %s AND user_id = %s
        """, (expense_id, get_current_user_id()))
        conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({"message": "Expense deleted"})


@app.route("/api/expenses/clear", methods=["DELETE"])
@login_required
def clear_all_expenses():
    """Delete ALL expenses for the current user."""
    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE user_id = %s", (get_current_user_id(),))
        conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({"message": "All expenses cleared"})


@app.route("/api/expenses/export", methods=["GET"])
@login_required
def export_expenses():
    """Download CSV report — logic 100% IDENTICAL to Supabase version."""
    uid   = get_current_user_id()
    uname = session.get("username", "user")

    try:
        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM expenses
            WHERE user_id = %s ORDER BY date DESC
        """, (uid,))
        rows = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["#", "Date", "Time", "Description", "Category", "Amount (₹)", "Source"])

    for i, r in enumerate(rows, 1):
        r  = dict(r)
        dt = r["date"] if isinstance(r["date"], datetime) else \
             datetime.fromisoformat(str(r["date"]).replace("Z", "+00:00"))
        writer.writerow([
            i,
            dt.strftime("%d/%m/%Y"),
            dt.strftime("%H:%M"),
            r["description"],
            r["category"],
            f"{float(r['amount']):.2f}",
            r.get("source", "text")
        ])

    cat_totals = defaultdict(float)
    for r in rows:
        cat_totals[r["category"]] += float(r["amount"])

    writer.writerow([])
    writer.writerow(["", "── SUMMARY ──", "", "", "", ""])
    writer.writerow(["", "Category", "", "", "", "Total (₹)"])
    for cat, amt in sorted(cat_totals.items(), key=lambda x: -x[1]):
        writer.writerow(["", cat, "", "", "", f"{amt:.2f}"])
    grand_total = sum(float(r["amount"]) for r in rows)
    writer.writerow(["", "GRAND TOTAL", "", "", "", f"{grand_total:.2f}"])
    writer.writerow([])
    writer.writerow(["", f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}"])

    output.seek(0)
    filename = f"expenses_{uname}_{datetime.now().strftime('%Y%m%d')}.csv"

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )


# ════════════════════════════════════════════════════════════
#  ANALYTICS ROUTES
# ════════════════════════════════════════════════════════════

@app.route("/api/analytics/summary", methods=["GET"])
@login_required
def analytics_summary():
    """Category totals — same result as Supabase expense_summary view."""
    try:
        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT
                user_id,
                category,
                COUNT(*)       AS transaction_count,
                SUM(amount)    AS total_amount,
                AVG(amount)    AS avg_amount,
                MAX(amount)    AS max_amount,
                MIN(date)      AS first_expense,
                MAX(date)      AS last_expense
            FROM expenses
            WHERE user_id = %s
            GROUP BY user_id, category
        """, (get_current_user_id(),))
        rows = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    result = []
    for r in rows:
        r = dict(r)
        r["total_amount"]  = float(r["total_amount"]  or 0)
        r["avg_amount"]    = float(r["avg_amount"]    or 0)
        r["max_amount"]    = float(r["max_amount"]    or 0)
        r["first_expense"] = str(r["first_expense"])
        r["last_expense"]  = str(r["last_expense"])
        result.append(r)
    return jsonify(result)


@app.route("/api/analytics/monthly", methods=["GET"])
@login_required
def analytics_monthly():
    """Monthly totals — same result as Supabase monthly_totals view."""
    try:
        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT
                user_id,
                DATE_TRUNC('month', date) AS month,
                SUM(amount)               AS total,
                COUNT(*)                  AS count
            FROM expenses
            WHERE user_id = %s
            GROUP BY user_id, DATE_TRUNC('month', date)
            ORDER BY month DESC
        """, (get_current_user_id(),))
        rows = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    result = []
    for r in rows:
        r = dict(r)
        r["total"] = float(r["total"] or 0)
        r["month"] = str(r["month"])
        result.append(r)
    return jsonify(result)


# ════════════════════════════════════════════════════════════
#  SERVE FRONTEND — IDENTICAL
# ════════════════════════════════════════════════════════════

@app.route("/api/ocr", methods=["POST"])
@login_required
def perform_ocr():
    """
    Perform real OCR on the uploaded image.
    Expects a file in request.files['image'].
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    try:
        tesseract_path = os.getenv("TESSERACT_PATH")
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        elif os.path.exists("/usr/bin/tesseract"):
            pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

        img = Image.open(file.stream).convert('L')
        text = pytesseract.image_to_string(img)

        if len(text.strip()) < 10:
            inverted = Image.eval(img, lambda x: 255 - x)
            inv_text = pytesseract.image_to_string(inverted)
            if len(inv_text.strip()) > len(text.strip()):
                text = inv_text

        return jsonify({"text": text})
    except Exception as e:
        error_msg = str(e)
        if "tesseract is not installed" in error_msg.lower() or "not found" in error_msg.lower():
            return jsonify({"error": "OCR engine not found on server. Please check Docker/System installation."}), 500
        return jsonify({"error": f"OCR Error: {error_msg}"}), 500

@app.route("/")
def index():
    return render_template("index.html")


# ════════════════════════════════════════════════════════════
#  RUN — IDENTICAL
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"\n AI Expense Tracker (Neon PostgreSQL) → http://localhost:{port}\n")
    app.run(debug=debug, port=port)
