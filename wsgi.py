# ============================================================
#  WSGI CONFIGURATION — PythonAnywhere
#  1. In PythonAnywhere → Web tab → click WSGI configuration file
#  2. DELETE everything in that file
#  3. PASTE the contents below
#  4. Replace 'vardhanwanjari' with your actual username
#  5. Click Save
#  6. Click "Reload vardhanwanjari.pythonanywhere.com"
# ============================================================

import sys
import os

# ── Add project folder to Python path ───────────────────────
# Replace 'vardhanwanjari' with YOUR PythonAnywhere username
# Replace 'expense_tracker' with YOUR actual folder name
project_home = '/home/vardhanwanjari/expense_tracker'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ── Load .env file ───────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# ── Import Flask app ─────────────────────────────────────────
from app import app as application
