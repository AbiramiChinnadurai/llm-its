"""
pages/2_Quiz.py
Quiz page — MCQ generation, answer evaluation, and AEL update.
"""

import streamlit as st
import time
from database.db import (log_quiz_attempt, get_error_topics, get_ael_modality,
                          update_ael, log_error_topic, get_recent_accuracy,
                          get_subject_summary)
from llm.llm_engine import generate_quiz_question, MODALITY_LABELS

st.set_page_config(page_title="Quiz | LLM-ITS", page_icon="🧠", layout="wide")

if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid      = st.session_state.uid
profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("quiz_question",    None),
    ("quiz_answered",    False),
    ("quiz_score",       0),
    ("quiz_total",       0),
    ("quiz_start_time",  None),
    ("prev_questions",   []),
    ("quiz_subject",     subjects[0]),
    ("quiz_topic",       ""),
    ("session_results",  []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Layout ────────────────────────────────────────────────────────────────────
st.title("🧠 Quiz Mode")
st.caption("AI-generated questions adapted to your mastery level. The system adjusts how it explains based on your performance.")

col_main, col_side = st.columns([3, 1])

with col_side:
    st.subheader("⚙️ Quiz Settings")
    subject = st.selectbox("Subject", subjects)
    st.session_state.quiz_subject = subject

    topic = st.text_input("Topic", placeholder="e.g. Sorting Algorithms")
    st.session_state.quiz_topic = topic

    summaries = get_subject_summary(uid)
    mastery   = next((s["strength_label"] for s in summaries
                      if s["subject"] == subject), "Weak")

    st.divider()
    color_map = {"Strong": "🟢", "Moderate": "🟡", "Weak": "🔴"}
    st.markdown(f"**Mastery:** {color_map.get(mastery,'')} {mastery}")

    active_topic = topic if topic else "general"
    modality_idx = get_ael_modality(uid, subject, active_topic)
    st.markdown(f"**AEL Modality:** M={modality_idx} — {MODALITY_LABELS.get(modality_idx,'')}")

    st.divider()
    st.markdown("**📊 Session Score**")
    total = st.session_state.quiz_total
    score = st.session_state.quiz_score
    if total > 0:
        pct = round((score / total) * 100, 1)
        st.metric("Accuracy", f"{pct}%", f"{score}/{total} correct")
        st.progress(pct / 100)
    else:
        st.caption("No attempts yet this session.")

with col_main:
    # ── Generate new question ─────────────────────────────────────────────────
    gen_col, clear_col = st.columns([2, 1])
    with gen_col:
        if st.button("🎯 Generate Question", type="primary", use_container_width=True,
                     disabled=not topic):
            if not topic:
                st.error("Please enter a topic first.")
            else:
                with st.spinner("Generating question..."):
                    q = generate_quiz_question(
                        subject, topic, mastery,
                        st.session_state.prev_questions
                    )
                if q:
                    st.session_state.quiz_question   = q
                    st.session_state.quiz_answered   = False
                    st.session_state.quiz_start_time = time.time()
                else:
                    st.error("Could not generate question. Try again.")

    with clear_col:
        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.quiz_score    = 0
            st.session_state.quiz_total    = 0
            st.session_state.prev_questions = []
            st.session_state.session_results = []
            st.session_state.quiz_question = None
            st.rerun()

    if not topic:
        st.info("👆 Enter a topic and click **Generate Question** to start.")

    # ── Display question ──────────────────────────────────────────────────────
    q = st.session_state.quiz_question
    if q:
        st.divider()
        st.subheader(f"📝 Question")
        st.markdown(f"**{q['question']}**")
        st.caption(f"Subject: {subject}  |  Topic: {topic}  |  Difficulty: {mastery}")
        st.divider()

        if not st.session_state.quiz_answered:
            # Answer options as radio buttons
            choice = st.radio(
                "Select your answer:",
                q["options"],
                index=None,
                key=f"radio_{st.session_state.quiz_total}"
            )

            if st.button("✅ Submit Answer", type="primary",
                         disabled=(choice is None), use_container_width=True):
                elapsed = round(time.time() - (st.session_state.quiz_start_time or time.time()), 2)
                selected_idx = q["options"].index(choice)
                correct_idx  = q["correct_index"]
                is_correct   = (selected_idx == correct_idx)

                st.session_state.quiz_answered = True
                st.session_state.quiz_total   += 1
                if is_correct:
                    st.session_state.quiz_score += 1

                # Log to DB
                score_val = 1 if is_correct else 0
                accuracy  = log_quiz_attempt(
                    uid, subject, topic, score_val, 1, elapsed, modality_idx
                )

                # Log error topics if wrong
                if not is_correct:
                    log_error_topic(uid, subject, topic)

                # Update AEL
                recent_acc = get_recent_accuracy(uid, subject, topic, n=2)
                new_m      = update_ael(uid, subject, topic, recent_acc)

                # Store result
                st.session_state.session_results.append({
                    "topic":     topic,
                    "correct":   is_correct,
                    "latency":   elapsed,
                    "modality":  modality_idx,
                    "new_m":     new_m
                })

                # Track previous questions
                st.session_state.prev_questions.append(q["question"])
                st.rerun()

        else:
            # Show result
            last = st.session_state.session_results[-1] if st.session_state.session_results else {}
            correct_idx = q["correct_index"]

            if last.get("correct"):
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect. Correct answer: **{q['options'][correct_idx]}**")

            st.info(f"💡 **Explanation:** {q['explanation']}")

            # AEL feedback
            new_m     = last.get("new_m", modality_idx)
            new_label = MODALITY_LABELS.get(new_m, "")
            if new_m > modality_idx:
                st.warning(f"🔄 AEL Update: Explanation style → **M={new_m}: {new_label}** (simplified to help you better)")
            elif new_m < modality_idx:
                st.success(f"🔄 AEL Update: Explanation style → **M={new_m}: {new_label}** (advanced — great progress!)")

            if st.button("➡️ Next Question", type="primary", use_container_width=True):
                st.session_state.quiz_question = None
                st.rerun()

    # ── Session summary ───────────────────────────────────────────────────────
    if st.session_state.session_results:
        st.divider()
        with st.expander("📋 Session History", expanded=False):
            for i, r in enumerate(st.session_state.session_results, 1):
                icon = "✅" if r["correct"] else "❌"
                st.caption(
                    f"{i}. {icon} {r['topic']} | "
                    f"⏱️ {r['latency']}s | "
                    f"M={r['modality']}→{r['new_m']}"
                )
