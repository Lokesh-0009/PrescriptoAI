from database import get_db

def create_user(username, password, role):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (username, password, role)
        VALUES (?, ?, ?)
    """, (username, password, role))

    conn.commit()
    conn.close()
    print("✅ User created successfully")

# -------------------------
# CREATE DEFAULT USERS
# -------------------------

create_user("admin", "admin123", "admin")
create_user("pharmacist", "pharma123", "staff")
create_user("owner", "owner123", "owner")
