"""
database/db.py
PostgreSQL (Supabase) persistence layer — drop-in replacement for SQLite version.
All function signatures are identical to the original.

Setup:
  1. pip install psycopg2-binary
  2. Add to .streamlit/secrets.toml:
       [supabase]
       DATABASE_URL = "postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres"
  3. Or set environment variable: DATABASE_URL=...
"""

import os
import psycopg2
import psycopg2.extras
import streamlit as st
from datetime import datetime
import bcrypt

# ── CONNECTION ────────────────────────────────────────────────────────────────

def _get_db_url():
    try:
        return st.secrets["supabase"]["DATABASE_URL"]
    except Exception:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL not found in .streamlit/secrets.toml")
        return url


def get_connection():
    """Open a fresh connection. Uses RealDictCursor so rows behave like dicts."""
    conn = psycopg2.connect(
        _get_db_url(),
        cursor_factory=psycopg2.extras.RealDictCursor,
        sslmode="require",
        connect_timeout=10
    )
    return conn


# ── INIT DB ───────────────────────────────────────────────────────────────────

_DB_INITIALIZED = False

def init_db():
    """Create all tables on first run. Uses module-level flag to run only once."""
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    conn = get_connection()
    conn.autocommit = True   # DDL needs autocommit on transaction pooler
    c = conn.cursor()

    # ── Table 1: learner_profile ──────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS learner_profile (
        uid             SERIAL PRIMARY KEY,
        name            TEXT NOT NULL,
        age             INTEGER,
        education_level TEXT,
        subject_list    TEXT,
        daily_hours     REAL DEFAULT 2.0,
        deadline        TEXT,
        learning_goals  TEXT,
        email           TEXT,
        password_hash   TEXT,
        created_at      TIMESTAMP DEFAULT NOW()
    )""")

    # ── Migrate: add email/password columns if missing ────────────────
    # Check existing columns first to avoid ALTER TABLE on pooler connections
    c.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='learner_profile'
    """)
    existing_cols = {r["column_name"] for r in c.fetchall()}
    if "email" not in existing_cols:
        c.execute("ALTER TABLE learner_profile ADD COLUMN email TEXT")
    if "password_hash" not in existing_cols:
        c.execute("ALTER TABLE learner_profile ADD COLUMN password_hash TEXT")

    # ── Table 2: quiz_attempts ────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        attempt_id          SERIAL PRIMARY KEY,
        uid                 INTEGER,
        subject             TEXT,
        topic               TEXT,
        score               INTEGER,
        total_questions     INTEGER,
        accuracy_pct        REAL,
        response_latency_s  REAL DEFAULT 0.0,
        ael_modality_used   INTEGER DEFAULT 0,
        timestamp           TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )""")

    # ── Table 3: subject_summary ──────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS subject_summary (
        summary_id      SERIAL PRIMARY KEY,
        uid             INTEGER,
        subject         TEXT,
        avg_accuracy    REAL DEFAULT 0.0,
        total_attempts  INTEGER DEFAULT 0,
        strength_label  TEXT DEFAULT 'Weak',
        last_updated    TIMESTAMP DEFAULT NOW(),
        UNIQUE(uid, subject),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )""")

    # ── Table 4: learning_plans ───────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS learning_plans (
        plan_id             SERIAL PRIMARY KEY,
        uid                 INTEGER,
        plan_text           TEXT,
        weak_topics_at_gen  TEXT,
        mastery_snapshot    TEXT,
        deadline            TEXT,
        days_remaining      INTEGER,
        generated_at        TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )""")

    # ── AEL modality index per topic ──────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS ael_state (
        uid         INTEGER,
        subject     TEXT,
        topic       TEXT,
        modality    INTEGER DEFAULT 0,
        PRIMARY KEY (uid, subject, topic),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )""")

    # ── Error topics tracking ─────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS error_topics (
        uid      INTEGER,
        subject  TEXT,
        topic    TEXT,
        count    INTEGER DEFAULT 1,
        PRIMARY KEY (uid, subject, topic),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS subject_topics (
        id        SERIAL PRIMARY KEY,
        subject   TEXT NOT NULL,
        topic     TEXT NOT NULL,
        position  INTEGER DEFAULT 0,
        UNIQUE(subject, topic)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS plan_days (
        id          SERIAL PRIMARY KEY,
        uid         INTEGER,
        plan_id     INTEGER,
        day_number  INTEGER,
        day_label   TEXT,
        content     TEXT,
        status      TEXT DEFAULT 'pending',
        FOREIGN KEY (plan_id) REFERENCES learning_plans(plan_id)
    )""")

    # ── Gamification: XP & Levels ─────────────────────────────────────
    c.execute('''
    CREATE TABLE IF NOT EXISTS learner_xp (
        uid             INTEGER PRIMARY KEY,
        total_xp        INTEGER DEFAULT 0,
        level           INTEGER DEFAULT 1,
        last_updated    TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )''')

    # ── Gamification: Daily Streaks ───────────────────────────────────
    c.execute('''
    CREATE TABLE IF NOT EXISTS learner_streaks (
        uid             INTEGER PRIMARY KEY,
        current_streak  INTEGER DEFAULT 0,
        longest_streak  INTEGER DEFAULT 0,
        last_study_date TEXT,
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )''')

    # ── AI: Hint usage tracking ───────────────────────────────────────
    c.execute('''
    CREATE TABLE IF NOT EXISTS hint_usage (
        id          SERIAL PRIMARY KEY,
        uid         INTEGER,
        subject     TEXT,
        topic       TEXT,
        hint_level  INTEGER,
        timestamp   TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )''')

    # ── AI: Socratic session history ──────────────────────────────────
    c.execute('''
    CREATE TABLE IF NOT EXISTS socratic_sessions (
        id          SERIAL PRIMARY KEY,
        uid         INTEGER,
        subject     TEXT,
        topic       TEXT,
        messages    TEXT,
        timestamp   TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )''')

    conn.commit()
    conn.close()


# ── LEARNER PROFILE ───────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

def create_profile(name, age, education_level, subject_list, daily_hours, deadline, learning_goals,
                   email: str = "", password: str = ""):
    conn = get_connection()
    c = conn.cursor()
    pw_hash = hash_password(password) if password else None
    c.execute("""
        INSERT INTO learner_profile
            (name, age, education_level, subject_list, daily_hours, deadline, learning_goals, email, password_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING uid
    """, (name, age, education_level, ",".join(subject_list), daily_hours, deadline, learning_goals,
          email.lower().strip() if email else None, pw_hash))
    uid = c.fetchone()["uid"]
    conn.commit()
    conn.close()
    return uid

def get_profile_by_email(email: str, password: str):
    """Lookup profile by email and verify password. Returns profile dict or None."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM learner_profile WHERE LOWER(email)=%s", (email.lower().strip(),))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    row = dict(row)
    stored_hash = row.get("password_hash") or ""
    if not stored_hash or not verify_password(password, stored_hash):
        return None
    return row


def get_profile(uid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM learner_profile WHERE uid = %s", (uid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_profiles():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT uid, name, education_level FROM learner_profile ORDER BY uid DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── QUIZ ATTEMPTS ─────────────────────────────────────────────────────────────

def log_quiz_attempt(uid, subject, topic, score, total, latency, ael_modality):
    accuracy = round((score / total) * 100, 2) if total > 0 else 0.0
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO quiz_attempts (uid, subject, topic, score, total_questions, accuracy_pct, response_latency_s, ael_modality_used)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (uid, subject, topic, score, total, accuracy, latency, ael_modality))

    # Update subject_summary
    _update_subject_summary(c, uid, subject)
    conn.commit()
    conn.close()
    return accuracy


def _update_subject_summary(c, uid, subject):
    c.execute("""
        SELECT AVG(accuracy_pct) as avg_acc, COUNT(*) as cnt
        FROM quiz_attempts WHERE uid=%s AND subject=%s
    """, (uid, subject))
    row = c.fetchone()

    avg_acc = round(float(row["avg_acc"] or 0.0), 2)
    cnt = row["cnt"]
    label = classify_strength(avg_acc)

    c.execute("""
        INSERT INTO subject_summary (uid, subject, avg_accuracy, total_attempts, strength_label, last_updated)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (uid, subject) DO UPDATE SET
            avg_accuracy   = EXCLUDED.avg_accuracy,
            total_attempts = EXCLUDED.total_attempts,
            strength_label = EXCLUDED.strength_label,
            last_updated   = EXCLUDED.last_updated
    """, (uid, subject, avg_acc, cnt, label))


def classify_strength(accuracy_pct):
    """Paper thresholds: Strong ≥75%, Moderate 50-74%, Weak <50%"""
    if accuracy_pct >= 75:
        return "Strong"
    elif accuracy_pct >= 50:
        return "Moderate"
    else:
        return "Weak"


def get_subject_summary(uid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM subject_summary WHERE uid=%s ORDER BY subject", (uid,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_accuracy(uid, subject, topic, n=2):
    """Get last n accuracy values for a topic — used by AEL."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT accuracy_pct FROM quiz_attempts
        WHERE uid=%s AND subject=%s AND topic=%s
        ORDER BY timestamp DESC LIMIT %s
    """, (uid, subject, topic, n))
    rows = c.fetchall()
    conn.close()
    return [r["accuracy_pct"] for r in rows]


def get_quiz_history(uid, subject=None):
    conn = get_connection()
    c = conn.cursor()
    if subject:
        c.execute("""
            SELECT * FROM quiz_attempts WHERE uid=%s AND subject=%s
            ORDER BY timestamp DESC
        """, (uid, subject))
    else:
        c.execute("""
            SELECT * FROM quiz_attempts WHERE uid=%s
            ORDER BY timestamp DESC
        """, (uid,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── AEL STATE ─────────────────────────────────────────────────────────────────

def get_ael_modality(uid, subject, topic):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT modality FROM ael_state WHERE uid=%s AND subject=%s AND topic=%s",
        (uid, subject, topic)
    )
    row = c.fetchone()
    conn.close()
    return row["modality"] if row else 0


def set_ael_modality(uid, subject, topic, modality):
    modality = max(0, min(4, modality))
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO ael_state (uid, subject, topic, modality)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (uid, subject, topic) DO UPDATE SET modality = EXCLUDED.modality
    """, (uid, subject, topic, modality))
    conn.commit()
    conn.close()


def update_ael(uid, subject, topic, recent_accuracies):
    """
    AEL update rule from the paper:
    M(t+1) = clip(M(t) + Δ(acc(t)), 0, 4)
    Δ(acc) = +1 if acc < 0.50, -1 if acc > 0.75, 0 otherwise
    Trigger only when 2 consecutive attempts cross the threshold.
    """
    current_m = get_ael_modality(uid, subject, topic)

    if len(recent_accuracies) >= 2:
        both_low  = all(a < 50 for a in recent_accuracies[:2])
        both_high = all(a > 75 for a in recent_accuracies[:2])
        if both_low:
            new_m = min(4, current_m + 1)
        elif both_high:
            new_m = max(0, current_m - 1)
        else:
            new_m = current_m
    else:
        new_m = current_m

    set_ael_modality(uid, subject, topic, new_m)
    return new_m


# ── ERROR TOPICS ──────────────────────────────────────────────────────────────

def log_error_topic(uid, subject, topic):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO error_topics (uid, subject, topic, count) VALUES (%s, %s, %s, 1)
        ON CONFLICT (uid, subject, topic) DO UPDATE SET count = error_topics.count + 1
    """, (uid, subject, topic))
    conn.commit()
    conn.close()


def get_error_topics(uid, subject):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT topic FROM error_topics WHERE uid=%s AND subject=%s
        ORDER BY count DESC LIMIT 5
    """, (uid, subject))
    rows = c.fetchall()
    conn.close()
    return [r["topic"] for r in rows]


# ── LEARNING PLANS ────────────────────────────────────────────────────────────

def save_learning_plan(uid, plan_text, weak_topics, mastery_snapshot, deadline, days_remaining):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO learning_plans (uid, plan_text, weak_topics_at_gen, mastery_snapshot, deadline, days_remaining)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (uid, plan_text, str(weak_topics), str(mastery_snapshot), deadline, days_remaining))
    conn.commit()
    conn.close()


def get_latest_plan(uid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM learning_plans WHERE uid=%s ORDER BY generated_at DESC LIMIT 1
    """, (uid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# ── SUBJECT TOPICS ────────────────────────────────────────────────────────────

def _resolve_subject_name(c, subject):
    """Return the stored subject name that matches case-insensitively, or subject itself if new."""
    c.execute(
        "SELECT subject FROM subject_topics WHERE LOWER(subject)=LOWER(%s) "
        "GROUP BY subject ORDER BY COUNT(*) DESC LIMIT 1",
        (subject.strip(),)
    )
    row = c.fetchone()
    return row["subject"] if row else subject.strip()


def save_topics(subject, topics):
    conn = get_connection()
    c = conn.cursor()
    canonical = _resolve_subject_name(c, subject)
    # Delete only this subject (exact canonical name)
    c.execute("DELETE FROM subject_topics WHERE subject=%s", (canonical,))
    for i, topic in enumerate(topics):
        if topic.strip():
            c.execute("""
                INSERT INTO subject_topics (subject, topic, position)
                VALUES (%s, %s, %s)
                ON CONFLICT (subject, topic) DO NOTHING
            """, (canonical, topic.strip(), i))
    conn.commit()
    conn.close()


def get_topics(subject):
    conn = get_connection()
    c = conn.cursor()
    canonical = _resolve_subject_name(c, subject)
    c.execute(
        "SELECT topic FROM subject_topics WHERE subject=%s ORDER BY position",
        (canonical,)
    )
    rows = c.fetchall()
    conn.close()
    return [r["topic"] for r in rows]


def topics_exist(subject):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) as c FROM subject_topics WHERE LOWER(subject)=LOWER(%s)",
        (subject.strip(),)
    )
    count = c.fetchone()["c"]
    conn.close()
    return count > 0


# ── PLAN DAYS ─────────────────────────────────────────────────────────────────

def save_plan_days(uid, plan_id, days):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM plan_days WHERE uid=%s AND plan_id=%s", (uid, plan_id))
    for d in days:
        c.execute("""
            INSERT INTO plan_days (uid, plan_id, day_number, day_label, content, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """, (uid, plan_id, d["day_number"], d["day_label"], d["content"]))
    conn.commit()
    conn.close()


def get_plan_days(uid, plan_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM plan_days WHERE uid=%s AND plan_id=%s ORDER BY day_number",
        (uid, plan_id)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_day_status(uid, plan_id, day_number, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE plan_days SET status=%s WHERE uid=%s AND plan_id=%s AND day_number=%s
    """, (status, uid, plan_id, day_number))
    conn.commit()
    conn.close()


def update_day_content(uid, plan_id, day_number, new_content):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE plan_days SET content=%s WHERE uid=%s AND plan_id=%s AND day_number=%s
    """, (new_content, uid, plan_id, day_number))
    conn.commit()
    conn.close()


def get_latest_plan_id(uid):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT plan_id FROM learning_plans WHERE uid=%s ORDER BY generated_at DESC LIMIT 1",
        (uid,)
    )
    row = c.fetchone()
    conn.close()
    return row["plan_id"] if row else None


XP_PER_QUIZ     = 10   # base XP per quiz completed
XP_BONUS_STRONG = 15   # bonus if accuracy >= 75%
XP_PER_LEVEL    = 100  # XP needed to level up

LEVEL_TITLES = {
    1: "🌱 Seedling",
    2: "📖 Learner",
    3: "🔥 Scholar",
    4: "⚡ Expert",
    5: "🏆 Master",
}


def get_xp(uid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM learner_xp WHERE uid=%s", (uid,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"uid": uid, "total_xp": 0, "level": 1}


def add_xp(uid, accuracy_pct):
    """Award XP after a quiz. Returns (xp_gained, new_total, new_level, leveled_up)."""
    xp_gained = XP_PER_QUIZ
    if accuracy_pct >= 75:
        xp_gained += XP_BONUS_STRONG

    conn = get_connection()
    c = conn.cursor()

    # Upsert XP row
    c.execute("""
        INSERT INTO learner_xp (uid, total_xp, level)
        VALUES (%s, %s, 1)
        ON CONFLICT (uid) DO UPDATE SET
            total_xp = learner_xp.total_xp + %s,
            last_updated = NOW()
        RETURNING total_xp, level
    """, (uid, xp_gained, xp_gained))
    row = c.fetchone()
    new_total = row["total_xp"]
    old_level = row["level"]

    # Calculate new level
    new_level = max(1, min(5, new_total // XP_PER_LEVEL + 1))
    leveled_up = new_level > old_level

    if leveled_up:
        c.execute("UPDATE learner_xp SET level=%s WHERE uid=%s", (new_level, uid))

    conn.commit()
    conn.close()
    return xp_gained, new_total, new_level, leveled_up


def get_level_title(level):
    return LEVEL_TITLES.get(level, "🏆 Master")


def get_xp_progress(total_xp, level):
    """Returns (xp_in_current_level, xp_needed_for_next) for progress bar."""
    xp_in_level = total_xp % XP_PER_LEVEL
    return xp_in_level, XP_PER_LEVEL


# ── STREAKS ───────────────────────────────────────────────────────────────────

def update_streak(uid):
    """
    Call once per day when student studies.
    Returns (current_streak, longest_streak, is_new_day).
    """
    from datetime import date
    today = str(date.today())

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM learner_streaks WHERE uid=%s", (uid,))
    row = c.fetchone()

    if not row:
        # First time
        c.execute("""
            INSERT INTO learner_streaks (uid, current_streak, longest_streak, last_study_date)
            VALUES (%s, 1, 1, %s)
        """, (uid, today))
        conn.commit()
        conn.close()
        return 1, 1, True

    row = dict(row)
    last_date = row["last_study_date"]
    current   = row["current_streak"]
    longest   = row["longest_streak"]

    if last_date == today:
        # Already studied today
        conn.close()
        return current, longest, False

    from datetime import date, timedelta
    yesterday = str(date.today() - timedelta(days=1))

    if last_date == yesterday:
        current += 1  # continued streak
    else:
        current = 1   # streak broken, reset

    longest = max(longest, current)

    c.execute("""
        UPDATE learner_streaks
        SET current_streak=%s, longest_streak=%s, last_study_date=%s
        WHERE uid=%s
    """, (current, longest, today, uid))
    conn.commit()
    conn.close()
    return current, longest, True


def get_streak(uid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM learner_streaks WHERE uid=%s", (uid,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"current_streak": 0, "longest_streak": 0, "last_study_date": None}


# ── HINT USAGE ────────────────────────────────────────────────────────────────

def log_hint_usage(uid, subject, topic, hint_level):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO hint_usage (uid, subject, topic, hint_level)
        VALUES (%s, %s, %s, %s)
    """, (uid, subject, topic, hint_level))
    conn.commit()
    conn.close()


# ── SOCRATIC SESSIONS ─────────────────────────────────────────────────────────

def save_socratic_session(uid, subject, topic, messages):
    import json
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO socratic_sessions (uid, subject, topic, messages)
        VALUES (%s, %s, %s, %s)
    """, (uid, subject, topic, json.dumps(messages)))
    conn.commit()
    conn.close()


def get_socratic_sessions(uid, subject=None, topic=None):
    conn = get_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM socratic_sessions WHERE uid=%s"
    params = [uid]
    
    if subject:
        query += " AND subject=%s"
        params.append(subject)
        
    if topic:
        query += " AND topic=%s"
        params.append(topic)
        
    query += " ORDER BY timestamp DESC"
    
    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return []
        
    # We want to return the messages from the most recent session for that topic
    # If no topic specified, we just return the full rows
    if topic and rows:
        import json
        try:
            return json.loads(rows[0]["messages"])
        except:
            return []
            
    return [dict(r) for r in rows]

def log_study_interaction(uid, subject, topic, question, answer, modality, latency, chunks):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO study_logs
        (user_id, subject, topic, question, answer, modality, latency, chunks_used)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (uid, subject, topic, question, answer, modality, latency, chunks)
    )

    conn.commit()
    cur.close()
    conn.close()

def update_subject_list(uid, subjects):
    """Update the learner's subject list."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE learner_profile SET subject_list = %s WHERE uid = %s",
        (", ".join(subjects), uid)
    )
    conn.commit()
    conn.close()