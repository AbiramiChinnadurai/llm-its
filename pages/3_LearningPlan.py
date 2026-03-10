"""
pages/3_LearningPlan.py
Learning Plan — Visual Timeline Roadmap.
Mark days complete/skip, auto-reschedule pending days.
"""

import streamlit as st
import re
from datetime import datetime, date, timedelta
from database.db import (get_subject_summary, get_error_topics,
                          save_learning_plan, get_latest_plan, get_latest_plan_id,
                          save_plan_days, get_plan_days,
                          update_day_status, get_profile)
from llm.llm_engine import generate_learning_plan

st.set_page_config(page_title="Roadmap | LLM-ITS", page_icon="🗺️", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=Instrument+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'Instrument Sans', sans-serif; }

.stApp {
    background: #080c14;
    color: #d4dbe8;
}

/* ══ HUD HEADER ══════════════════════════════════════════════════════════ */
.hud-header {
    background: linear-gradient(160deg, #0d1524 0%, #080c14 60%);
    border: 1px solid #1a2540;
    border-radius: 20px;
    padding: 32px 40px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.hud-header::after {
    content: 'ROADMAP';
    position: absolute;
    right: 32px; top: 50%;
    transform: translateY(-50%);
    font-family: 'Syne', sans-serif;
    font-size: 5rem;
    font-weight: 800;
    color: rgba(255,255,255,0.025);
    letter-spacing: 0.15em;
    pointer-events: none;
    user-select: none;
}
.hud-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    color: #f0f6ff;
    margin: 0 0 4px 0;
    letter-spacing: -0.5px;
}
.hud-sub { color: #4a6080; font-size: 0.88rem; margin: 0; font-weight: 300; }

/* ══ PROGRESS HUD ════════════════════════════════════════════════════════ */
.progress-hud {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 28px;
}
.hud-cell {
    background: #0d1524;
    border: 1px solid #1a2540;
    border-radius: 14px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.hud-cell:hover { border-color: #2a4060; }
.hud-cell::before {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
}
.hud-cell.completed::before { background: linear-gradient(90deg, #10b981, #059669); }
.hud-cell.skipped::before   { background: linear-gradient(90deg, #f59e0b, #d97706); }
.hud-cell.pending::before   { background: linear-gradient(90deg, #3b82f6, #1d4ed8); }
.hud-cell.total::before     { background: linear-gradient(90deg, #8b5cf6, #6d28d9); }

.hud-num {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 4px;
}
.hud-cell.completed .hud-num { color: #10b981; }
.hud-cell.skipped   .hud-num { color: #f59e0b; }
.hud-cell.pending   .hud-num { color: #3b82f6; }
.hud-cell.total     .hud-num { color: #8b5cf6; }

.hud-label { font-size: 0.7rem; color: #3a5070; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 500; }

/* ══ PROGRESS TRACK ══════════════════════════════════════════════════════ */
.progress-track-wrap { margin: 0 0 32px 0; }
.progress-track-bar {
    height: 6px;
    background: #0d1524;
    border-radius: 10px;
    overflow: hidden;
    margin: 8px 0 6px 0;
    border: 1px solid #1a2540;
}
.progress-track-fill {
    height: 100%;
    border-radius: 10px;
    background: linear-gradient(90deg, #10b981, #3b82f6, #8b5cf6);
    transition: width 0.6s ease;
    position: relative;
}
.progress-track-fill::after {
    content: '';
    position: absolute;
    right: 0; top: 50%;
    transform: translateY(-50%);
    width: 10px; height: 10px;
    background: #fff;
    border-radius: 50%;
    box-shadow: 0 0 8px rgba(255,255,255,0.6);
}
.progress-caption {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: #3a5070;
}

/* ══ TRACK STATUS ════════════════════════════════════════════════════════ */
.track-status {
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 0.82rem;
    font-weight: 500;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.on-track  { background: #0a1f14; border: 1px solid #065f35; color: #34d399; }
.off-track { background: #1c1005; border: 1px solid #78350f; color: #fbbf24; }

/* ══ TIMELINE ════════════════════════════════════════════════════════════ */
.timeline-wrap { position: relative; padding-left: 52px; }

/* Vertical spine */
.timeline-wrap::before {
    content: '';
    position: absolute;
    left: 19px; top: 24px; bottom: 24px;
    width: 2px;
    background: linear-gradient(180deg,
        #10b981 0%,
        #3b82f6 40%,
        #1a2540 70%,
        #1a2540 100%
    );
    border-radius: 2px;
}

/* ══ DAY NODE ════════════════════════════════════════════════════════════ */
.day-node {
    position: relative;
    margin-bottom: 16px;
    animation: fadeSlideIn 0.4s ease both;
}
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateX(-12px); }
    to   { opacity: 1; transform: translateX(0); }
}

/* Node dot on spine */
.day-node::before {
    content: attr(data-icon);
    position: absolute;
    left: -42px;
    top: 18px;
    width: 24px; height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    z-index: 2;
    border: 2px solid;
}
.day-node.status-completed::before {
    background: #064e2e;
    border-color: #10b981;
    box-shadow: 0 0 10px rgba(16,185,129,0.4);
    content: '✓';
    color: #10b981;
    font-size: 0.75rem;
    font-weight: 700;
}
.day-node.status-pending::before {
    background: #0d1a2e;
    border-color: #3b82f6;
    box-shadow: 0 0 8px rgba(59,130,246,0.25);
    content: attr(data-num);
    color: #3b82f6;
    font-family: 'Syne', sans-serif;
    font-size: 0.65rem;
    font-weight: 700;
    text-align: center;
    line-height: 20px;
}
.day-node.status-skipped::before {
    background: #1c1005;
    border-color: #f59e0b;
    border-style: dashed;
    content: '↷';
    color: #f59e0b;
    font-size: 0.9rem;
}
.day-node.status-today::before {
    background: #1d4ed8;
    border-color: #60a5fa;
    box-shadow: 0 0 14px rgba(96,165,250,0.5), 0 0 28px rgba(96,165,250,0.2);
    content: '▶';
    color: #fff;
    font-size: 0.55rem;
    animation: todayPulse 2s infinite;
}
@keyframes todayPulse {
    0%, 100% { box-shadow: 0 0 14px rgba(96,165,250,0.5), 0 0 28px rgba(96,165,250,0.2); }
    50%       { box-shadow: 0 0 20px rgba(96,165,250,0.8), 0 0 40px rgba(96,165,250,0.4); }
}

/* Card */
.day-card {
    background: #0d1524;
    border: 1px solid #1a2540;
    border-radius: 14px;
    padding: 16px 20px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}
.day-card:hover {
    border-color: #2a4060;
    background: #101b2e;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
.day-card.completed {
    background: #081810;
    border-color: #064e2e;
}
.day-card.skipped {
    background: #120d05;
    border-color: #78350f;
    opacity: 0.75;
}
.day-card.today {
    background: #0d1a2e;
    border-color: #2563eb;
    box-shadow: 0 0 0 1px rgba(59,130,246,0.2), 0 4px 24px rgba(59,130,246,0.1);
}

/* Card header */
.card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 0;
}
.card-day-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.status-completed .card-day-label { color: #10b981; }
.status-pending   .card-day-label { color: #3b82f6; }
.status-skipped   .card-day-label { color: #f59e0b; }
.status-today     .card-day-label { color: #60a5fa; }

.card-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.92rem;
    font-weight: 600;
    color: #d4dbe8;
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.day-card.completed .card-title { color: #6b7a80; text-decoration: line-through; }
.day-card.skipped   .card-title { color: #5a4a30; }
.day-card.today     .card-title { color: #f0f6ff; }

.status-badge {
    font-size: 0.68rem;
    border-radius: 20px;
    padding: 3px 10px;
    white-space: nowrap;
    font-weight: 500;
}
.badge-completed { background: #064e2e; color: #34d399; border: 1px solid #059669; }
.badge-pending   { background: #0d1a2e; color: #60a5fa; border: 1px solid #1d4ed8; }
.badge-skipped   { background: #1c1005; color: #fbbf24; border: 1px solid #92400e; }
.badge-today     { background: #1d4ed8; color: #fff; border: 1px solid #3b82f6;
                   box-shadow: 0 0 8px rgba(59,130,246,0.3); }

/* Expanded content */
.day-content-wrap {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid #1a2540;
    font-size: 0.84rem;
    color: #8090a8;
    line-height: 1.7;
}

/* ══ GENERATE BUTTON ═════════════════════════════════════════════════════ */
.stButton > button {
    border-radius: 12px !important;
    font-family: 'Instrument Sans', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    border: 1px solid #1a2540 !important;
    background: #0d1524 !important;
    color: #8090a8 !important;
}
.stButton > button:hover {
    background: #101b2e !important;
    border-color: #2a4060 !important;
    color: #d4dbe8 !important;
}
button[kind="primary"] {
    background: linear-gradient(135deg, #1d4ed8, #1e3a8a) !important;
    border-color: #2563eb !important;
    color: #fff !important;
    font-weight: 600 !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    box-shadow: 0 4px 20px rgba(37,99,235,0.35) !important;
    transform: translateY(-1px) !important;
}

/* ══ MASTERY CHIPS ═══════════════════════════════════════════════════════ */
.mastery-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 24px; }
.mastery-chip {
    border-radius: 12px;
    padding: 12px 18px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-width: 120px;
    border: 1px solid;
}
.mastery-chip.strong { background: #081810; border-color: #064e2e; }
.mastery-chip.moderate{ background: #141005; border-color: #78350f; }
.mastery-chip.weak   { background: #180808; border-color: #7f1d1d; }
.mastery-chip .subj  { font-family:'Syne',sans-serif; font-size:0.8rem; font-weight:600; }
.mastery-chip.strong .subj  { color: #34d399; }
.mastery-chip.moderate .subj{ color: #fbbf24; }
.mastery-chip.weak .subj    { color: #f87171; }
.mastery-chip .pct   { font-family:'Syne',sans-serif; font-size:1.3rem; font-weight:800; color:#d4dbe8; }
.mastery-chip .wk    { font-size:0.68rem; color:#4a6080; }

/* ══ META ════════════════════════════════════════════════════════════════ */
.meta-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 20px;
}
.meta-cell {
    background: #0d1524;
    border: 1px solid #1a2540;
    border-radius: 12px;
    padding: 14px 16px;
}
.meta-cell .val {
    font-family: 'Syne', sans-serif;
    font-size: 1.5rem;
    font-weight: 800;
    color: #f0f6ff;
}
.meta-cell .lbl { font-size: 0.68rem; color: #3a5070; text-transform: uppercase; letter-spacing: 0.1em; }

hr { border-color: #1a2540 !important; }

[data-baseweb="select"] {
    background: #0d1524 !important;
    border-color: #1a2540 !important;
    border-radius: 10px !important;
}

.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #2a4060;
    margin: 20px 0 10px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────
if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid      = st.session_state.uid
profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_plan_into_days(plan_text):
    days = []
    matches = re.findall(
        r'(?:^|\n)\s*\*{0,2}(Day\s+\d+)\*{0,2}[:\-–]?\s*(.*?)(?=\n\s*\*{0,2}Day\s+\d+|\Z)',
        plan_text, re.IGNORECASE | re.DOTALL
    )
    if matches:
        for i, (label, content) in enumerate(matches, 1):
            days.append({"day_number": i, "day_label": label.strip(), "content": content.strip()})
    else:
        lines = [l.strip() for l in plan_text.split("\n") if l.strip()]
        size  = max(3, len(lines) // 7)
        for i, start in enumerate(range(0, len(lines), size), 1):
            chunk = "\n".join(lines[start:start + size])
            if chunk:
                days.append({"day_number": i, "day_label": f"Day {i}", "content": chunk})
    return days

def reschedule(days):
    completed  = [d for d in days if d["status"] == "completed"]
    pending    = [d for d in days if d["status"] == "pending"]
    skipped    = [d for d in days if d["status"] == "skipped"]
    rescheduled = []
    for d in skipped:
        new_d = dict(d)
        new_d["content"] = f"[Rescheduled] {d['content']}"
        new_d["status"]  = "pending"
        rescheduled.append(new_d)
    ordered = completed + pending + rescheduled
    for i, d in enumerate(ordered, 1):
        d["day_number"] = i
        d["day_label"]  = f"Day {i}"
    return ordered

def first_line(text):
    """Extract first meaningful line as a short title."""
    for line in text.split("\n"):
        line = line.strip().lstrip("*•-#").strip()
        if len(line) > 6:
            return line[:60] + ("…" if len(line) > 60 else "")
    return "Study Session"

# ── Load data ─────────────────────────────────────────────────────────────────
summaries              = get_subject_summary(uid)
weak_topics_by_subject = {s: get_error_topics(uid, s) for s in subjects}

deadline_str = profile.get("deadline", str(date.today()))
try:
    deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
except:
    deadline_date = date.today()
days_left = max(1, (deadline_date - date.today()).days)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hud-header">
    <div class="hud-title">🗺️ Learning Roadmap</div>
    <div class="hud-sub">Your personalized journey to exam day — track every step of the path.</div>
</div>
""", unsafe_allow_html=True)

# ── Layout ────────────────────────────────────────────────────────────────────
col_main, col_side = st.columns([3, 1])

# ══ SIDEBAR ═══════════════════════════════════════════════════════════════════
with col_side:
    st.markdown('<div class="section-label">Mission Stats</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="meta-grid">
        <div class="meta-cell">
            <div class="val">{days_left}</div>
            <div class="lbl">Days Left</div>
        </div>
        <div class="meta-cell">
            <div class="val">{profile.get('daily_hours', 2)}h</div>
            <div class="lbl">Daily</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">Mastery Status</div>', unsafe_allow_html=True)
    cm = {"Strong": "strong", "Moderate": "moderate", "Weak": "weak"}
    ei = {"Strong": "🟢", "Moderate": "🟡", "Weak": "🔴"}
    if summaries:
        chips_html = '<div class="mastery-row">'
        for s in summaries:
            wt  = weak_topics_by_subject.get(s["subject"], [])
            cls = cm.get(s["strength_label"], "weak")
            wk_html = f'<div class="wk">⚠ {", ".join(wt[:2])}</div>' if wt else '<div class="wk">✓ No weak topics</div>'
            chips_html += f"""
            <div class="mastery-chip {cls}">
                <div class="subj">{ei.get(s['strength_label'],'')} {s['subject']}</div>
                <div class="pct">{s['avg_accuracy']:.0f}%</div>
                {wk_html}
            </div>"""
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)
    else:
        st.caption("Complete quizzes for mastery data.")

    st.divider()

    if st.button("🤖 Generate New Roadmap", type="primary", use_container_width=True):
        with st.spinner("Plotting your personalized roadmap..."):
            llm_profile = {
                "name":           profile.get("name", "Student"),
                "deadline":       deadline_str,
                "daily_hours":    profile.get("daily_hours", 2),
                "learning_goals": profile.get("learning_goals", "Master all subjects")
            }
            disp_sum  = summaries or [
                {"subject": s, "strength_label": "Weak", "avg_accuracy": 0.0}
                for s in subjects
            ]
            plan_text = generate_learning_plan(llm_profile, disp_sum, weak_topics_by_subject)
            snap      = {s["subject"]: s["strength_label"] for s in disp_sum}
            save_learning_plan(uid, plan_text, weak_topics_by_subject, snap, deadline_str, days_left)
            plan_id = get_latest_plan_id(uid)
            parsed  = parse_plan_into_days(plan_text)
            if parsed:
                save_plan_days(uid, plan_id, parsed)
            st.session_state["plan_text"] = plan_text
            st.session_state["plan_id"]   = plan_id
            st.success("✅ Roadmap generated!")
            st.rerun()

# ══ MAIN ══════════════════════════════════════════════════════════════════════
with col_main:

    # Load plan
    plan_text = st.session_state.get("plan_text")
    plan_id   = st.session_state.get("plan_id")

    if not plan_text:
        saved = get_latest_plan(uid)
        if saved:
            plan_text = saved["plan_text"]
            plan_id   = saved["plan_id"]
            st.session_state["plan_text"] = plan_text
            st.session_state["plan_id"]   = plan_id

    if not plan_text:
        st.markdown("""
        <div style="text-align:center; padding:80px 20px; color:#2a4060;">
            <div style="font-size:3.5rem; margin-bottom:20px;">🗺️</div>
            <div style="font-family:'Syne',sans-serif; font-size:1.6rem;
                        color:#3a5070; margin-bottom:10px; font-weight:700;">
                No roadmap yet
            </div>
            <div style="font-size:0.85rem; color:#2a4060;">
                Click <strong style="color:#3b82f6;">Generate New Roadmap</strong> in the panel to plot your learning path.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # Load / parse days
    days = get_plan_days(uid, plan_id) if plan_id else []
    if not days:
        days = parse_plan_into_days(plan_text)
        if days and plan_id:
            save_plan_days(uid, plan_id, days)
            days = get_plan_days(uid, plan_id)

    if not days:
        st.warning("Could not parse plan. Showing raw text.")
        st.markdown(plan_text)
        st.stop()

    # Auto-reschedule skipped
    skipped_count = sum(1 for d in days if d["status"] == "skipped")
    if skipped_count:
        reordered = reschedule(days)
        save_plan_days(uid, plan_id, [
            {"day_number": d["day_number"], "day_label": d["day_label"], "content": d["content"]}
            for d in reordered
        ])
        for orig, new in zip(days, reordered):
            if orig["status"] != "pending":
                update_day_status(uid, plan_id, new["day_number"], orig["status"])
        days = get_plan_days(uid, plan_id)

    # ── Stats ──────────────────────────────────────────────────────────
    total     = len(days)
    completed = sum(1 for d in days if d["status"] == "completed")
    skipped   = sum(1 for d in days if d["status"] == "skipped")
    pending   = total - completed - skipped
    pct       = completed / total if total > 0 else 0

    st.markdown(f"""
    <div class="progress-hud">
        <div class="hud-cell total">
            <div class="hud-num">{total}</div>
            <div class="hud-label">Total Days</div>
        </div>
        <div class="hud-cell completed">
            <div class="hud-num">{completed}</div>
            <div class="hud-label">Completed</div>
        </div>
        <div class="hud-cell skipped">
            <div class="hud-num">{skipped}</div>
            <div class="hud-label">Rescheduled</div>
        </div>
        <div class="hud-cell pending">
            <div class="hud-num">{pending}</div>
            <div class="hud-label">Remaining</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Progress bar
    fill_pct = round(pct * 100)
    st.markdown(f"""
    <div class="progress-track-wrap">
        <div class="progress-track-bar">
            <div class="progress-track-fill" style="width:{fill_pct}%"></div>
        </div>
        <div class="progress-caption">
            <span>{completed} of {total} days completed — {fill_pct}%</span>
            <span>Deadline: {deadline_date}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Track status
    if pending > 0:
        est_done = date.today() + timedelta(days=pending)
        on_track = est_done <= deadline_date
        if on_track:
            st.markdown(f'<div class="track-status on-track">✅ On track — estimated completion <strong>{est_done}</strong></div>', unsafe_allow_html=True)
        else:
            overdue = (est_done - deadline_date).days
            st.markdown(f'<div class="track-status off-track">⚠️ At current pace, you finish <strong>{overdue} days after</strong> your deadline. Reduce skips to catch up.</div>', unsafe_allow_html=True)

    # ── Timeline ───────────────────────────────────────────────────────
    today_day = completed + 1

    # Expand state
    if "expanded_days" not in st.session_state:
        st.session_state.expanded_days = set()
        st.session_state.expanded_days.add(today_day)

    st.markdown('<div class="timeline-wrap">', unsafe_allow_html=True)

    for day in days:
        dn      = day["day_number"]
        status  = day.get("status", "pending")
        content = day.get("content", "")
        is_today = (status == "pending" and dn == today_day)
        node_status = "today" if is_today else status

        title_text = first_line(content)

        if status == "completed":
            badge_html = '<span class="status-badge badge-completed">✓ Done</span>'
        elif is_today:
            badge_html = '<span class="status-badge badge-today">▶ Today</span>'
        elif status == "skipped":
            badge_html = '<span class="status-badge badge-skipped">↷ Rescheduled</span>'
        else:
            badge_html = '<span class="status-badge badge-pending">○ Pending</span>'

        expanded = dn in st.session_state.expanded_days

        # Render card header via HTML
        st.markdown(f"""
        <div class="day-node status-{node_status}" data-num="{dn}" data-icon="">
            <div class="day-card {status} {'today' if is_today else ''}">
                <div class="card-head">
                    <span class="card-day-label">Day {dn}</span>
                    <span class="card-title">{title_text}</span>
                    {badge_html}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Expand toggle + actions via Streamlit (inside each node)
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1.2, 1, 1, 1.8])

        with btn_col1:
            toggle_label = "▲ Collapse" if expanded else "▼ View Details"
            if st.button(toggle_label, key=f"tog_{dn}", use_container_width=True):
                if expanded:
                    st.session_state.expanded_days.discard(dn)
                else:
                    st.session_state.expanded_days.add(dn)
                st.rerun()

        with btn_col2:
            if status != "completed":
                if st.button("✅ Complete", key=f"done_{dn}", type="primary", use_container_width=True):
                    update_day_status(uid, plan_id, dn, "completed")
                    st.session_state.expanded_days.discard(dn)
                    st.rerun()
            else:
                if st.button("↩ Undo", key=f"undo_{dn}", use_container_width=True):
                    update_day_status(uid, plan_id, dn, "pending")
                    st.rerun()

        with btn_col3:
            if status == "pending":
                if st.button("⏭ Skip", key=f"skip_{dn}", use_container_width=True):
                    update_day_status(uid, plan_id, dn, "skipped")
                    st.rerun()
            elif status == "skipped":
                if st.button("↩ Restore", key=f"unskip_{dn}", use_container_width=True):
                    update_day_status(uid, plan_id, dn, "pending")
                    st.rerun()

        with btn_col4:
            pass  # spacer

        # Expanded content
        if expanded:
            st.markdown(f"""
            <div style="margin-left:0; margin-bottom:8px;">
                <div class="day-content-wrap" style="
                    background:#0d1524;
                    border:1px solid #1a2540;
                    border-top: none;
                    border-radius: 0 0 14px 14px;
                    padding: 16px 20px;
                    font-size: 0.84rem;
                    color: #8090a8;
                    line-height: 1.75;
                ">
                    {content.replace(chr(10), '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.download_button(
        "⬇️ Export Roadmap .txt", plan_text,
        file_name="learning_roadmap.txt",
        use_container_width=False
    )
