"""
pages/3_LearningPlan.py
Learning Plan — mark days complete/skip, auto-reschedule pending days.
"""

import streamlit as st
import re
from datetime import datetime, date, timedelta
from database.db import (get_subject_summary, get_error_topics,
                          save_learning_plan, get_latest_plan, get_latest_plan_id,
                          save_plan_days, get_plan_days,
                          update_day_status, get_profile)
from llm.llm_engine import generate_learning_plan

st.set_page_config(page_title="Learning Plan | LLM-ITS", page_icon="🗓️", layout="wide")

if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid      = st.session_state.uid
profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_plan_into_days(plan_text):
    """Parse LLM plan text into list of day dicts."""
    days = []
    # Match "Day 1:", "Day 1 -", "**Day 1**", "DAY 1"
    matches = re.findall(
        r'(?:^|\n)\s*\*{0,2}(Day\s+\d+)\*{0,2}[:\-–]?\s*(.*?)(?=\n\s*\*{0,2}Day\s+\d+|\Z)',
        plan_text, re.IGNORECASE | re.DOTALL
    )
    if matches:
        for i, (label, content) in enumerate(matches, 1):
            days.append({
                "day_number": i,
                "day_label":  label.strip(),
                "content":    content.strip()
            })
    else:
        # Fallback — split into ~7 chunks
        lines = [l.strip() for l in plan_text.split("\n") if l.strip()]
        size  = max(3, len(lines) // 7)
        for i, start in enumerate(range(0, len(lines), size), 1):
            chunk = "\n".join(lines[start:start + size])
            if chunk:
                days.append({"day_number": i, "day_label": f"Day {i}", "content": chunk})
    return days


def reschedule(days):
    """
    Auto-reschedule: skipped days get appended to the end
    with a note, preserving pending days in current order.
    Returns reordered list with recalculated day numbers.
    """
    completed = [d for d in days if d["status"] == "completed"]
    pending   = [d for d in days if d["status"] == "pending"]
    skipped   = [d for d in days if d["status"] == "skipped"]

    # Append skipped to end of pending with a note
    rescheduled = []
    for d in skipped:
        new_d = dict(d)
        new_d["content"]  = f"[Rescheduled] {d['content']}"
        new_d["status"]   = "pending"
        rescheduled.append(new_d)

    ordered = completed + pending + rescheduled
    # Renumber
    for i, d in enumerate(ordered, 1):
        d["day_number"] = i
        d["day_label"]  = f"Day {i}"
    return ordered


# ── Load data ─────────────────────────────────────────────────────────────────
summaries              = get_subject_summary(uid)
weak_topics_by_subject = {s: get_error_topics(uid, s) for s in subjects}

deadline_str = profile.get("deadline", str(date.today()))
try:
    deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
except:
    deadline_date = date.today()
days_left = max(1, (deadline_date - date.today()).days)

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("🗓️ Personalized Learning Plan")
st.caption("Mark days complete or skip them — skipped days are automatically rescheduled to the end.")

# ── Status ────────────────────────────────────────────────────────────────────
st.subheader("📊 Your Current Mastery")
if summaries:
    cols = st.columns(len(summaries))
    cm   = {"Strong": "🟢", "Moderate": "🟡", "Weak": "🔴"}
    for col, s in zip(cols, summaries):
        wt = weak_topics_by_subject.get(s["subject"], [])
        col.metric(f"{cm.get(s['strength_label'],'⚪')} {s['subject']}",
                   f"{s['avg_accuracy']:.1f}%", s["strength_label"])
        if wt:
            col.caption("Weak: " + ", ".join(wt[:2]))
else:
    st.info("Take some quizzes first for a more accurate plan.")

st.divider()

# ── Generate ──────────────────────────────────────────────────────────────────
gc1, gc2 = st.columns([3, 1])
with gc2:
    st.metric("📅 Days Left",    days_left)
    st.metric("⏰ Daily Hours",  f"{profile.get('daily_hours', 2)}h")
with gc1:
    if st.button("🤖 Generate New Plan", type="primary", use_container_width=True):
        with st.spinner("Generating your personalized schedule..."):
            llm_profile = {
                "name":          profile.get("name", "Student"),
                "deadline":      deadline_str,
                "daily_hours":   profile.get("daily_hours", 2),
                "learning_goals":profile.get("learning_goals", "Master all subjects")
            }
            disp_sum  = summaries or [
                {"subject": s, "strength_label": "Weak", "avg_accuracy": 0.0}
                for s in subjects
            ]
            plan_text = generate_learning_plan(llm_profile, disp_sum, weak_topics_by_subject)
            snap      = {s["subject"]: s["strength_label"] for s in disp_sum}
            save_learning_plan(uid, plan_text, weak_topics_by_subject,
                               snap, deadline_str, days_left)
            plan_id = get_latest_plan_id(uid)
            parsed  = parse_plan_into_days(plan_text)
            if parsed:
                save_plan_days(uid, plan_id, parsed)
            st.session_state["plan_text"] = plan_text
            st.session_state["plan_id"]   = plan_id
            st.success("✅ Plan generated!")
            st.rerun()

# ── Load plan ─────────────────────────────────────────────────────────────────
plan_text = st.session_state.get("plan_text")
plan_id   = st.session_state.get("plan_id")

if not plan_text:
    saved = get_latest_plan(uid)
    if saved:
        plan_text = saved["plan_text"]
        plan_id   = saved["plan_id"]
        st.session_state["plan_text"] = plan_text
        st.session_state["plan_id"]   = plan_id
        st.caption(f"📌 Generated: {saved['generated_at']}")

if not plan_text:
    st.info("👆 Click **Generate New Plan** to create your schedule.")
    st.stop()

st.divider()

# ── Load or parse days ────────────────────────────────────────────────────────
days = get_plan_days(uid, plan_id) if plan_id else []
if not days:
    days = parse_plan_into_days(plan_text)
    if days and plan_id:
        save_plan_days(uid, plan_id, days)
        days = get_plan_days(uid, plan_id)

if not days:
    st.warning("Could not parse plan into days. Showing full text instead.")
    st.markdown(plan_text)
    st.stop()

# ── Auto-reschedule if any skipped ───────────────────────────────────────────
skipped_count = sum(1 for d in days if d["status"] == "skipped")
if skipped_count:
    reordered = reschedule(days)
    # Persist reordered days
    save_plan_days(uid, plan_id, [
        {"day_number": d["day_number"], "day_label": d["day_label"],
         "content": d["content"]} for d in reordered
    ])
    # Restore statuses
    for orig, new in zip(days, reordered):
        if orig["status"] != "pending":
            update_day_status(uid, plan_id, new["day_number"], orig["status"])
    days = get_plan_days(uid, plan_id)

# ── Progress summary ──────────────────────────────────────────────────────────
total     = len(days)
completed = sum(1 for d in days if d["status"] == "completed")
skipped   = sum(1 for d in days if d["status"] == "skipped")
pending   = total - completed - skipped
pct       = completed / total if total > 0 else 0

p1, p2, p3, p4 = st.columns(4)
p1.metric("📅 Total Days",  total)
p2.metric("✅ Completed",   completed)
p3.metric("⏭️ Skipped",     skipped)
p4.metric("⏳ Remaining",   pending)
st.progress(pct, text=f"{completed} of {total} days completed ({round(pct*100)}%)")

# Estimated completion
if pending > 0:
    est_done = date.today() + timedelta(days=pending)
    on_track = est_done <= deadline_date
    if on_track:
        st.success(f"✅ On track! Estimated completion: **{est_done}** (deadline: {deadline_date})")
    else:
        overdue = (est_done - deadline_date).days
        st.warning(f"⚠️ At current pace you'll finish **{overdue} days after** your deadline ({deadline_date}). Consider reducing skip days.")

st.divider()

# ── Day cards ─────────────────────────────────────────────────────────────────
st.subheader("📋 Day-by-Day Schedule")

STATUS_ICON = {"pending": "⏳", "completed": "✅", "skipped": "⏭️"}
STATUS_BG   = {"completed": "#e8f8e8", "skipped": "#fff3e0", "pending": "#f0f4ff"}

today_day = completed + 1  # next pending day is "today"

for day in days:
    dn      = day["day_number"]
    status  = day.get("status", "pending")
    icon    = STATUS_ICON.get(status, "⏳")
    label   = day.get("day_label", f"Day {dn}")
    content = day.get("content", "")
    is_today = (status == "pending" and dn == today_day)

    header = f"{icon} {label}"
    if is_today:
        header += " ← **Today**"
    if status == "completed":
        header += " — Done"
    elif status == "skipped":
        header += " — Rescheduled to end"

    with st.expander(header, expanded=is_today):
        st.markdown(content)
        st.divider()

        c1, c2, c3 = st.columns(3)

        with c1:
            if status != "completed":
                if st.button("✅ Mark Complete", key=f"done_{dn}",
                             type="primary", use_container_width=True):
                    update_day_status(uid, plan_id, dn, "completed")
                    st.rerun()
            else:
                st.success("✅ Completed")
                if st.button("↩️ Undo", key=f"undo_{dn}", use_container_width=True):
                    update_day_status(uid, plan_id, dn, "pending")
                    st.rerun()

        with c2:
            if status == "pending":
                if st.button("⏭️ Skip — Reschedule", key=f"skip_{dn}",
                             use_container_width=True):
                    update_day_status(uid, plan_id, dn, "skipped")
                    st.info(f"Day {dn} skipped. It will be rescheduled to the end automatically.")
                    st.rerun()
            elif status == "skipped":
                if st.button("↩️ Unskip", key=f"unskip_{dn}",
                             use_container_width=True):
                    update_day_status(uid, plan_id, dn, "pending")
                    st.rerun()

        with c3:
            st.caption(f"Status: **{status.title()}**")

st.divider()
st.download_button("⬇️ Download Plan as .txt", plan_text,
                   file_name="study_plan.txt", use_container_width=False)
