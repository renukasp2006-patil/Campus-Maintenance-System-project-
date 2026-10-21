
from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "campus.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            problem TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(requests)")
    }

    columns = {
        "student_mobile": "TEXT",
        "student_email": "TEXT",
        "teacher_mobile": "TEXT",
        "teacher_email": "TEXT"
    }

    for name, kind in columns.items():
        if name not in existing:
            conn.execute(
                f"ALTER TABLE requests ADD COLUMN {name} {kind}"
            )

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def files(filename):
    return send_from_directory(BASE_DIR, filename)


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({
            "message": "Enter username and password."
        }), 400

    conn = get_db()

    try:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()

        return jsonify({
            "message": "Registration successful!"
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "message": "Username already exists!"
        }), 400

    finally:
        conn.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()

    conn.close()

    if user:
        return jsonify({
            "message": "Login successful!",
            "username": user["username"]
        })

    return jsonify({
        "message": "Invalid username or password!"
    }), 401


@app.route("/api/requests", methods=["POST"])
def add_request():
    data = request.get_json(silent=True) or {}

    fields = [
        "student_name",
        "student_mobile",
        "student_email",
        "teacher_mobile",
        "teacher_email",
        "category",
        "location",
        "problem",
        "date"
    ]

    values = [
        str(data.get(field, "")).strip()
        for field in fields
    ]

    if not all(values):
        return jsonify({
            "message": "Please fill in all required fields."
        }), 400

    conn = get_db()

    try:
        cursor = conn.execute("""
            INSERT INTO requests (
                student_name,
                student_mobile,
                student_email,
                teacher_mobile,
                teacher_email,
                category,
                location,
                problem,
                date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, values)

        conn.commit()

        return jsonify({
            "message": "Maintenance request submitted!",
            "request_id": cursor.lastrowid
        }), 201

    finally:
        conn.close()


@app.route("/api/requests", methods=["GET"])
def get_requests():
    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM requests ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/requests/<int:request_id>", methods=["PUT"])
def update_status(request_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    allowed_statuses = [
        "Pending",
        "Accepted",
        "In Progress",
        "Completed"
    ]

    if status not in allowed_statuses:
        return jsonify({
            "message": "Invalid status!"
        }), 400

    conn = get_db()

    try:
        cursor = conn.execute(
            "UPDATE requests SET status=? WHERE id=?",
            (status, request_id)
        )

        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({
                "message": "Request not found!"
            }), 404

        return jsonify({
            "message": "Status updated successfully!",
            "request_id": request_id,
            "status": status
        })

    finally:
        conn.close()


@app.route("/api/requests/<int:request_id>", methods=["GET"])
def get_request(request_id):
    conn = get_db()

    try:
        row = conn.execute(
            "SELECT * FROM requests WHERE id=?",
            (request_id,)
        ).fetchone()

        if row:
            return jsonify(dict(row))

        return jsonify({
            "message": "Request not found!"
        }), 404

    finally:
        conn.close()


if __name__ == "__main__":
    create_database()

    print("Database connected successfully!")
    print("Campus Maintenance Backend Started!")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
