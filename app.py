import streamlit as st
import sqlite3, hashlib, secrets, csv, io
from datetime import datetime, date, time, timedelta
import pandas as pd
import plotly.express as px

DB = "attendance.db"
st.set_page_config(page_title="Student Attendance Management", page_icon="🎓", layout="wide")

def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 150000).hex()
    return f"{salt}${digest}"

def check_pw(pw, stored):
    try:
        salt, digest = stored.split("$", 1)
        return secrets.compare_digest(hash_pw(pw, salt).split("$",1)[1], digest)
    except Exception:
        return False

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, roll TEXT UNIQUE, name TEXT NOT NULL,
          course TEXT, semester TEXT, email TEXT UNIQUE, password TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'student', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS subjects(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
          teacher TEXT
        );
        CREATE TABLE IF NOT EXISTS attendance(
          id INTEGER PRIMARY KEY AUTOINCREMENT, roll TEXT NOT NULL, subject TEXT NOT NULL,
          day TEXT NOT NULL, status TEXT NOT NULL, marked_time TEXT NOT NULL,
          verified INTEGER NOT NULL DEFAULT 0, verified_by TEXT,
          UNIQUE(roll, subject, day)
        );
        """)
        # Demo accounts are created only on first run.
        if not c.execute("SELECT 1 FROM users WHERE role='teacher'").fetchone():
            c.execute("INSERT INTO users(roll,name,course,semester,email,password,role,created_at) VALUES(?,?,?,?,?,?,?,?)",
                      ("T001","Demo Teacher","BCA","3","teacher@demo.com",hash_pw("Teacher@123"),"teacher",datetime.now().isoformat(timespec="seconds")))
        if not c.execute("SELECT 1 FROM users WHERE role='cr'").fetchone():
            c.execute("INSERT INTO users(roll,name,course,semester,email,password,role,created_at) VALUES(?,?,?,?,?,?,?,?)",
                      ("CR001","Class Representative","BCA","3","cr@demo.com",hash_pw("CR@12345"),"cr",datetime.now().isoformat(timespec="seconds")))
        if not c.execute("SELECT 1 FROM subjects").fetchone():
            c.executemany("INSERT INTO subjects(name,teacher) VALUES(?,?)",
                          [("Python Programming","Demo Teacher"),("Database Management","Demo Teacher"),("Web Development","Demo Teacher")])

def q(sql, params=()):
    with conn() as c:
        return c.execute(sql, params).fetchall()

def run(sql, params=()):
    with conn() as c:
        c.execute(sql, params)
        c.commit()

def get_subjects():
    return [r["name"] for r in q("SELECT name FROM subjects ORDER BY name")]

init_db()
if "user" not in st.session_state:
    st.session_state.user = None

st.title("🎓 Student Attendance Management System")
st.caption("Without face recognition or biometrics • Student marking • CR verification • Teacher dashboard")

with st.sidebar:
    st.header("Navigation")
    if st.session_state.user:
        u = st.session_state.user
        st.success(f"Logged in: {u['name']} ({u['role'].upper()})")
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    st.markdown("---")
    st.caption("Demo logins")
    st.code("Teacher: teacher@demo.com\nPassword: Teacher@123\n\nCR: cr@demo.com\nPassword: CR@12345")

user = st.session_state.user

def register_page():
    st.subheader("Student registration")
    with st.form("register"):
        roll = st.text_input("Roll number *").strip().upper()
        name = st.text_input("Full name *").strip()
        course = st.selectbox("Course", ["BCA","B.Sc. CS","Other"])
        sem = st.selectbox("Semester", [str(i) for i in range(1,7)])
        email = st.text_input("Email *").strip().lower()
        pw = st.text_input("Password *", type="password")
        pw2 = st.text_input("Confirm password *", type="password")
        submitted = st.form_submit_button("Create account", use_container_width=True)
    if submitted:
        if not all([roll,name,email,pw]):
            st.error("Please fill all required fields.")
        elif pw != pw2:
            st.error("Passwords do not match.")
        elif len(pw) < 8:
            st.error("Password must be at least 8 characters.")
        else:
            try:
                run("INSERT INTO users(roll,name,course,semester,email,password,role,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (roll,name,course,sem,email,hash_pw(pw),"student",datetime.now().isoformat(timespec="seconds")))
                st.success("Registration successful. Please login.")
            except sqlite3.IntegrityError:
                st.error("Roll number or email already exists.")

def login_page():
    st.subheader("Login")
    with st.form("login"):
        email = st.text_input("Email").strip().lower()
        pw = st.text_input("Password", type="password")
        go = st.form_submit_button("Login", use_container_width=True)
    if go:
        rows = q("SELECT * FROM users WHERE email=?", (email,))
        if rows and check_pw(pw, rows[0]["password"]):
            st.session_state.user = dict(rows[0])
            st.rerun()
        else:
            st.error("Incorrect email or password.")

if not user:
    a,b = st.tabs(["Login","Register"])
    with a: login_page()
    with b: register_page()
    st.info("First-time demo: use the Teacher or CR credentials shown in the sidebar, or register a student account.")
    st.stop()

if user["role"] == "student":
    st.subheader(f"Welcome, {user['name']}")
    today = date.today().isoformat()
    now = datetime.now()
    c1,c2,c3 = st.columns(3)
    total = q("SELECT COUNT(*) n FROM attendance WHERE roll=?", (user["roll"],))[0]["n"]
    present = q("SELECT COUNT(*) n FROM attendance WHERE roll=? AND status='Present'", (user["roll"],))[0]["n"]
    c1.metric("Attendance entries", total)
    c2.metric("Present", present)
    c3.metric("Attendance %", f"{(present/total*100 if total else 0):.1f}%")
    st.markdown("### Mark today's attendance")
    with st.form("mark"):
        subj = st.selectbox("Subject", get_subjects())
        status = st.radio("Status", ["Present","Absent"], horizontal=True)
        confirm = st.checkbox("I confirm that this attendance information is correct.")
        submit = st.form_submit_button("Mark attendance")
    if submit:
        # Attendance window: 09:00 to 16:15 local system time.
        if not confirm:
            st.error("Please confirm the declaration.")
        elif not (time(9,0) <= now.time() <= time(16,15)):
            st.error("Attendance can only be marked between 9:00 AM and 4:15 PM.")
        else:
            try:
                run("INSERT INTO attendance(roll,subject,day,status,marked_time,verified) VALUES(?,?,?,?,?,0)",
                    (user["roll"],subj,today,status,now.isoformat(timespec="seconds")))
                st.success("Attendance submitted. Waiting for CR verification.")
            except sqlite3.IntegrityError:
                st.warning("You have already submitted attendance for this subject today.")
    st.markdown("### My attendance history")
    rows = q("""SELECT day,subject,status,marked_time,verified,verified_by
                FROM attendance WHERE roll=? ORDER BY day DESC, subject""", (user["roll"],))
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        df["verified"] = df["verified"].map({1:"Yes",0:"Pending"})
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No attendance records yet.")

elif user["role"] == "cr":
    st.subheader("CR verification panel")
    pending = q("""SELECT a.id,a.day,a.subject,a.roll,u.name,a.status,a.marked_time
                    FROM attendance a JOIN users u ON u.roll=a.roll
                    WHERE a.verified=0 ORDER BY a.day DESC,a.marked_time""")
    if not pending:
        st.success("No pending attendance entries.")
    else:
        df = pd.DataFrame([dict(r) for r in pending])
        st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)
        st.markdown("### Verify an entry")
        ids = [r["id"] for r in pending]
        labels = {r["id"]: f"{r['day']} • {r['subject']} • {r['roll']} ({r['name']}) • {r['status']}" for r in pending}
        selected = st.selectbox("Pending entry", ids, format_func=lambda x: labels[x])
        x,y = st.columns(2)
        with x:
            if st.button("Verify", type="primary", use_container_width=True):
                run("UPDATE attendance SET verified=1, verified_by=? WHERE id=?", (user["roll"],selected))
                st.success("Entry verified.")
                st.rerun()
        with y:
            if st.button("Reject / mark absent", use_container_width=True):
                run("UPDATE attendance SET status='Absent',verified=1,verified_by=? WHERE id=?", (user["roll"],selected))
                st.warning("Entry marked Absent and verified.")
                st.rerun()
    st.markdown("### Add subject")
    with st.form("subject"):
        new_subject = st.text_input("Subject name")
        teacher_name = st.text_input("Teacher name", value="Demo Teacher")
        add = st.form_submit_button("Add subject")
    if add:
        if new_subject.strip():
            try:
                run("INSERT INTO subjects(name,teacher) VALUES(?,?)",(new_subject.strip(),teacher_name.strip()))
                st.success("Subject added.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Subject already exists.")

elif user["role"] == "teacher":
    st.subheader("Teacher dashboard")
    students = q("SELECT roll,name,course,semester FROM users WHERE role='student' ORDER BY roll")
    att = q("""SELECT a.*,u.name,u.course,u.semester FROM attendance a
               JOIN users u ON u.roll=a.roll ORDER BY a.day DESC""")
    if not students:
        st.info("No student registrations yet.")
    else:
        start = st.date_input("From date", value=date.today()-timedelta(days=30))
        end = st.date_input("To date", value=date.today())
        subject_options = ["All subjects"] + get_subjects()
        subject = st.selectbox("Subject filter", subject_options)
        data = [dict(r) for r in att if start.isoformat() <= r["day"] <= end.isoformat() and (subject=="All subjects" or r["subject"]==subject)]
        total_students = len(students)
        present_today = sum(1 for r in data if r["day"]==date.today().isoformat() and r["status"]=="Present")
        absent_today = sum(1 for r in data if r["day"]==date.today().isoformat() and r["status"]=="Absent")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total students",total_students)
        m2.metric("Present today",present_today)
        m3.metric("Absent today",absent_today)
        m4.metric("Today's entries",present_today+absent_today)
        st.markdown("### Attendance records")
        if data:
            df = pd.DataFrame(data)
            df["verified"] = df["verified"].map({1:"Yes",0:"Pending"})
            st.dataframe(df[["day","subject","roll","name","status","marked_time","verified"]], use_container_width=True, hide_index=True)
            daily = df.groupby(["day","status"]).size().reset_index(name="count")
            st.plotly_chart(px.line(daily, x="day", y="count", color="status", title="Daily attendance trend"), use_container_width=True)
            sub = df.groupby(["subject","status"]).size().reset_index(name="count")
            st.plotly_chart(px.bar(sub, x="subject", y="count", color="status", barmode="group", title="Subject-wise attendance"), use_container_width=True)
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV report", csv_bytes, "attendance_report.csv", "text/csv")
            st.markdown("### Defaulter list (below 75% in selected records)")
            rollups=[]
            for s in students:
                mine=[r for r in data if r["roll"]==s["roll"]]
                total=len(mine); pres=sum(1 for r in mine if r["status"]=="Present")
                pct=pres/total*100 if total else 0
                if total and pct < 75:
                    rollups.append({"Roll":s["roll"],"Name":s["name"],"Present":pres,"Total":total,"Attendance %":round(pct,1)})
            if rollups:
                st.dataframe(pd.DataFrame(rollups),use_container_width=True,hide_index=True)
            else:
                st.success("No defaulters in the selected records.")
        else:
            st.info("No records match these filters.")
        st.markdown("### Basic attendance insights")
        if data:
            df2=pd.DataFrame(data)
            absences=df2[df2.status=="Absent"].groupby("roll").size().sort_values(ascending=False)
            if len(absences):
                top=absences.index[0]
                nm=next((s["name"] for s in students if s["roll"]==top),top)
                st.write(f"Most absent in this filtered period: **{nm} ({top})**, {int(absences.iloc[0])} absent entries.")
            else:
                st.write("No absences recorded in this filtered period.")
            low_subject=df2.groupby("subject").apply(lambda x: (x.status=="Present").mean()*100, include_groups=False).sort_values()
            if len(low_subject):
                st.write(f"Lowest present rate by subject: **{low_subject.index[0]} ({low_subject.iloc[0]:.1f}%)**.")
    st.caption("This is a classroom project prototype. Teacher dashboard shows submitted records; CR verification status is visible in the table.")

st.markdown("---")
st.caption("Project prototype • SQLite database is stored locally in attendance.db • Use demo credentials only for testing.")
