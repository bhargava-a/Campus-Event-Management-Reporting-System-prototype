# Campus Event Reporting System — Design Doc

## Assumptions & Decisions
**Event IDs are globally unique** → I prefixed them like `COL01_EV001` so 50 colleges won’t collide. Simple. Works.
**One DB for all colleges** → Easier to query reports across campuses. If this scaled to 5000 colleges, I’d shard — but not today.

**Feedback optional** → Students can skip rating. AVG() ignores NULLs — handled in SQL.
**Duplicate regs?** → Blocked at DB level with `PRIMARY KEY (student_id, event_id)`. No app-level check needed.
**Cancelled events?** → Added `cancelled` flag. Reports filter them out. Clean.
**Attendance before registration?** → Allowed. Maybe student walked in last minute. Real world is messy.

## Database Schema (SQLite)

Used 6 tables:

`colleges` → id, name
`students` → id (e.g., COL01_STU001), name, email, college_id
`events` → id (e.g., COL01_EV001), name, type, date, college_id, cancelled
`registrations` → (student_id, event_id) → composite PK → no duplicates
`attendance` → (student_id, event_id) → marked present/absent
`feedback` → (student_id, event_id) → rating 1-5, optional comment

## API Endpoints (Flask)

All JSON. All simple.

### POST Endpoints (Write Data)
`POST /students` → Create student (send id, name, email, college_id)
`POST /events` → Create event (send id, name, type, date, college_id)
`POST /register` → Register student for event
`POST /attendance` → Mark if student attended
`POST /feedback` → Submit rating + comment

### GET Endpoints (Reports — Read Only)
`GET /reports/registrations` → Event name + total signups
`GET /reports/attendance` → Event name + % who showed up
`GET /reports/feedback` → Event name + avg rating (ignores NULLs)
`GET /reports/top-students` → Top 3 students by events attended (BONUS)
`GET /reports/events?type=Workshop` → Filter events by type (BONUS)

## Workflows (In My Head — Didn’t Draw Diagrams, But Here’s Logic)

### Registration
Student → POST /register → DB inserts (student_id, event_id) → 201 OK or 400 if duplicate.

### Attendance
Staff scans QR or types ID → POST /attendance → Upsert (student_id, event_id, attended=1) → Done.

### Reporting
Admin clicks “Show Popular Events” → GET /reports/registrations → SQL COUNT + JOIN → Returns sorted list.

## Edge Cases I Handled

**Duplicate registration** → DB constraint blocks it → returns 400
**Feedback without attendance** → Allowed. Maybe student hated it and left early.
**Event cancelled** → Excluded from all reports → WHERE cancelled = 0
**No feedback for event** → AVG(rating) returns NULL → COALESCE(…, 0) → shows 0.0
**Student registers twice** → Impossible. Composite PK.

## Scale Assumption (50 Colleges, 500 Students, 20 Events)

Max rows: 50 * 500 * 20 = 500,000 registrations → SQLite handles this fine for prototype.
or production? → PostgreSQL + connection pooling + read replicas.
Event IDs unique across colleges → `COL{id}_EV{id}` → no collisions.

