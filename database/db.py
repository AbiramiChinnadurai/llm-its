"""
database/db.py
SQLite persistence layer — creates and manages all 4 tables from the paper:
  1. learner_profile
  2. quiz_attempts
  3. subject_summary
  4. learning_plans
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "llm_its.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables and triggers on first run."""
    conn = get_connection()
    c = conn.cursor()

    # ── Table 1: learner_profile ──────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS learner_profile (
        uid             INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        age             INTEGER,
        education_level TEXT,
        subject_list    TEXT,
        daily_hours     REAL DEFAULT 2.0,
        deadline        TEXT,
        learning_goals  TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    # ── Table 2: quiz_attempts ────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        attempt_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        uid                 INTEGER,
        subject             TEXT,
        topic               TEXT,
        score               INTEGER,
        total_questions     INTEGER,
        accuracy_pct        REAL,
        response_latency_s  REAL DEFAULT 0.0,
        ael_modality_used   INTEGER DEFAULT 0,
        timestamp           TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )""")

    # ── Table 3: subject_summary ──────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS subject_summary (
        summary_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        uid             INTEGER,
        subject         TEXT,
        avg_accuracy    REAL DEFAULT 0.0,
        total_attempts  INTEGER DEFAULT 0,
        strength_label  TEXT DEFAULT 'Weak',
        last_updated    TEXT DEFAULT (datetime('now')),
        UNIQUE(uid, subject),
        FOREIGN KEY (uid) REFERENCES learner_profile(uid)
    )""")

    # ── Table 4: learning_plans ───────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS learning_plans (
        plan_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        uid                 INTEGER,
        plan_text           TEXT,
        weak_topics_at_gen  TEXT,
        mastery_snapshot    TEXT,
        deadline            TEXT,
        days_remaining      INTEGER,
        generated_at        TEXT DEFAULT (datetime('now')),
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
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        subject   TEXT NOT NULL,
        topic     TEXT NOT NULL,
        position  INTEGER DEFAULT 0,
        UNIQUE(subject, topic)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS plan_days (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        uid         INTEGER,
        plan_id     INTEGER,
        day_number  INTEGER,
        day_label   TEXT,
        content     TEXT,
        status      TEXT DEFAULT 'pending',
        FOREIGN KEY (plan_id) REFERENCES learning_plans(plan_id)
    )""")
    conn.commit()
    conn.close()
    print("[DB] Initialized successfully.")


# ── LEARNER PROFILE ───────────────────────────────────────────────────────────

def create_profile(name, age, education_level, subject_list, daily_hours, deadline, learning_goals):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO learner_profile (name, age, education_level, subject_list, daily_hours, deadline, learning_goals)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, age, education_level, ",".join(subject_list), daily_hours, deadline, learning_goals))
    uid = c.lastrowid
    conn.commit()
    conn.close()
    return uid


def get_profile(uid):
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("SELECT * FROM learner_profile WHERE uid = ?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_profiles():
    conn = get_connection()
    rows = conn.execute("SELECT uid, name, education_level FROM learner_profile ORDER BY uid DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── QUIZ ATTEMPTS ─────────────────────────────────────────────────────────────

def log_quiz_attempt(uid, subject, topic, score, total, latency, ael_modality):
    accuracy = round((score / total) * 100, 2) if total > 0 else 0.0
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO quiz_attempts (uid, subject, topic, score, total_questions, accuracy_pct, response_latency_s, ael_modality_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (uid, subject, topic, score, total, accuracy, latency, ael_modality))
    conn.commit()

    # Update subject_summary
    _update_subject_summary(c, uid, subject)
    conn.commit()
    conn.close()
    return accuracy


def _update_subject_summary(c, uid, subject):
    row = c.execute("""
        SELECT AVG(accuracy_pct) as avg_acc, COUNT(*) as cnt
        FROM quiz_attempts WHERE uid=? AND subject=?
    """, (uid, subject)).fetchone()

    avg_acc = round(row["avg_acc"] or 0.0, 2)
    cnt = row["cnt"]
    label = classify_strength(avg_acc)

    c.execute("""
        INSERT INTO subject_summary (uid, subject, avg_accuracy, total_attempts, strength_label, last_updated)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(uid, subject) DO UPDATE SET
            avg_accuracy   = excluded.avg_accuracy,
            total_attempts = excluded.total_attempts,
            strength_label = excluded.strength_label,
            last_updated   = excluded.last_updated
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
    rows = conn.execute(
        "SELECT * FROM subject_summary WHERE uid=? ORDER BY subject", (uid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_accuracy(uid, subject, topic, n=2):
    """Get last n accuracy values for a topic — used by AEL."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT accuracy_pct FROM quiz_attempts
        WHERE uid=? AND subject=? AND topic=?
        ORDER BY timestamp DESC LIMIT ?
    """, (uid, subject, topic, n)).fetchall()
    conn.close()
    return [r["accuracy_pct"] for r in rows]


def get_quiz_history(uid, subject=None):
    conn = get_connection()
    if subject:
        rows = conn.execute("""
            SELECT * FROM quiz_attempts WHERE uid=? AND subject=?
            ORDER BY timestamp DESC
        """, (uid, subject)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM quiz_attempts WHERE uid=?
            ORDER BY timestamp DESC
        """, (uid,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── AEL STATE ─────────────────────────────────────────────────────────────────

def get_ael_modality(uid, subject, topic):
    conn = get_connection()
    row = conn.execute(
        "SELECT modality FROM ael_state WHERE uid=? AND subject=? AND topic=?",
        (uid, subject, topic)
    ).fetchone()
    conn.close()
    return row["modality"] if row else 0


def set_ael_modality(uid, subject, topic, modality):
    modality = max(0, min(4, modality))
    conn = get_connection()
    conn.execute("""
        INSERT INTO ael_state (uid, subject, topic, modality)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(uid, subject, topic) DO UPDATE SET modality = excluded.modality
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
        both_low    = all(a < 50 for a in recent_accuracies[:2])
        both_high   = all(a > 75 for a in recent_accuracies[:2])
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
    conn.execute("""
        INSERT INTO error_topics (uid, subject, topic, count) VALUES (?, ?, ?, 1)
        ON CONFLICT(uid, subject, topic) DO UPDATE SET count = count + 1
    """, (uid, subject, topic))
    conn.commit()
    conn.close()


def get_error_topics(uid, subject):
    conn = get_connection()
    rows = conn.execute("""
        SELECT topic FROM error_topics WHERE uid=? AND subject=?
        ORDER BY count DESC LIMIT 5
    """, (uid, subject)).fetchall()
    conn.close()
    return [r["topic"] for r in rows]


# ── LEARNING PLANS ────────────────────────────────────────────────────────────

def save_learning_plan(uid, plan_text, weak_topics, mastery_snapshot, deadline, days_remaining):
    conn = get_connection()
    conn.execute("""
        INSERT INTO learning_plans (uid, plan_text, weak_topics_at_gen, mastery_snapshot, deadline, days_remaining)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (uid, plan_text, str(weak_topics), str(mastery_snapshot), deadline, days_remaining))
    conn.commit()
    conn.close()


def get_latest_plan(uid):
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM learning_plans WHERE uid=? ORDER BY generated_at DESC LIMIT 1
    """, (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ── SUBJECT TOPICS ────────────────────────────────────────────────────────────

def save_topics(subject, topics):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM subject_topics WHERE subject=?", (subject,))
    for i, topic in enumerate(topics):
        if topic.strip():
            c.execute("""
                INSERT OR IGNORE INTO subject_topics (subject, topic, position)
                VALUES (?, ?, ?)
            """, (subject, topic.strip(), i))
    conn.commit()
    conn.close()


def get_topics(subject):
    conn = get_connection()
    rows = conn.execute(
        "SELECT topic FROM subject_topics WHERE subject=? ORDER BY position",
        (subject,)
    ).fetchall()
    conn.close()
    return [r["topic"] for r in rows]


def topics_exist(subject):
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) as c FROM subject_topics WHERE subject=?", (subject,)
    ).fetchone()["c"]
    conn.close()
    return count > 0


# ── PLAN DAYS ─────────────────────────────────────────────────────────────────

def save_plan_days(uid, plan_id, days):
    conn = get_connection()
    conn.execute("DELETE FROM plan_days WHERE uid=? AND plan_id=?", (uid, plan_id))
    for d in days:
        conn.execute("""
            INSERT INTO plan_days (uid, plan_id, day_number, day_label, content, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (uid, plan_id, d["day_number"], d["day_label"], d["content"]))
    conn.commit()
    conn.close()


def get_plan_days(uid, plan_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM plan_days WHERE uid=? AND plan_id=? ORDER BY day_number",
        (uid, plan_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_day_status(uid, plan_id, day_number, status):
    conn = get_connection()
    conn.execute("""
        UPDATE plan_days SET status=? WHERE uid=? AND plan_id=? AND day_number=?
    """, (status, uid, plan_id, day_number))
    conn.commit()
    conn.close()


def update_day_content(uid, plan_id, day_number, new_content):
    conn = get_connection()
    conn.execute("""
        UPDATE plan_days SET content=? WHERE uid=? AND plan_id=? AND day_number=?
    """, (new_content, uid, plan_id, day_number))
    conn.commit()
    conn.close()


def get_latest_plan_id(uid):
    conn = get_connection()
    row = conn.execute(
        "SELECT plan_id FROM learning_plans WHERE uid=? ORDER BY generated_at DESC LIMIT 1",
        (uid,)
    ).fetchone()
    conn.close()
    return row["plan_id"] if row else None