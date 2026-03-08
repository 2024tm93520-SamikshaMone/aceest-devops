import os
import sqlite3
from flask import Flask, jsonify, request

app = Flask(__name__)

# The original ACEest app was a Tkinter desktop application. Since Tkinter
# needs a display server and Docker containers don't have one, I've converted
# the business logic into a Flask REST API. All program data, calorie factors
# and DB schema are taken directly from the original source files provided.

DB_PATH = os.environ.get("DB_PATH", "aceest_fitness.db")

# Program data from Aceestver-1.1.py (first version with calorie_factor)
PROGRAMS = {
    "Fat Loss (FL)": {
        "workout": (
            "Mon: Back Squat 5x5 + Core\n"
            "Tue: EMOM 20min Assault Bike\n"
            "Wed: Bench Press + 21-15-9\n"
            "Thu: Deadlift + Box Jumps\n"
            "Fri: Zone 2 Cardio 30min"
        ),
        "diet": (
            "Breakfast: Egg Whites + Oats\n"
            "Lunch: Grilled Chicken + Brown Rice\n"
            "Dinner: Fish Curry + Millet Roti\n"
            "Target: ~2000 kcal"
        ),
        "calorie_factor": 22
    },
    "Muscle Gain (MG)": {
        "workout": (
            "Mon: Squat 5x5\n"
            "Tue: Bench 5x5\n"
            "Wed: Deadlift 4x6\n"
            "Thu: Front Squat 4x8\n"
            "Fri: Incline Press 4x10\n"
            "Sat: Barbell Rows 4x10"
        ),
        "diet": (
            "Breakfast: Eggs + Peanut Butter Oats\n"
            "Lunch: Chicken Biryani\n"
            "Dinner: Mutton Curry + Jeera Rice\n"
            "Target: ~3200 kcal"
        ),
        "calorie_factor": 35
    },
    "Beginner (BG)": {
        "workout": (
            "Full Body Circuit:\n"
            "- Air Squats\n"
            "- Ring Rows\n"
            "- Push-ups\n"
            "Focus: Technique & Consistency"
        ),
        "diet": (
            "Balanced Tamil Meals\n"
            "Idli / Dosa / Rice + Dal\n"
            "Protein Target: 120g/day"
        ),
        "calorie_factor": 26
    }
}


def get_db():
    # re-read env var on every call so tests can point to a temp file
    path = os.environ.get("DB_PATH", DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # schema matches Aceestver-2.1.2.py which first introduced SQLite
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT UNIQUE NOT NULL,
            age      INTEGER,
            weight   REAL,
            program  TEXT,
            calories INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            week        TEXT,
            adherence   INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.route("/")
def home():
    return jsonify({
        "message": "ACEest Fitness & Gym API",
        "status": "running",
        "version": "1.0"
    })


@app.route("/health")
def health():
    # used by Docker HEALTHCHECK and Jenkins pipeline to verify app is up
    return jsonify({"status": "ok"}), 200


@app.route("/api/programs", methods=["GET"])
def get_programs():
    result = {}
    for name, data in PROGRAMS.items():
        result[name] = {
            "workout": data["workout"],
            "diet": data["diet"],
            "calorie_factor": data["calorie_factor"]
        }
    return jsonify(result)


@app.route("/api/calories", methods=["POST"])
def calculate_calories():
    # original formula from Aceestver-2.1.2.py:
    # calories = int(self.weight.get() * self.programs[program]["factor"])
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "request body is missing"}), 400

    weight = data.get("weight")
    program = data.get("program")

    if weight is None or program is None:
        return jsonify({"error": "weight and program are both required"}), 400

    if not isinstance(weight, (int, float)) or weight <= 0:
        return jsonify({"error": "weight must be a positive number"}), 400

    if program not in PROGRAMS:
        return jsonify({"error": f"program '{program}' not found"}), 404

    calories = int(weight * PROGRAMS[program]["calorie_factor"])

    return jsonify({
        "weight": weight,
        "program": program,
        "estimated_calories": calories
    })


@app.route("/api/clients", methods=["GET"])
def get_all_clients():
    conn = get_db()
    rows = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/clients", methods=["POST"])
def add_client():
    # mirrors save_client() from the original desktop app
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "request body is missing"}), 400

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "client name is required"}), 400

    program = (data.get("program") or "").strip()
    if program and program not in PROGRAMS:
        return jsonify({"error": f"program '{program}' not found"}), 404

    age = data.get("age")
    weight = data.get("weight")

    calories = None
    if weight and program:
        calories = int(weight * PROGRAMS[program]["calorie_factor"])

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO clients (name, age, weight, program, calories)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, age, weight, program or None, calories)
        )
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

    conn.close()
    return jsonify({
        "message": "client saved successfully",
        "name": name,
        "calories": calories
    }), 201


@app.route("/api/clients/<client_name>", methods=["GET"])
def get_client(client_name):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM clients WHERE name = ?", (client_name,)
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "client not found"}), 404

    return jsonify(dict(row))


@app.route("/api/progress", methods=["POST"])
def save_progress():
    # mirrors save_progress() from Aceestver-2.1.2.py
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "request body is missing"}), 400

    client_name = (data.get("client_name") or "").strip()
    week = (data.get("week") or "").strip()
    adherence = data.get("adherence")

    if not client_name or not week or adherence is None:
        return jsonify({"error": "client_name, week and adherence are required"}), 400

    if not isinstance(adherence, int) or not (0 <= adherence <= 100):
        return jsonify({"error": "adherence must be an integer between 0 and 100"}), 400

    conn = get_db()
    conn.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
        (client_name, week, adherence)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "message": "progress saved",
        "client_name": client_name,
        "week": week,
        "adherence": adherence
    }), 201


@app.route("/api/progress/<client_name>", methods=["GET"])
def get_progress(client_name):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM progress WHERE client_name = ? ORDER BY id",
        (client_name,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
