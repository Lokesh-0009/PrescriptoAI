from flask import Blueprint, render_template, request, redirect, session
from database import get_db
from datetime import datetime

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id, role FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cur.fetchone()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[1]

            # Update last login
            cur.execute(
                "UPDATE users SET last_login=? WHERE user_id=?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user[0])
            )
            conn.commit()
            conn.close()

            return redirect("/dashboard")

        conn.close()
        return "❌ Invalid credentials"

    return render_template("login.html")


@auth.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
