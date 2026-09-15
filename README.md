# AI Expense Tracker — Neon PostgreSQL + PythonAnywhere
# Complete Free Deployment Guide

## What This Setup Gives You

    Neon.tech        → Free PostgreSQL database (cloud)
    PythonAnywhere   → Free Flask hosting (live website)
    Result           → vardhanwanjari.pythonanywhere.com  (LIVE 24/7)
    Cost             → ZERO — no credit card anywhere

## Project Files

    expense_tracker/
    ├── app.py            ← Flask backend (Neon PostgreSQL version)
    ├── requirements.txt  ← psycopg2-binary instead of supabase
    ├── .env.example      ← Copy to .env and fill in Neon URL
    ├── .env              ← YOUR credentials (never share)
    ├── neon_schema.sql   ← Run this in Neon SQL Editor
    ├── wsgi.py           ← Paste into PythonAnywhere WSGI config
    └── templates/
        └── index.html    ← UNCHANGED — same frontend

========================================================
 PART 1 — SETUP NEON DATABASE (5 minutes)
========================================================

STEP 1 — Create Free Neon Account
    Go to  : https://neon.tech
    Click  : Sign Up (GitHub login is fastest)
    No credit card needed

STEP 2 — Create a Project
    Click  : New Project
    Name   : expense-tracker
    Region : AWS / Asia Pacific (closest to India)
    Click  : Create Project

STEP 3 — Run the Schema
    In Neon Dashboard → click "SQL Editor"
    Click "New Query"
    Open neon_schema.sql from this project
    Copy ALL contents → paste into SQL Editor
    Click "Run" button
    You should see: CREATE TABLE, CREATE INDEX messages

STEP 4 — Get Your Connection String
    In Neon Dashboard → click "Connection Details"
    Under "Connection string" copy the full URL:
    It looks like:
    postgresql://user:pass@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require

    SAVE THIS — you need it in the next step

========================================================
 PART 2 — SETUP PYTHONANYWHERE (10 minutes)
========================================================

STEP 5 — You Already Have PythonAnywhere Account
    Your username: vardhanwanjari
    Your URL     : http://vardhanwanjari.pythonanywhere.com

STEP 6 — Upload Project Files
    PythonAnywhere Dashboard → Files tab
    Go to: /home/vardhanwanjari/
    Create new folder: expense_tracker
    Upload these files into it:
        app.py
        requirements.txt
        wsgi.py
        .env
        templates/index.html   (create templates folder first)

STEP 7 — Create .env File
    In Files tab → go to /home/vardhanwanjari/expense_tracker/
    Create new file: .env
    Paste this (replace with YOUR Neon URL):

        DATABASE_URL=postgresql://user:pass@ep-xxxx.aws.neon.tech/neondb?sslmode=require
        FLASK_SECRET_KEY=any_random_string_here_change_this
        FLASK_DEBUG=False
        FLASK_PORT=5000

STEP 8 — Install Packages
    Dashboard → Consoles → Bash → type:

        pip3.10 install --user flask psycopg2-binary werkzeug python-dotenv

    Wait for installation to finish.

STEP 9 — Configure Web App
    Dashboard → Web tab → "Add a new web app"
    Click Next
    Select: Manual configuration
    Select: Python 3.10
    Click Next

    Now scroll down to "WSGI configuration file"
    Click the link to open it
    DELETE everything in that file
    PASTE the contents of wsgi.py
    (make sure the folder path says vardhanwanjari)
    Click Save

STEP 10 — Go LIVE
    In Web tab → click the green button:
    "Reload vardhanwanjari.pythonanywhere.com"

    Open in any browser:
    http://vardhanwanjari.pythonanywhere.com

    YOUR APP IS LIVE ON THE INTERNET! ✅

========================================================
 VERIFY EVERYTHING WORKS
========================================================

1. Open http://vardhanwanjari.pythonanywhere.com
2. Register a new account
3. Login with username / email / contact
4. Add an expense — type "200 pizza"
5. Check dashboard charts
6. Try Export CSV

To see your data in Neon:
    neon.tech → Your Project → Tables
    → users table   → see registered users
    → expenses table → see all expenses

========================================================
 API ENDPOINTS (IDENTICAL to Supabase version)
========================================================

    POST   /api/register          Create new account
    POST   /api/login             Login (username/email/contact)
    POST   /api/logout            End session
    GET    /api/me                Get current user profile
    GET    /api/expenses          Get all expenses
    POST   /api/expenses          Add new expense
    DELETE /api/expenses/<id>     Delete one expense
    DELETE /api/expenses/clear    Delete all expenses
    GET    /api/expenses/export   Download CSV report
    GET    /api/analytics/summary Category totals
    GET    /api/analytics/monthly Monthly totals

========================================================
 TROUBLESHOOTING
========================================================

Problem: "DATABASE_URL not found"
Fix    : Check .env file exists and has DATABASE_URL=...
         Make sure .env is in /home/vardhanwanjari/expense_tracker/

Problem: "could not connect to server"
Fix    : Check your Neon project is active (neon.tech → Dashboard)
         Free Neon projects auto-pause after inactivity
         Just open neon.tech and it wakes up automatically

Problem: "ModuleNotFoundError: No module named 'psycopg2'"
Fix    : Run in Bash console:
         pip3.10 install --user psycopg2-binary

Problem: "relation users does not exist"
Fix    : Run neon_schema.sql in Neon SQL Editor again

Problem: 500 Internal Server Error
Fix    : Dashboard → Web tab → Error log → read the exact error

Problem: App shows old version after you made changes
Fix    : Dashboard → Web tab → Reload vardhanwanjari.pythonanywhere.com

========================================================
 WHAT CHANGED vs SUPABASE VERSION
========================================================

    supabase library         → psycopg2-binary
    create_client(URL, KEY)  → psycopg2.connect(DATABASE_URL)
    supabase.table()...      → cursor.execute(SQL)
    SUPABASE_URL + KEY       → DATABASE_URL (one string)
    Supabase views           → PostgreSQL GROUP BY queries

    index.html               → UNCHANGED (not touched)
    All route URLs           → UNCHANGED
    All business logic       → UNCHANGED
    Session handling         → UNCHANGED
    CSV export               → UNCHANGED
    hash_password()          → UNCHANGED
    generate_id()            → UNCHANGED
