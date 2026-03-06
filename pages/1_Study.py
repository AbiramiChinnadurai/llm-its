"""
pages/1_Study.py
Study page — auto-extracted topic list from PDF + RAG explanations with AEL.
"""

import streamlit as st
import time
from database.db import (get_subject_summary, get_error_topics,
                          get_ael_modality, get_topics)
from rag.rag_pipeline import retrieve_chunks, format_context, index_exists
from llm.llm_engine import generate_explanation, MODALITY_LABELS

st.set_page_config(page_title="Study | LLM-ITS", page_icon="📖", layout="wide")

if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid      = st.session_state.uid
profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

if "chat_history"   not in st.session_state: st.session_state.chat_history   = []
if "study_subject"  not in st.session_state: st.session_state.study_subject  = subjects[0]
if "selected_topic" not in st.session_state: st.session_state.selected_topic = None

st.title("📖 Study with Your AI Tutor")
st.caption("Pick a topic from your syllabus — the AI answers only from your uploaded curriculum.")

col_main, col_side = st.columns([3, 1])

# ── SIDEBAR: Topic list ───────────────────────────────────────────────────────
with col_side:
    st.subheader("📚 Your Topics")

    subject = st.selectbox("Subject", subjects, key="study_subj_sel")
    if subject != st.session_state.study_subject:
        st.session_state.study_subject  = subject
        st.session_state.selected_topic = None
        st.session_state.chat_history   = []

    topics = get_topics(subject)

    if not topics:
        st.warning(f"No topics for **{subject}**.\n\nGo to **Upload Syllabus** and upload your PDF first.")
    else:
        # Search filter
        search = st.text_input("🔍 Search topics", placeholder="Type to filter...")
        filtered = [t for t in topics if search.lower() in t.lower()] if search else topics
        st.caption(f"Showing {len(filtered)} of {len(topics)} topics")
        st.divider()

        for t in filtered:
            is_active = (t == st.session_state.selected_topic)
            if st.button(
                f"{'▶ ' if is_active else ''}{t}",
                key=f"t_{t}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                if st.session_state.selected_topic != t:
                    st.session_state.selected_topic = t
                    st.session_state.chat_history   = []
                st.rerun()

    # ── AEL status ────────────────────────────────────────────────────
    st.divider()
    active_topic = st.session_state.selected_topic or "general"
    m_idx  = get_ael_modality(uid, subject, active_topic)
    m_lbl  = MODALITY_LABELS.get(m_idx, "Standard Prose")
    icons  = ["🔵","🟢","🟡","🟠","🔴"]
    st.markdown("**🔄 Explanation Style**")
    st.info(f"{icons[m_idx]} M={m_idx}: **{m_lbl}**")
    st.caption("Auto-adapts from your quiz results.")

    # Weak topics shortcut
    weak = get_error_topics(uid, subject)
    if weak:
        st.divider()
        st.markdown("**⚠️ Weak Topics**")
        for t in weak:
            if st.button(f"🔴 {t}", key=f"w_{t}", use_container_width=True):
                st.session_state.selected_topic = t
                st.session_state.chat_history   = []
                st.rerun()

    # Index status
    st.divider()
    if index_exists(subject):
        st.success("✅ Syllabus indexed")
    else:
        st.warning("⚠️ Upload syllabus first")

# ── MAIN: Chat area ───────────────────────────────────────────────────────────
with col_main:
    selected_topic = st.session_state.selected_topic

    if not selected_topic:
        st.info("👈 **Select a topic** from the left to start studying.")
        if not get_topics(subject):
            st.warning("No topics found. Go to **Upload Syllabus** (sidebar) to upload your PDF.")
        st.stop()

    # Header
    hcol1, hcol2 = st.columns([4, 1])
    with hcol1:
        st.subheader(f"📖 {selected_topic}")
    with hcol2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    # Suggested starter questions (shown only when chat is empty)
    if not st.session_state.chat_history:
        st.markdown("**💡 Quick start:**")
        suggestions = [
            f"Explain {selected_topic} in simple terms",
            f"What are the key concepts in {selected_topic}?",
            f"Give me a real-world example of {selected_topic}",
            f"What are common mistakes in {selected_topic}?",
        ]
        sc1, sc2 = st.columns(2)
        for i, sug in enumerate(suggestions):
            col = sc1 if i % 2 == 0 else sc2
            if col.button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state["_prefill"] = sug
                st.rerun()
        st.divider()

    # Render chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                st.caption(
                    f"🔄 {MODALITY_LABELS.get(msg.get('modality', 0), '')}  "
                    f"|  ⏱️ {msg.get('latency', '?')}s  "
                    f"|  📚 {msg.get('chunks', 0)} chunks"
                )

    # Chat input
    prefill = st.session_state.pop("_prefill", None)
    query   = st.chat_input(f"Ask about {selected_topic}...")
    q = prefill or query

    if q:
        st.session_state.chat_history.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)

        with st.chat_message("assistant"):
            with st.spinner("Searching syllabus and generating answer..."):
                # Gather context
                summaries   = get_subject_summary(uid)
                mastery     = next((s["strength_label"] for s in summaries
                                    if s["subject"] == subject), "Moderate")
                weak_topics = get_error_topics(uid, subject)
                m_idx       = get_ael_modality(uid, subject, selected_topic)

                chunks  = retrieve_chunks(subject, q,
                                          weak_topics=weak_topics,
                                          mastery_level=mastery)
                context = format_context(chunks)

                llm_profile = {
                    "education_level": profile.get("education_level", "undergraduate"),
                    "current_subject": subject,
                    "mastery_level":   mastery,
                    "weak_topics":     weak_topics,
                }
                # Last 3 turns as history
                hist = st.session_state.chat_history
                history_turns = []
                for i in range(0, len(hist) - 1, 2):
                    if i + 1 < len(hist):
                        history_turns.append({
                            "student": hist[i]["content"],
                            "tutor":   hist[i+1]["content"]
                        })

                t0       = time.time()
                response = generate_explanation(q, context, llm_profile,
                                                m_idx, history_turns)
                elapsed  = round(time.time() - t0, 2)

            st.markdown(response)
            st.caption(
                f"🔄 **{MODALITY_LABELS.get(m_idx, '')}**  "
                f"|  ⏱️ {elapsed}s  "
                f"|  📚 {len(chunks)} chunks retrieved"
            )
            if not chunks:
                st.warning("⚠️ No syllabus found — upload your PDF in **Upload Syllabus**.")

        st.session_state.chat_history.append({
            "role": "assistant", "content": response,
            "modality": m_idx, "latency": elapsed, "chunks": len(chunks)
        })
