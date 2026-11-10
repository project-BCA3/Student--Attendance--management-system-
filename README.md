# Student Attendance Management System (No Face Recognition)

## Features
- Student registration and login (passwords stored as salted PBKDF2 hashes)
- Student marks Present/Absent for a subject
- Attendance window: 9:00 AM–4:15 PM using the computer/server local time
- Duplicate prevention: one entry per student, subject and date
- CR dashboard to verify or reject entries
- Teacher dashboard with date/subject filters, metrics, charts and CSV export
- Defaulter list for attendance below 75%
- Basic rule-based attendance insights (no paid AI API required)

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Create and activate a virtual environment (recommended).
4. Install dependencies:
   `pip install -r requirements.txt`
5. Start the app:
   `streamlit run app.py`
6. Open the local URL shown in the terminal (usually http://localhost:8501).

## Demo logins
- Teacher: `teacher@demo.com` / `Teacher@123`
- CR: `cr@demo.com` / `CR@12345`
- Students: use Register to create a student account.

## Database
The app creates `attendance.db` automatically in the project folder. Back it up before deleting or moving the project.

## Important project notes
- This is a working academic prototype, not a production attendance/security system.
- It deliberately does not use face recognition, biometrics, GPS, email OTP or Gemini.
- SQLite is used so the project works immediately without cloud credentials. For a multi-device college deployment, migrate to Firebase/Firestore or a hosted database and add proper server-side authorization.
- The time window uses the machine's local clock. A real deployment should enforce time on the server.
- CR verification is a workflow check, not proof that the student was physically present.
- Change demo passwords and add stronger admin controls before any real use.

## Suggested BCA report chapters
1. Introduction and problem statement
2. Existing system and proposed system
3. Requirements and feasibility
4. System design (DFD, ER diagram, flowchart)
5. Database design
6. Module implementation
7. Testing and screenshots
8. Limitations and future scope
9. Conclusion and bibliography
