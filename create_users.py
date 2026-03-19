import sqlite3

conn = sqlite3.connect("medical_system.db")
cur = conn.cursor()

users = [
    ("admin", "admin123", "admin"),
    ("pharmacist", "pharma123", "pharmacist"),
    ("doctor", "doctor123", "doctor")
]

cur.executemany("""
INSERT INTO users (username, password, role)
VALUES (?, ?, ?)
""", users)

conn.commit()
conn.close()

print("✅ Admin, Pharmacist, Doctor users created successfully")
