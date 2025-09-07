# Campus-Event-Management-Reporting-System-prototype

Built this in a tight time constraint. 

I went with Flask + SQLite because it’s lightweight, fast to prototype, and gets the job done without overcomplicating things. No fancy ORMs, no bloated setups — just raw endpoints, clean SQL, and working reports.

I manually tested everything in Postman
Tables:
1.created students
2.events
3.registrations
4.marked attendance
5.submitted feedback 
Didn’t rely on auto-seed (even though it’s there) because I wanted to prove the full flow works start to finish.

Used prefixed IDs like COL01_STU001 and COL01_EV001 to keep things organized across colleges — made sense for scale, even in a prototype.

I have handled Reports in the below manner:
- Total registrations per event
- Attendance percentage
- Average feedback 
- Bonus: Top 3 most active students

All endpoints return clean JSON. No frontend needed — Postman screenshots prove it works.

If you wanna run it:
1. cli> pip install flask
2. cli> python app.py
3. Hit the endpoints in Postman (or curl) — start with creating a student + event, then register, attend, feedback, then hit reports.

I did. While debugging, restarting Flask 10 times, and ignoring that endless “database locked” panic. 

This isn’t perfect — but it’s functional, documented, and delivered on time. And that’s what matters.