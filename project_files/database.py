import sqlite3

DB_NAME = "medical_system.db"

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # ================= USERS =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT,
        last_login TEXT,
        is_active INTEGER DEFAULT 1
    )
    """)

    # Migration: add is_active column if it doesn't exist (for existing DBs)
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]
    if "is_active" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")

    # ================= DISPENSE LOG =================
    # ✅ doctor_name ADDED (THIS FIXES YOUR ERROR)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dispense_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        prescription_id TEXT,
        patient_name TEXT,
        doctor_name TEXT,
        medicine_name TEXT,
        prescribed_dose TEXT,
        dispensed_dose TEXT,
        pharmacist_id INTEGER,
        timestamp TEXT
    )
    """)

    # ================= PRESCRIPTION METADATA =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS prescription_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prescription_id TEXT UNIQUE,
        raw_text TEXT,
        symptoms_json TEXT,
        diseases_json TEXT,
        interactions_json TEXT,
        dosage_safety_json TEXT
    )
    """)

    # ================= AUDIT LOG =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()
