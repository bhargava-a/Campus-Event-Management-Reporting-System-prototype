from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_NAME = "campus.db"

# ---------- DB INIT ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Colleges (optional, for scale)
    c.execute('''CREATE TABLE IF NOT EXISTS colleges (
                    id TEXT PRIMARY KEY,
                    name TEXT
                )''')

    # Students
    c.execute('''CREATE TABLE IF NOT EXISTS students (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    college_id TEXT
                )''')

    # Events
    c.execute('''CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    type TEXT CHECK(type IN ('Workshop', 'Hackathon', 'Fest', 'Seminar')),
                    date TEXT,
                    college_id TEXT,
                    cancelled INTEGER DEFAULT 0
                )''')

    # Registrations — composite key prevents duplicates
    c.execute('''CREATE TABLE IF NOT EXISTS registrations (
                    student_id TEXT,
                    event_id TEXT,
                    registered_on TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (student_id, event_id),
                    FOREIGN KEY(student_id) REFERENCES students(id),
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )''')

    # Attendance — by student + event, not reg_id
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                    student_id TEXT,
                    event_id TEXT,
                    attended INTEGER DEFAULT 1,
                    checked_in_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (student_id, event_id),
                    FOREIGN KEY(student_id) REFERENCES students(id),
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )''')

    # Feedback — by student + event
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                    student_id TEXT,
                    event_id TEXT,
                    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
                    comment TEXT,
                    submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (student_id, event_id),
                    FOREIGN KEY(student_id) REFERENCES students(id),
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )''')

    conn.commit()
    conn.close()

# ---------- HELPERS ----------
def query_db(query, args=(), one=False, commit=True):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    if commit:
        conn.commit()
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# ---------- ENDPOINTS ----------

# Create Student
@app.route("/students", methods=["POST"])
def create_student():
    data = request.json
    query_db("INSERT INTO students (id, name, email, college_id) VALUES (?,?,?,?)",
             (data["id"], data["name"], data["email"], data["college_id"]))
    return jsonify({"message": "Student created", "student_id": data["id"]}), 201

# Create Event
@app.route("/events", methods=["POST"])
def create_event():
    data = request.json
    query_db("INSERT INTO events (id, name, type, date, college_id) VALUES (?,?,?,?,?)",
             (data["id"], data["name"], data["type"], data["date"], data["college_id"]))
    return jsonify({"message": "Event created", "event_id": data["id"]}), 201

# Register Student for Event
@app.route("/register", methods=["POST"])
def register_event():
    data = request.json
    try:
        query_db("INSERT INTO registrations (student_id, event_id) VALUES (?,?)",
                 (data["student_id"], data["event_id"]))
        return jsonify({"message": "Registration successful"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Already registered"}), 400

# Mark Attendance
@app.route("/attendance", methods=["POST"])
def mark_attendance():
    data = request.json
    query_db("INSERT OR REPLACE INTO attendance (student_id, event_id, attended) VALUES (?,?,?)",
             (data["student_id"], data["event_id"], int(data.get("attended", 1))))
    return jsonify({"message": "Attendance marked"}), 201

# Submit Feedback
@app.route("/feedback", methods=["POST"])
def submit_feedback():
    data = request.json
    query_db("INSERT OR REPLACE INTO feedback (student_id, event_id, rating, comment) VALUES (?,?,?,?)",
             (data["student_id"], data["event_id"], data["rating"], data.get("comment", "")))
    return jsonify({"message": "Feedback submitted"}), 201

# ---------- REPORTS ----------

@app.route("/reports/registrations", methods=["GET"])
def report_registrations():
    rows = query_db('''SELECT e.id, e.name, COUNT(r.student_id) AS total_registrations
                       FROM events e
                       LEFT JOIN registrations r ON e.id = r.event_id
                       WHERE e.cancelled = 0
                       GROUP BY e.id
                       ORDER BY total_registrations DESC''')
    return jsonify([dict(row) for row in rows])

@app.route("/reports/attendance", methods=["GET"])
def report_attendance():
    rows = query_db('''SELECT e.id, e.name,
                              COALESCE(ROUND(100.0 * SUM(CASE WHEN a.attended=1 THEN 1 ELSE 0 END) / COUNT(r.student_id), 2), 0) AS attendance_percentage
                       FROM events e
                       JOIN registrations r ON e.id = r.event_id
                       LEFT JOIN attendance a ON r.student_id = a.student_id AND r.event_id = a.event_id
                       WHERE e.cancelled = 0
                       GROUP BY e.id''')
    return jsonify([dict(row) for row in rows])

@app.route("/reports/feedback", methods=["GET"])
def report_feedback():
    rows = query_db('''SELECT e.id, e.name, COALESCE(ROUND(AVG(f.rating), 2), 0) AS avg_feedback
                       FROM events e
                       JOIN feedback f ON e.id = f.event_id
                       WHERE e.cancelled = 0
                       GROUP BY e.id''')
    return jsonify([dict(row) for row in rows])

# BONUS: Top 3 most active students (by events attended)
@app.route("/reports/top-students", methods=["GET"])
def report_top_students():
    rows = query_db('''SELECT s.id, s.name, COUNT(a.event_id) AS events_attended
                       FROM students s
                       JOIN attendance a ON s.id = a.student_id AND a.attended = 1
                       GROUP BY s.id
                       ORDER BY events_attended DESC
                       LIMIT 3''')
    return jsonify([dict(row) for row in rows])

# BONUS: Filter events by type
@app.route("/reports/events", methods=["GET"])
def report_events_by_type():
    event_type = request.args.get('type')
    if not event_type:
        return jsonify({"error": "Missing 'type' query param"}), 400
    rows = query_db('''SELECT id, name, date
                       FROM events
                       WHERE type = ? AND cancelled = 0''', (event_type,))
    return jsonify([dict(row) for row in rows])

# BONUS: Seed sample data (for demo)
@app.route("/seed", methods=["GET"])
def seed_data():
    # Insert 1 college
    query_db("INSERT OR IGNORE INTO colleges (id, name) VALUES ('COL01', 'Tech College')")

    # Insert 2 students
    query_db("INSERT OR IGNORE INTO students (id, name, email, college_id) VALUES ('COL01_STU001', 'Alice', 'alice@edu.com', 'COL01')")
    query_db("INSERT OR IGNORE INTO students (id, name, email, college_id) VALUES ('COL01_STU002', 'Bob', 'bob@edu.com', 'COL01')")

    # Insert 2 events
    query_db("INSERT OR IGNORE INTO events (id, name, type, date, college_id) VALUES ('COL01_EV001', 'AI Workshop', 'Workshop', '2025-09-10', 'COL01')")
    query_db("INSERT OR IGNORE INTO events (id, name, type, date, college_id) VALUES ('COL01_EV002', 'Hackathon', 'Hackathon', '2025-09-15', 'COL01')")

    # Register students
    query_db("INSERT OR IGNORE INTO registrations (student_id, event_id) VALUES ('COL01_STU001', 'COL01_EV001')")
    query_db("INSERT OR IGNORE INTO registrations (student_id, event_id) VALUES ('COL01_STU002', 'COL01_EV001')")
    query_db("INSERT OR IGNORE INTO registrations (student_id, event_id) VALUES ('COL01_STU001', 'COL01_EV002')")

    # Mark attendance
    query_db("INSERT OR REPLACE INTO attendance (student_id, event_id, attended) VALUES ('COL01_STU001', 'COL01_EV001', 1)")
    query_db("INSERT OR REPLACE INTO attendance (student_id, event_id, attended) VALUES ('COL01_STU002', 'COL01_EV001', 0)")
    query_db("INSERT OR REPLACE INTO attendance (student_id, event_id, attended) VALUES ('COL01_STU001', 'COL01_EV002', 1)")

    # Submit feedback
    query_db("INSERT OR REPLACE INTO feedback (student_id, event_id, rating) VALUES ('COL01_STU001', 'COL01_EV001', 5)")
    query_db("INSERT OR REPLACE INTO feedback (student_id, event_id, rating) VALUES ('COL01_STU001', 'COL01_EV002', 4)")

    return jsonify({"message": "Sample data seeded!"})

# ---------- RUN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)