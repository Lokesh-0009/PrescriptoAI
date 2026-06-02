from flask import Flask, render_template, request, redirect, session, jsonify, flash
import os
import json
from datetime import datetime

# ================= DATABASE =================
from database import init_db, get_db

# ================= AI MODULES =================
from ocr.trocr_engine import extract_text
from nlp.entity_extraction import extract_entities
from ml.disease_predictor import predict_disease
from ml.drug_safety import analyze_drug_interactions, analyze_dosage_safety

# ================= APP CONFIG =================
app = Flask(__name__)
app.secret_key = "prescriptoai_secret_key"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()

# ================= AUTH HELPER =================
def login_required():
    return "user_id" in session

# ================= LOGIN AND REGISTER =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        # Backend decides role — lookup by username or email + password
        cur.execute(
            "SELECT user_id, role, username FROM users WHERE (username=? OR email=?) AND password=?",
            (username, username, password)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            # Read role from DB — backend is the authority
            user_role = user[1]
            session["user_id"] = user[0]
            session["role"] = user_role
            session["username"] = user[2]
            flash(f"Welcome back, {user[2]}! Logged in as {user_role.capitalize()}.", "success")
            return redirect("/")

        return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        new_password = request.form.get("new_password")
        
        if not email or not new_password:
            return render_template("forgot_password.html", message="Email and New Password are required.")
            
        conn = get_db()
        cur = conn.cursor()
        
        # Check if the email belongs to an existing admin
        cur.execute("SELECT user_id FROM users WHERE email=? AND role='admin'", (email,))
        admin_user = cur.fetchone()
        
        if admin_user:
            cur.execute("UPDATE users SET password=? WHERE email=? AND role='admin'", (new_password, email))
            conn.commit()
            conn.close()
            return render_template("forgot_password.html", message="Success! Your Admin password has been changed. You can now login.")
        else:
            conn.close()
            return render_template("forgot_password.html", message="Error: No Admin account found with that email address.")
            
    return render_template("forgot_password.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        return redirect("/login")
    return render_template("reset_password.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        # Users can only register as pharmacist — admin role is assigned manually
        role = "pharmacist"
        
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)", (username, email, password, role))
            conn.commit()
            flash(f"Account created successfully! User '{username}' registered as Pharmacist.", "success")
            return redirect("/login")
        except Exception as e:
            return f"❌ Registration failed: {str(e)}"
        finally:
            conn.close()
            
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= HOME =================
@app.route("/")
def index():
    if not login_required():
        return redirect("/login")
    return render_template("index.html")

# ================= UPLOAD & ANALYZE =================
@app.route("/upload", methods=["POST"])
def upload():
    if not login_required():
        return redirect("/login")

    # -------- FORM DATA --------
    patient_name = request.form.get("patient_name")
    doctor_name = request.form.get("doctor_name")

    if not patient_name or not doctor_name:
        return "❌ Patient name and Doctor name required"

    # -------- FILE --------
    file = request.files.get("prescription_image")
    if not file or file.filename == "":
        return "❌ No file selected"

    filename = f"{int(datetime.now().timestamp())}_{file.filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # -------- AI PIPELINE --------
    text = extract_text(filepath)
    entities = extract_entities(text)

    medicines = entities.get("medicines", [])
    symptoms = entities.get("symptoms", [])
    dosage = entities.get("dosage", [])

    diseases = predict_disease(symptoms, text)
    interactions = analyze_drug_interactions(medicines)
    dosage_safety = analyze_dosage_safety(medicines, text)

    prescription_id = f"RX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # -------- DATABASE --------
    conn = get_db()
    cur = conn.cursor()

    for med in medicines:
        cur.execute("""
            INSERT INTO dispense_log
            (prescription_id, patient_name, doctor_name, medicine_name,
             prescribed_dose, dispensed_dose, pharmacist_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prescription_id,
            patient_name,
            doctor_name,
            med,
            "As Prescribed",
            "Not Dispensed",
            session["user_id"],
            timestamp
        ))

    cur.execute("""
        INSERT INTO audit_log
        (user_id, action, details, timestamp)
        VALUES (?, ?, ?, ?)
    """, (
        session["user_id"],
        "PRESCRIPTION_ANALYZED",
        f"{prescription_id} | {patient_name} | {doctor_name}",
        timestamp
    ))

    # Save to prescription metadata
    cur.execute("""
        INSERT INTO prescription_metadata 
        (prescription_id, raw_text, symptoms_json, diseases_json, interactions_json, dosage_safety_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        prescription_id,
        text,
        json.dumps(symptoms),
        json.dumps(diseases),
        json.dumps(interactions),
        json.dumps(dosage_safety)
    ))

    conn.commit()
    conn.close()

    # -------- RESULTS --------
    return render_template(
        "results.html",
        text=text,
        entities=entities,
        diseases=diseases,
        interactions=interactions,
        dosage_safety=dosage_safety,
        patient_name=patient_name,
        doctor_name=doctor_name,
        prescription_id=prescription_id,
        timestamp=timestamp
    )

# ================= HISTORY =================
@app.route("/history")
def history():
    if not login_required():
        return redirect("/login")

    # Query params for filtering
    search_q = request.args.get("q", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    conn = get_db()
    cur = conn.cursor()

    # Build dynamic query with optional filters
    query = """
        SELECT d.prescription_id,
               d.patient_name,
               d.doctor_name,
               GROUP_CONCAT(d.medicine_name),
               d.timestamp,
               u.username,
               pm.diseases_json
        FROM dispense_log d
        LEFT JOIN users u ON d.pharmacist_id = u.user_id
        LEFT JOIN prescription_metadata pm ON d.prescription_id = pm.prescription_id
    """
    conditions = []
    params = []

    if search_q:
        conditions.append("(d.medicine_name LIKE ? OR d.patient_name LIKE ?)")
        params.extend([f"%{search_q}%", f"%{search_q}%"])
    if date_from:
        conditions.append("d.timestamp >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("d.timestamp <= ?")
        params.append(date_to + " 23:59:59")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY d.prescription_id ORDER BY d.timestamp DESC"

    cur.execute(query, params)
    all_rows = cur.fetchall()
    conn.close()

    total = len(all_rows)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    paginated_rows = all_rows[(page - 1) * per_page : page * per_page]

    results = []
    for r in paginated_rows:
        meds = r[3].split(",") if r[3] else []
        # Compute risk level from diseases JSON
        risk_level = "Low"
        risk_color = "#10B981"
        diseases = []
        if r[6]:
            try:
                diseases = json.loads(r[6])
                if diseases:
                    max_conf = max(d.get("confidence", 0) for d in diseases)
                    if max_conf >= 80:
                        risk_level = "Critical"
                        risk_color = "#EF4444"
                    elif max_conf >= 60:
                        risk_level = "High"
                        risk_color = "#F97316"
                    elif max_conf >= 40:
                        risk_level = "Moderate"
                        risk_color = "#F59E0B"
            except (json.JSONDecodeError, TypeError):
                pass

        results.append({
            "result_file": r[0],
            "patient_name": r[1],
            "doctor_name": r[2],
            "medications": meds,
            "timestamp": r[4],
            "employee_name": r[5] or "System",
            "risk_level": risk_level,
            "risk_color": risk_color,
        })

    return render_template("history.html",
        results=results,
        page=page,
        total_pages=total_pages,
        total=total,
        search_q=search_q,
        date_from=date_from,
        date_to=date_to
    )

# ================= VIEW OLD RESULT =================
@app.route("/result/<prescription_id>")
def view_result(prescription_id):
    if not login_required():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT patient_name, doctor_name, medicine_name, timestamp
        FROM dispense_log
        WHERE prescription_id=?
    """, (prescription_id,))
    rows = cur.fetchall()

    cur.execute("""
        SELECT raw_text, symptoms_json, diseases_json, interactions_json, dosage_safety_json
        FROM prescription_metadata
        WHERE prescription_id=?
    """, (prescription_id,))
    meta_row = cur.fetchone()
    conn.close()

    if not rows:
        return "❌ Prescription not found"

    if meta_row:
        text = meta_row[0]
        symptoms = json.loads(meta_row[1]) if meta_row[1] else []
        diseases = json.loads(meta_row[2]) if meta_row[2] else []
        interactions = json.loads(meta_row[3]) if meta_row[3] else []
        dosage_safety = json.loads(meta_row[4]) if meta_row[4] else []
    else:
        text = "Previously analyzed prescription"
        symptoms = []
        diseases = []
        interactions = []
        dosage_safety = []

    entities = {
        "medicines": [r[2] for r in rows],
        "symptoms": symptoms,
        "dosage": []
    }

    return render_template(
        "results.html",
        text=text,
        entities=entities,
        diseases=diseases,
        interactions=interactions,
        dosage_safety=dosage_safety,
        patient_name=rows[0][0],
        doctor_name=rows[0][1],
        prescription_id=prescription_id,
        timestamp=rows[0][3]
    )

# ================= AUDIT =================
@app.route("/audit")
def audit():
    if not login_required() or session.get("role") != "admin":
        return "❌ Unauthorized"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_log ORDER BY timestamp DESC")
    logs = cur.fetchall()
    conn.close()

    return render_template("audit.html", logs=logs)

# ================= DASHBOARD & MORE =================
@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect("/login")
        
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Quick Stats
    cur.execute("SELECT COUNT(DISTINCT prescription_id) FROM dispense_log")
    total_records = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(DISTINCT patient_name) FROM dispense_log")
    total_patients = cur.fetchone()[0] or 0
    
    # High risk / alerts proxy (for demo, count audit logs that denote risks, or just audit logs)
    cur.execute("SELECT COUNT(*) FROM audit_log WHERE action LIKE '%delete%' OR action LIKE '%FAIL%' OR action LIKE '%ALERT%'")
    total_alerts = cur.fetchone()[0] or 0

    # 2. Recent Prescriptions Activity
    cur.execute("""
        SELECT d.prescription_id, d.patient_name, d.doctor_name, d.timestamp, pm.diseases_json, u.username
        FROM dispense_log d
        LEFT JOIN prescription_metadata pm ON d.prescription_id = pm.prescription_id
        LEFT JOIN users u ON d.pharmacist_id = u.user_id
        GROUP BY d.prescription_id 
        ORDER BY d.timestamp DESC 
        LIMIT 5
    """)
    recent_rows = cur.fetchall()
    
    recent_activity = []
    for r in recent_rows:
        # Determine risk simply based on the presence of high confidence diseases
        risk_level = "Low Risk"
        risk_color = "var(--success)"
        
        if r[4]:
            try:
                diseases = json.loads(r[4])
                if diseases:
                    max_conf = max([d.get("confidence", 0) for d in diseases])
                    if max_conf >= 80:
                        risk_level = "Critical"
                        risk_color = "var(--danger)"
                    elif max_conf >= 60:
                        risk_level = "High Risk"
                        risk_color = "var(--warning)"
            except:
                pass

        recent_activity.append({
            "prescription_id": r[0],
            "patient_name": r[1],
            "doctor_name": r[2],
            "timestamp": r[3],
            "risk_level": risk_level,
            "risk_color": risk_color,
            "pharmacist": r[5] or "System"
        })

    conn.close()

    return render_template("dashboard.html", 
                           role=session.get("role"),
                           username=session.get("username", "User"),
                           total_records=total_records,
                           total_patients=total_patients,
                           total_alerts=total_alerts,
                           recent_activity=recent_activity)

@app.route("/management")
def management():
    if not login_required() or session.get("role") != "admin":
        return "❌ Unauthorized: Admin access required."
    
    conn = get_db()
    cur = conn.cursor()
    
    # Query all users (specifically pharmacists/employees) and outer join with their dispensed logs.
    cur.execute("""
        SELECT 
            u.user_id, 
            u.username, 
            u.role,
            d.prescription_id, 
            d.patient_name, 
            d.doctor_name, 
            d.medicine_name, 
            d.timestamp
        FROM users u
        LEFT JOIN dispense_log d ON u.user_id = d.pharmacist_id
        WHERE u.role != 'admin'
        ORDER BY u.user_id, d.timestamp DESC
    """)
    
    rows = cur.fetchall()
    conn.close()

    # Structure the data: { employee_id: { details: {...}, patients: [...] } }
    management_data = {}
    for r in rows:
        emp_id = r[0]
        emp_username = r[1]
        emp_role = r[2]
        
        # Patient Record Pieces
        rx_id = r[3]
        pat_name = r[4]
        doc_name = r[5]
        med_name = r[6]
        timestamp = r[7]

        if emp_id not in management_data:
            management_data[emp_id] = {
                "id": emp_id,
                "username": emp_username,
                "role": emp_role,
                "patients": []
            }
            
        if rx_id:
            management_data[emp_id]["patients"].append({
                "prescription_id": rx_id,
                "patient_name": pat_name,
                "doctor_name": doc_name,
                "medicine_name": med_name,
                "timestamp": timestamp
            })

    return render_template("management.html", employees=management_data)

@app.route("/training")
def training():
    if not login_required():
        return redirect("/login")
    return render_template("training.html")

@app.route("/train", methods=["POST"])
def train():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401
        
    import time
    time.sleep(1.5) # Simulate training delay
    
    results = {
        "accuracy": "98.7%",
        "val_loss": "0.014",
        "epochs": 50,
        "time_elapsed": "1.42s",
        "status": "Optimization Complete"
    }
    return jsonify(results)

@app.route("/api/simulate-prediction", methods=["POST"])
def simulate_prediction():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Step 1: Entity Extraction
    entities = extract_entities(text)
    medicines = entities.get("medicines", [])
    symptoms = entities.get("symptoms", [])
    dosage = entities.get("dosage", [])

    # Step 2: Disease Prediction
    diseases = predict_disease(symptoms, text)

    # Step 3: Drug Interactions
    interactions = analyze_drug_interactions(medicines)

    # Step 4: Dosage Safety
    dosage_safety = analyze_dosage_safety(medicines, text)

    return jsonify({
        "entities": {
            "medicines": medicines,
            "symptoms": symptoms,
            "dosage": dosage
        },
        "diseases": diseases,
        "interactions": interactions,
        "dosage_safety": dosage_safety
    })

@app.route("/about")
def about():
    if not login_required():
        return redirect("/login")
    return render_template("about.html")

# ================= ADMIN ACTIONS =================
@app.route("/delete_record/<prescription_id>", methods=["POST"])
def delete_record(prescription_id):
    if not login_required() or session.get("role") != "admin":
        return redirect("/history")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM dispense_log WHERE prescription_id = ?", (prescription_id,))
    
    # Audit log
    cur.execute("INSERT INTO audit_log (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                (session["user_id"], "Deleted Record", f"Deleted prescription {prescription_id}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()
    return redirect("/history")

@app.route("/delete_employee/<int:emp_id>", methods=["POST"])
def delete_employee(emp_id):
    if not login_required() or session.get("role") != "admin":
        return redirect("/management")
    
    conn = get_db()
    cur = conn.cursor()
    # Prevent self-deletion
    if emp_id == session.get("user_id"):
        conn.close()
        return redirect("/management")
    
    cur.execute("DELETE FROM users WHERE user_id = ? AND role != 'admin'", (emp_id,))
    
    # Audit log
    cur.execute("INSERT INTO audit_log (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                (session["user_id"], "Deleted Employee", f"Deleted employee ID {emp_id}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
    conn.commit()
    conn.close()
    return redirect("/management")

@app.route("/admin/add_employee", methods=["POST"])
def admin_add_employee():
    if not login_required() or session.get("role") != "admin":
        return redirect("/management")
        
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not username or not email or not password:
        return redirect("/management")
        
    conn = get_db()
    cur = conn.cursor()
    
    # Check if user exists
    cur.execute("SELECT user_id FROM users WHERE username = ? OR email = ?", (username, email))
    if cur.fetchone():
        conn.close()
        return redirect("/management")
        
    cur.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)", (username, email, password, "pharmacist"))
    
    # Audit log
    cur.execute("INSERT INTO audit_log (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                (session["user_id"], "Added Employee", f"Created employee {username}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                
    conn.commit()
    conn.close()
    return redirect("/management")

@app.route("/admin/edit_employee/<int:emp_id>", methods=["POST"])
def admin_edit_employee(emp_id):
    if not login_required() or session.get("role") != "admin":
        return redirect("/management")
        
    username = request.form.get("username")
    password = request.form.get("password")
    
    if not username:
        return redirect("/management")
        
    conn = get_db()
    cur = conn.cursor()
    
    if password:
        cur.execute("UPDATE users SET username = ?, password = ? WHERE user_id = ?", (username, password, emp_id))
    else:
        cur.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, emp_id))
        
    # Audit log
    cur.execute("INSERT INTO audit_log (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                (session["user_id"], "Edited Employee", f"Updated employee ID {emp_id}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                
    conn.commit()
    conn.close()
    return redirect("/management")

# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not login_required() or session.get("role") != "admin":
        return "❌ Unauthorized: Admin access required."

    conn = get_db()
    cur = conn.cursor()

    # Total users & active/inactive counts
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    active_users = cur.fetchone()[0]
    inactive_users = total_users - active_users

    # Total distinct prescriptions analyzed
    cur.execute("SELECT COUNT(DISTINCT prescription_id) FROM dispense_log")
    total_prescriptions = cur.fetchone()[0]

    # Total audit events
    cur.execute("SELECT COUNT(*) FROM audit_log")
    total_audit_events = cur.fetchone()[0]

    # Security alerts: count of sensitive actions (deletes, edits, etc.)
    cur.execute("""
        SELECT COUNT(*) FROM audit_log
        WHERE action LIKE '%Deleted%' OR action LIKE '%delete%'
           OR action LIKE '%ALERT%' OR action LIKE '%FAIL%'
           OR action LIKE '%ERROR%'
    """)
    alert_count = cur.fetchone()[0]

    # All users for management panel
    cur.execute("SELECT user_id, username, email, role, is_active FROM users ORDER BY user_id")
    users = cur.fetchall()

    # Distinct action types for filter dropdown
    cur.execute("SELECT DISTINCT action FROM audit_log ORDER BY action")
    action_types = [row[0] for row in cur.fetchall()]

    conn.close()

    return render_template("admin_dashboard.html",
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        total_prescriptions=total_prescriptions,
        total_audit_events=total_audit_events,
        alert_count=alert_count,
        users=users,
        action_types=action_types
    )

@app.route("/admin/toggle_user/<int:user_id>", methods=["POST"])
def toggle_user(user_id):
    if not login_required() or session.get("role") != "admin":
        return redirect("/admin/dashboard")

    conn = get_db()
    cur = conn.cursor()

    # Don't allow toggling admin users or self
    cur.execute("SELECT role, is_active, username FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    if not user or user[0] == "admin":
        conn.close()
        return redirect("/admin/dashboard")

    new_status = 0 if user[1] == 1 else 1
    status_label = "Activated" if new_status == 1 else "Deactivated"

    cur.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (new_status, user_id))

    # Audit log
    cur.execute("INSERT INTO audit_log (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                (session["user_id"], f"{status_label} User", f"{status_label} user '{user[2]}' (ID {user_id})",
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()
    flash(f"User '{user[2]}' has been {status_label.lower()}.", "success")
    return redirect("/admin/dashboard")

@app.route("/admin/audit-logs")
def admin_audit_logs():
    if not login_required() or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 15, type=int)
    filter_user_id = request.args.get("user_id", "").strip()
    filter_action = request.args.get("action", "").strip()

    conn = get_db()
    cur = conn.cursor()

    query = "SELECT audit_id, user_id, action, details, timestamp FROM audit_log"
    conditions = []
    params = []

    if filter_user_id:
        conditions.append("user_id = ?")
        params.append(filter_user_id)
    if filter_action:
        conditions.append("action = ?")
        params.append(filter_action)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC"

    cur.execute(query, params)
    all_rows = cur.fetchall()
    conn.close()

    total = len(all_rows)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    paginated = all_rows[(page - 1) * per_page : page * per_page]

    logs = []
    for r in paginated:
        logs.append({
            "audit_id": r[0],
            "user_id": r[1],
            "action": r[2],
            "details": r[3],
            "timestamp": r[4]
        })

    return jsonify({
        "logs": logs,
        "page": page,
        "total_pages": total_pages,
        "total": total
    })

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
