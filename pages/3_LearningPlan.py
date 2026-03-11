"""
pages/3_LearningPlan.py
Dynamic Winding Roadmap — nodes adapt to mastery, click to study, locked progression.
"""

import streamlit as st
import re
import json
from datetime import datetime, date, timedelta
from database.db import (get_subject_summary, get_error_topics,
                          save_learning_plan, get_latest_plan, get_latest_plan_id,
                          save_plan_days, get_plan_days,
                          update_day_status, get_profile,
                          add_xp, get_level_title)
from llm.llm_engine import generate_learning_plan

st.set_page_config(page_title="Roadmap | LLM-ITS", page_icon="🗺️", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=Instrument+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'Instrument Sans', sans-serif; }
.stApp { background: #080c14; color: #d4dbe8; }

.hud-header {
    background: linear-gradient(160deg, #0d1524 0%, #080c14 60%);
    border: 1px solid #1a2540; border-radius: 20px;
    padding: 32px 40px; margin-bottom: 32px;
    position: relative; overflow: hidden;
}
.hud-header::after {
    content: 'ROADMAP'; position: absolute; right: 32px; top: 50%;
    transform: translateY(-50%); font-family: 'Syne', sans-serif;
    font-size: 5rem; font-weight: 800; color: rgba(255,255,255,0.025);
    letter-spacing: 0.15em; pointer-events: none; user-select: none;
}
.hud-title { font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800; color:#f0f6ff; margin:0 0 4px 0; }
.hud-sub   { color:#4a6080; font-size:0.88rem; margin:0; font-weight:300; }

/* ── Progress HUD ── */
.progress-hud { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:28px; }
.hud-cell { background:#0d1524; border:1px solid #1a2540; border-radius:14px; padding:18px 20px; position:relative; overflow:hidden; }
.hud-cell::before { content:''; position:absolute; bottom:0; left:0; right:0; height:2px; }
.hud-cell.completed::before { background:linear-gradient(90deg,#10b981,#059669); }
.hud-cell.pending::before   { background:linear-gradient(90deg,#3b82f6,#1d4ed8); }
.hud-cell.total::before     { background:linear-gradient(90deg,#8b5cf6,#6d28d9); }
.hud-cell.xp::before        { background:linear-gradient(90deg,#f59e0b,#d97706); }
.hud-num { font-family:'Syne',sans-serif; font-size:2.4rem; font-weight:800; line-height:1; margin-bottom:4px; }
.hud-cell.completed .hud-num { color:#10b981; }
.hud-cell.pending   .hud-num { color:#3b82f6; }
.hud-cell.total     .hud-num { color:#8b5cf6; }
.hud-cell.xp        .hud-num { color:#f59e0b; }
.hud-label { font-size:0.7rem; color:#3a5070; text-transform:uppercase; letter-spacing:0.1em; font-weight:500; }

/* ── Progress bar ── */
.progress-track-bar { height:6px; background:#0d1524; border-radius:10px; overflow:hidden; margin:8px 0 6px 0; border:1px solid #1a2540; }
.progress-track-fill { height:100%; border-radius:10px; background:linear-gradient(90deg,#10b981,#3b82f6,#8b5cf6); transition:width 0.6s ease; }
.progress-caption { display:flex; justify-content:space-between; font-size:0.72rem; color:#3a5070; }

/* ── Winding Roadmap ── */
.roadmap-container { position:relative; padding:20px 0 40px 0; }

.road-node-row { display:flex; align-items:center; margin-bottom:0; position:relative; }
.road-node-row.left  { justify-content:flex-start;  padding-left:40px; }
.road-node-row.right { justify-content:flex-end;    padding-right:40px; }

/* Connector lines between nodes */
.road-connector {
    position:relative; height:60px;
    display:flex; align-items:center;
}
.road-connector.to-right { justify-content:flex-end; padding-right:80px; }
.road-connector.to-left  { justify-content:flex-start; padding-left:80px; }
.road-connector::before {
    content:'';
    position:absolute;
    width:60%;
    height:3px;
    border-radius:3px;
    border-top:3px dashed #1a2540;
}
.road-connector.to-right::before { right:80px; }
.road-connector.to-left::before  { left:80px; }
.road-connector.done::before { border-top:3px solid #10b981; }

/* Node circle */
.road-node {
    width:72px; height:72px; border-radius:50%;
    display:flex; flex-direction:column;
    align-items:center; justify-content:center;
    border:3px solid; position:relative;
    transition:all 0.2s ease; flex-shrink:0;
    cursor:pointer; z-index:2;
}
.road-node.done {
    background:#064e2e; border-color:#10b981;
    box-shadow:0 0 16px rgba(16,185,129,0.35);
}
.road-node.active {
    background:#1d4ed8; border-color:#60a5fa;
    box-shadow:0 0 20px rgba(96,165,250,0.5), 0 0 40px rgba(96,165,250,0.2);
    animation:activePulse 2s infinite;
}
.road-node.locked {
    background:#0d1120; border-color:#1a2540;
    opacity:0.5; cursor:not-allowed;
}
.road-node.skipped {
    background:#1c1005; border-color:#f59e0b;
    border-style:dashed; opacity:0.6;
}
@keyframes activePulse {
    0%,100% { box-shadow:0 0 20px rgba(96,165,250,0.5),0 0 40px rgba(96,165,250,0.2); }
    50%      { box-shadow:0 0 28px rgba(96,165,250,0.8),0 0 56px rgba(96,165,250,0.4); }
}
.node-icon { font-size:1.4rem; line-height:1; }
.node-num  { font-family:'Syne',sans-serif; font-size:0.6rem; font-weight:800;
             color:#3a5070; margin-top:2px; }
.road-node.done   .node-num { color:#10b981; }
.road-node.active .node-num { color:#fff; }

/* Node label card */
.node-label-card {
    background:#0d1524; border:1px solid #1a2540;
    border-radius:12px; padding:10px 14px;
    max-width:200px; margin:0 14px;
    transition:all 0.2s;
}
.node-label-card.done   { border-color:#064e2e; background:#081810; }
.node-label-card.active { border-color:#2563eb; background:#0d1a2e;
                           box-shadow:0 0 0 1px rgba(59,130,246,0.2); }
.node-label-card.locked { opacity:0.4; }
.nlc-day   { font-size:0.62rem; text-transform:uppercase; letter-spacing:0.1em;
             font-weight:600; margin-bottom:3px; }
.nlc-day.done   { color:#10b981; }
.nlc-day.active { color:#60a5fa; }
.nlc-day.locked { color:#2a4060; }
.nlc-day.skipped{ color:#f59e0b; }
.nlc-title { font-family:'Syne',sans-serif; font-size:0.82rem; font-weight:600; color:#d4dbe8; }
.nlc-title.done   { color:#6b7a80; text-decoration:line-through; }
.nlc-title.locked { color:#2a4060; }
.nlc-badge { display:inline-block; font-size:0.62rem; border-radius:20px;
             padding:2px 8px; margin-top:4px; font-weight:500; }
.badge-done    { background:#064e2e; color:#34d399; border:1px solid #059669; }
.badge-active  { background:#1d4ed8; color:#fff; border:1px solid #3b82f6; }
.badge-locked  { background:#0d1120; color:#2a4060; border:1px solid #1a2540; }
.badge-skipped { background:#1c1005; color:#fbbf24; border:1px solid #92400e; }
.badge-pending { background:#0d1a2e; color:#60a5fa; border:1px solid #1d4ed8; }

/* Milestone flag */
.milestone-flag {
    background:linear-gradient(135deg,#7c3aed,#4f46e5);
    border:1px solid #6d28d9; border-radius:12px;
    padding:8px 16px; margin:8px auto; text-align:center;
    font-family:'Syne',sans-serif; font-size:0.75rem;
    font-weight:700; color:#e9d5ff; letter-spacing:0.05em;
    max-width:200px; box-shadow:0 0 16px rgba(109,40,217,0.3);
}

/* Detail panel */
.detail-panel {
    background:#0d1524; border:1px solid #2563eb;
    border-radius:16px; padding:20px 24px; margin:16px 0;
    box-shadow:0 0 0 1px rgba(59,130,246,0.15), 0 8px 32px rgba(0,0,0,0.4);
    animation:slideDown 0.2s ease;
}
@keyframes slideDown { from{opacity:0;transform:translateY(-8px)} to{opacity:1;transform:translateY(0)} }
.dp-header { font-family:'Syne',sans-serif; font-size:1rem; font-weight:700;
             color:#f0f6ff; margin-bottom:10px; }
.dp-content { font-size:0.84rem; color:#8090a8; line-height:1.75; }
.dp-subject-tag {
    display:inline-block; background:#1d4ed8; color:#bfdbfe;
    border-radius:8px; padding:3px 10px; font-size:0.7rem;
    font-weight:600; margin-bottom:10px; border:1px solid #2563eb;
}

/* Mastery chips */
.mastery-row { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:24px; }
.mastery-chip { border-radius:12px; padding:12px 18px; display:flex; flex-direction:column; gap:2px; flex:1; min-width:120px; border:1px solid; }
.mastery-chip.strong   { background:#081810; border-color:#064e2e; }
.mastery-chip.moderate { background:#141005; border-color:#78350f; }
.mastery-chip.weak     { background:#180808; border-color:#7f1d1d; }
.mastery-chip .subj { font-family:'Syne',sans-serif; font-size:0.8rem; font-weight:600; }
.mastery-chip.strong   .subj { color:#34d399; }
.mastery-chip.moderate .subj { color:#fbbf24; }
.mastery-chip.weak     .subj { color:#f87171; }
.mastery-chip .pct { font-family:'Syne',sans-serif; font-size:1.3rem; font-weight:800; color:#d4dbe8; }
.mastery-chip .wk  { font-size:0.68rem; color:#4a6080; }

.meta-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:20px; }
.meta-cell { background:#0d1524; border:1px solid #1a2540; border-radius:12px; padding:14px 16px; }
.meta-cell .val { font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:800; color:#f0f6ff; }
.meta-cell .lbl { font-size:0.68rem; color:#3a5070; text-transform:uppercase; letter-spacing:0.1em; }

.section-label { font-size:0.68rem; font-weight:600; letter-spacing:0.12em;
                 text-transform:uppercase; color:#2a4060; margin:20px 0 10px 0; }

.stButton > button {
    border-radius:12px !important; font-family:'Instrument Sans',sans-serif !important;
    font-size:0.84rem !important; font-weight:500 !important;
    transition:all 0.2s ease !important; border:1px solid #1a2540 !important;
    background:#0d1524 !important; color:#8090a8 !important;
}
.stButton > button:hover { background:#101b2e !important; border-color:#2a4060 !important; color:#d4dbe8 !important; }
button[kind="primary"] {
    background:linear-gradient(135deg,#1d4ed8,#1e3a8a) !important;
    border-color:#2563eb !important; color:#fff !important; font-weight:600 !important;
}
button[kind="primary"]:hover {
    background:linear-gradient(135deg,#2563eb,#1d4ed8) !important;
    box-shadow:0 4px 20px rgba(37,99,235,0.35) !important; transform:translateY(-1px) !important;
}
hr { border-color:#1a2540 !important; }
[data-baseweb="select"] { background:#0d1524 !important; border-color:#1a2540 !important; border-radius:10px !important; }

/* Dynamic alert */
.dynamic-alert {
    background:#0f1a0f; border:1px solid #166534; border-radius:12px;
    padding:12px 18px; margin-bottom:20px; font-size:0.82rem; color:#4ade80;
    display:flex; align-items:center; gap:10px;
}
.dynamic-alert.warn {
    background:#1c1005; border-color:#92400e; color:#fbbf24;
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


def first_line(text):
    for line in text.split("\n"):
        line = line.strip().lstrip("*•-#").strip()
        if len(line) > 6:
            return line[:55] + ("…" if len(line) > 55 else "")
    return "Study Session"


def extract_subject_from_content(content, subjects):
    """Guess which subject this day covers based on content keywords."""
    content_lower = content.lower()
    for subj in subjects:
        if subj.lower() in content_lower:
            return subj
    return subjects[0] if subjects else ""


def extract_topic_from_content(content):
    """Extract the main topic from day content."""
    for line in content.split("\n"):
        line = line.strip().lstrip("*•-#:").strip()
        if len(line) > 6:
            # Remove common prefixes like "Study:", "Topic:", etc.
            for prefix in ["study:", "topic:", "focus:", "review:", "cover:"]:
                if line.lower().startswith(prefix):
                    line = line[len(prefix):].strip()
            return line[:80]
    return content[:80]


def get_mastery_snapshot(summaries):
    return {s["subject"]: {"accuracy": s["avg_accuracy"], "label": s["strength_label"]} for s in summaries}


def should_regenerate(old_snapshot, new_summaries):
    """Check if mastery has changed significantly since last generation."""
    if not old_snapshot:
        return False
    for s in new_summaries:
        subj = s["subject"]
        if subj in old_snapshot:
            old_acc = old_snapshot[subj].get("accuracy", 0)
            new_acc = s["avg_accuracy"]
            if abs(new_acc - old_acc) >= 15:  # 15% change triggers regen suggestion
                return True
    return False


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
    <div class="hud-sub">Your dynamic personalized journey — adapts as your mastery grows.</div>
</div>
""", unsafe_allow_html=True)

col_main, col_side = st.columns([3, 1])

# ══ SIDEBAR ═══════════════════════════════════════════════════════════════════
with col_side:
    st.markdown('<div class="section-label">Mission Stats</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="meta-grid">
        <div class="meta-cell"><div class="val">{days_left}</div><div class="lbl">Days Left</div></div>
        <div class="meta-cell"><div class="val">{profile.get('daily_hours', 2)}h</div><div class="lbl">Daily</div></div>
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
            if plan_text.startswith("[Error"):
                st.error(f"Failed to generate roadmap: {plan_text}")
                st.stop()
                
            snap      = get_mastery_snapshot(disp_sum)
            save_learning_plan(uid, plan_text, weak_topics_by_subject, snap, deadline_str, days_left)
            plan_id = get_latest_plan_id(uid)
            parsed  = parse_plan_into_days(plan_text)
            if parsed:
                save_plan_days(uid, plan_id, parsed)
            st.session_state["plan_text"]       = plan_text
            st.session_state["plan_id"]         = plan_id
            st.session_state["mastery_snapshot"] = snap
            st.session_state.pop("selected_node", None)
            st.success("✅ Roadmap generated!")
            st.rerun()

# ══ MAIN ══════════════════════════════════════════════════════════════════════
with col_main:
    plan_text = st.session_state.get("plan_text")
    plan_id   = st.session_state.get("plan_id")

    if not plan_text:
        saved = get_latest_plan(uid)
        if saved:
            plan_text = saved["plan_text"]
            plan_id   = saved["plan_id"]
            st.session_state["plan_text"] = plan_text
            st.session_state["plan_id"]   = plan_id
            try:
                snap = json.loads(saved.get("mastery_snapshot", "{}").replace("'", '"'))
            except:
                snap = {}
            st.session_state["mastery_snapshot"] = snap

    if not plan_text:
        st.markdown("""
        <div style="text-align:center; padding:80px 20px; color:#2a4060;">
            <div style="font-size:3.5rem; margin-bottom:20px;">🗺️</div>
            <div style="font-family:'Syne',sans-serif; font-size:1.6rem; color:#3a5070; margin-bottom:10px; font-weight:700;">No roadmap yet</div>
            <div style="font-size:0.85rem; color:#2a4060;">Click <strong style="color:#3b82f6;">Generate New Roadmap</strong> to plot your learning path.</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # Load days
    days = get_plan_days(uid, plan_id) if plan_id else []
    if not days:
        days = parse_plan_into_days(plan_text)
        if days and plan_id:
            save_plan_days(uid, plan_id, days)
            days = get_plan_days(uid, plan_id)

    if not days:
        st.warning("Could not parse plan.")
        st.markdown(plan_text)
        st.stop()

    # ── Dynamic mastery check ─────────────────────────────────────────
    old_snap = st.session_state.get("mastery_snapshot", {})
    if summaries and should_regenerate(old_snap, summaries):
        st.markdown("""
        <div class="dynamic-alert warn">
            ⚡ Your mastery has improved significantly since this roadmap was generated.
            Consider regenerating for a more accurate plan!
        </div>
        """, unsafe_allow_html=True)

    # ── Stats ─────────────────────────────────────────────────────────
    total     = len(days)
    completed = sum(1 for d in days if d["status"] == "completed")
    skipped   = sum(1 for d in days if d["status"] == "skipped")
    pending   = total - completed - skipped
    pct       = completed / total if total > 0 else 0
    fill_pct  = round(pct * 100)

    # XP from plan completion
    plan_xp = completed * 20

    st.markdown(f"""
    <div class="progress-hud">
        <div class="hud-cell total">
            <div class="hud-num">{total}</div><div class="hud-label">Total Days</div>
        </div>
        <div class="hud-cell completed">
            <div class="hud-num">{completed}</div><div class="hud-label">Completed</div>
        </div>
        <div class="hud-cell pending">
            <div class="hud-num">{pending}</div><div class="hud-label">Remaining</div>
        </div>
        <div class="hud-cell xp">
            <div class="hud-num">{plan_xp}</div><div class="hud-label">XP Earned</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div>
        <div class="progress-track-bar">
            <div class="progress-track-fill" style="width:{fill_pct}%"></div>
        </div>
        <div class="progress-caption">
            <span>{completed} of {total} days completed — {fill_pct}%</span>
            <span>Deadline: {deadline_date}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Milestone celebrations ────────────────────────────────────────
    prev_pct = st.session_state.get("prev_completion_pct", 0)
    for milestone in [25, 50, 75, 100]:
        if prev_pct < milestone <= fill_pct:
            st.balloons()
            msgs = {
                25:  "🎉 25% done! Great start — keep the momentum!",
                50:  "🔥 Halfway there! You're crushing it!",
                75:  "⚡ 75% complete! The finish line is in sight!",
                100: "🏆 ROADMAP COMPLETE! You're a champion!",
            }
            st.success(msgs[milestone])
st.session_state["prev_completion_pct"] = fill_pct

with col_main:
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Find active (current) node ─────────────────────────────────────
    active_day = None
    for d in days:
        if d["status"] == "pending":
            active_day = d["day_number"]
            break

    selected_node = st.session_state.get("selected_node", None)

    # ── Winding Roadmap ────────────────────────────────────────────────
    MILESTONE_DAYS = {
        round(total * 0.25): "🚩 25% Milestone",
        round(total * 0.50): "⭐ Halfway Point",
        round(total * 0.75): "🔥 Final Stretch",
        total:               "🏆 Exam Ready!",
    }

    st.markdown('<div class="roadmap-container">', unsafe_allow_html=True)

    for i, day in enumerate(days):
        dn     = day["day_number"]
        status = day.get("status", "pending")
        content= day.get("content", "")

        is_active = (dn == active_day)
        is_locked = (status == "pending" and not is_active)

        # Determine node class
        if status == "completed":
            node_cls = "done"
            badge    = '<span class="nlc-badge badge-done">✓ Done</span>'
            icon     = "✓"
        elif is_active:
            node_cls = "active"
            badge    = '<span class="nlc-badge badge-active">▶ Today</span>'
            icon     = "▶"
        elif status == "skipped":
            node_cls = "skipped"
            badge    = '<span class="nlc-badge badge-skipped">↷ Skipped</span>'
            icon     = "↷"
        elif is_locked:
            node_cls = "locked"
            badge    = '<span class="nlc-badge badge-locked">🔒 Locked</span>'
            icon     = "🔒"
        else:
            node_cls = "pending"
            badge    = '<span class="nlc-badge badge-pending">○ Pending</span>'
            icon     = str(dn)

        title      = first_line(content)
        side       = "left" if i % 2 == 0 else "right"
        label_side = "right" if side == "left" else "left"

        # Milestone flag before this node?
        if dn in MILESTONE_DAYS:
            st.markdown(f'<div class="milestone-flag">{MILESTONE_DAYS[dn]}</div>', unsafe_allow_html=True)

        # Node row — use columns for zigzag
        if side == "left":
            n1, n2, n3 = st.columns([0.15, 0.25, 0.6])
        else:
            n1, n2, n3 = st.columns([0.6, 0.25, 0.15])

        node_col  = n2
        label_col = n3 if side == "left" else n1

        with node_col:
            # Clickable node button (only if not locked)
            if not is_locked:
                btn_label = f"{icon}\nDay {dn}"
                if st.button(btn_label, key=f"node_{dn}",
                             help=title if not is_locked else "Complete previous day first",
                             use_container_width=True):
                    if selected_node == dn:
                        st.session_state["selected_node"] = None
                    else:
                        st.session_state["selected_node"] = dn
                    st.rerun()
            else:
                st.markdown(
                    f'<div class="road-node {node_cls}" title="Complete previous day first">'
                    f'<div class="node-icon">🔒</div>'
                    f'<div class="node-num">Day {dn}</div></div>',
                    unsafe_allow_html=True
                )

        with label_col:
            st.markdown(
                f'<div class="node-label-card {node_cls}">'
                f'<div class="nlc-day {node_cls}">Day {dn}</div>'
                f'<div class="nlc-title {node_cls}">{title}</div>'
                f'{badge}</div>',
                unsafe_allow_html=True
            )

        # ── Detail panel when node is selected ────────────────────────
        if selected_node == dn and not is_locked:
            subj  = extract_subject_from_content(content, subjects)
            topic = extract_topic_from_content(content)

            safe_content = content.replace("\n", "<br>")
            st.markdown(
                f'<div class="detail-panel">'
                f'<div class="dp-subject-tag">📚 {subj}</div>'
                f'<div class="dp-header">Day {dn} — {title}</div>'
                f'<div class="dp-content">{safe_content}</div></div>',
                unsafe_allow_html=True
            )

            act1, act2, act3, act4 = st.columns(4)

            # Study this topic button → goes to study page
            with act1:
                if st.button("📖 Study This Topic", key=f"study_{dn}", type="primary", use_container_width=True):
                    st.session_state["study_subject"]  = subj
                    st.session_state["selected_topic"] = topic
                    st.session_state["chat_history"]   = []
                    st.switch_page("pages/1_Study.py")

            with act2:
                if status != "completed":
                    if st.button("✅ Mark Complete", key=f"done_{dn}", use_container_width=True):
                        update_day_status(uid, plan_id, dn, "completed")
                        # Award XP for completing a day
                        try:
                            add_xp(uid, 100)  # treat as high accuracy for plan completion
                        except:
                            pass
                        st.session_state["selected_node"] = None
                        st.rerun()
                else:
                    if st.button("↩ Undo", key=f"undo_{dn}", use_container_width=True):
                        update_day_status(uid, plan_id, dn, "pending")
                        st.rerun()

            with act3:
                if status == "pending" and is_active:
                    if st.button("⏭ Skip Day", key=f"skip_{dn}", use_container_width=True):
                        update_day_status(uid, plan_id, dn, "skipped")
                        st.session_state["selected_node"] = None
                        st.rerun()
                elif status == "skipped":
                    if st.button("↩ Restore", key=f"unskip_{dn}", use_container_width=True):
                        update_day_status(uid, plan_id, dn, "pending")
                        st.rerun()

            with act4:
                if st.button("✖ Close", key=f"close_{dn}", use_container_width=True):
                    st.session_state["selected_node"] = None
                    st.rerun()

        # Connector line between nodes (except last)
        if i < len(days) - 1:
            conn_done = (status == "completed")
            conn_color = "#10b981" if conn_done else "#1a2540"
            conn_shadow = "box-shadow:0 0 8px rgba(16,185,129,0.4);" if conn_done else ""
            st.markdown(
                f'<div style="height:32px;display:flex;align-items:center;justify-content:center;">'
                f'<div style="width:3px;height:100%;background:{conn_color};'
                f'border-radius:3px;margin:0 auto;{conn_shadow}"></div></div>',
                unsafe_allow_html=True
            )

    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ── Dynamic mastery alert at bottom ───────────────────────────────
    if summaries:
        weak_subjects = [s["subject"] for s in summaries if s["strength_label"] == "Weak"]
        if weak_subjects:
            st.markdown(f"""
            <div class="dynamic-alert warn">
                🔴 Weak subjects detected: <strong>{', '.join(weak_subjects)}</strong>.
                Regenerate your roadmap to prioritize these topics.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="dynamic-alert">
                ✅ All subjects at Moderate or Strong — your roadmap is well-balanced!
            </div>
            """, unsafe_allow_html=True)

    st.download_button(
        "⬇️ Export Roadmap .txt", plan_text,
        file_name="learning_roadmap.txt",
        use_container_width=False
    )
