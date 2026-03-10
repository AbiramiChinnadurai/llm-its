"""
pages/1_Study.py
Study page — auto-extracted topic list from PDF + RAG explanations with AEL.
Enhanced UI with professional design, custom CSS, and improved UX.
"""

import streamlit as st
import time
from database.db import (get_subject_summary, get_error_topics,
                          get_ael_modality, get_topics)
from rag.rag_pipeline import retrieve_chunks, format_context, index_exists
from llm.llm_engine import generate_explanation, MODALITY_LABELS

st.set_page_config(page_title="Study | LLM-ITS", page_icon="📖", layout="wide")

# ── Professional CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,300;0,600;1,300&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Page background ── */
.stApp {
    background: #0f1117;
    color: #e8e8e8;
}

/* ── Header ── */
.study-header {
    background: linear-gradient(135deg, #1a1f2e 0%, #12161f 100%);
    border: 1px solid #2a3040;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.study-header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(99,179,237,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.study-header h1 {
    font-family: 'Fraunces', serif;
    font-size: 2rem;
    font-weight: 600;
    color: #f0f4ff;
    margin: 0 0 4px 0;
    letter-spacing: -0.5px;
}
.study-header p {
    color: #7a8499;
    font-size: 0.9rem;
    margin: 0;
    font-weight: 300;
}

/* ── Topic buttons ── */
.stButton > button {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 400 !important;
    transition: all 0.18s ease !important;
    border: 1px solid #2a3040 !important;
    background: #161b27 !important;
    color: #c0c8dc !important;
    text-align: left !important;
}
.stButton > button:hover {
    background: #1e2535 !important;
    border-color: #63b3ed !important;
    color: #f0f4ff !important;
    transform: translateX(3px) !important;
}
button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    border-color: #3b82f6 !important;
    color: #fff !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    box-shadow: 0 4px 16px rgba(59,130,246,0.3) !important;
}

/* ── Sidebar panel ── */
section[data-testid="stSidebar"] {
    background: #0d1018 !important;
    border-right: 1px solid #1e2535;
}

/* ── Sidebar section labels ── */
.sidebar-label {
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4a5568;
    margin: 20px 0 8px 0;
}

/* ── AEL badge ── */
.ael-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #1a2235;
    border: 1px solid #2d3a52;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.8rem;
    color: #93c5fd;
    font-weight: 500;
    margin-top: 6px;
}
.ael-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #3b82f6;
    box-shadow: 0 0 6px rgba(59,130,246,0.6);
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: #161b27 !important;
    border: 1px solid #1e2a3a !important;
    border-radius: 14px !important;
    margin-bottom: 12px !important;
    padding: 16px !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    background: #161b27 !important;
    border: 1px solid #2a3040 !important;
    border-radius: 14px !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}

/* ── Quick start chips ── */
.chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0 20px 0;
}
.chip {
    background: #1a2235;
    border: 1px solid #2d3a52;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.8rem;
    color: #93c5fd;
    cursor: pointer;
    transition: all 0.15s;
}
.chip:hover {
    background: #1e2d4a;
    border-color: #3b82f6;
}

/* ── Topic active state ── */
.topic-active {
    background: linear-gradient(135deg, #1e3a5f, #1a2f4a) !important;
    border-color: #3b82f6 !important;
    color: #93c5fd !important;
}

/* ── Status pills ── */
.status-indexed {
    background: #0d2818;
    border: 1px solid #166534;
    color: #4ade80;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 0.78rem;
    font-weight: 500;
}
.status-missing {
    background: #2d1a0a;
    border: 1px solid #92400e;
    color: #fb923c;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 0.78rem;
}

/* ── Weak topic tags ── */
.weak-tag {
    display: inline-block;
    background: #2d1a1a;
    border: 1px solid #7f1d1d;
    color: #f87171;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.75rem;
    margin: 3px 2px;
}

/* ── Latency caption ── */
.meta-row {
    display: flex;
    gap: 14px;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #1e2535;
}
.meta-pill {
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.73rem;
    color: #6b7a99;
}

/* ── Divider ── */
hr {
    border-color: #1e2535 !important;
}

/* ── Selectbox ── */
[data-baseweb="select"] {
    background: #161b27 !important;
    border-color: #2a3040 !important;
    border-radius: 10px !important;
}

/* ── Text input ── */
[data-baseweb="input"] {
    background: #161b27 !important;
    border-color: #2a3040 !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid      = st.session_state.uid
profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

if "chat_history"   not in st.session_state: st.session_state.chat_history   = []
if "study_subject"  not in st.session_state: st.session_state.study_subject  = subjects[0]
if "selected_topic" not in st.session_state: st.session_state.selected_topic = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="study-header">
    <h1>📖 Study with Your AI Tutor</h1>
    <p>Pick a topic from your syllabus — the AI answers only from your uploaded curriculum.</p>
</div>
""", unsafe_allow_html=True)

col_main, col_side = st.columns([3, 1])

# ── SIDEBAR: Topic list ───────────────────────────────────────────────────────
with col_side:
    st.markdown('<div class="sidebar-label">Subject</div>', unsafe_allow_html=True)
    subject = st.selectbox("", subjects, key="study_subj_sel", label_visibility="collapsed")
    if subject != st.session_state.study_subject:
        st.session_state.study_subject  = subject
        st.session_state.selected_topic = None
        st.session_state.chat_history   = []

    topics = get_topics(subject)

    if not topics:
        st.markdown('<div class="status-missing">⚠️ No topics — upload PDF first</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="sidebar-label">Search Topics</div>', unsafe_allow_html=True)
        search   = st.text_input("", placeholder="🔍 Filter topics...", label_visibility="collapsed")
        filtered = [t for t in topics if search.lower() in t.lower()] if search else topics
        st.caption(f"{len(filtered)} of {len(topics)} topics")
        st.divider()

        for t in filtered:
            is_active = (t == st.session_state.selected_topic)
            label     = f"▶ {t}" if is_active else t
            if st.button(label, key=f"t_{t}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                if st.session_state.selected_topic != t:
                    st.session_state.selected_topic = t
                    st.session_state.chat_history   = []
                st.rerun()

    # ── AEL status ────────────────────────────────────────────────────
    st.divider()
    active_topic = st.session_state.selected_topic or "general"
    m_idx  = get_ael_modality(uid, subject, active_topic)
    m_lbl  = MODALITY_LABELS.get(m_idx, "Standard Prose")
    st.markdown('<div class="sidebar-label">Explanation Style</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="ael-badge">
        <span class="ael-dot"></span>
        M={m_idx} · {m_lbl}
    </div>
    <div style="font-size:0.72rem; color:#4a5568; margin-top:6px;">Auto-adapts from quiz results</div>
    """, unsafe_allow_html=True)

    # Weak topics
    weak = get_error_topics(uid, subject)
    if weak:
        st.divider()
        st.markdown('<div class="sidebar-label">Weak Topics</div>', unsafe_allow_html=True)
        for t in weak:
            st.markdown(f'<span class="weak-tag">🔴 {t}</span>', unsafe_allow_html=True)
        st.write("")
        for t in weak:
            if st.button(f"Study: {t}", key=f"w_{t}", use_container_width=True):
                st.session_state.selected_topic = t
                st.session_state.chat_history   = []
                st.rerun()

    # Index status
    st.divider()
    if index_exists(subject):
        st.markdown('<div class="status-indexed">✅ Syllabus indexed</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-missing">⚠️ Upload syllabus first</div>', unsafe_allow_html=True)

# ── MAIN: Chat area ───────────────────────────────────────────────────────────
with col_main:
    selected_topic = st.session_state.selected_topic

    if not selected_topic:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px; color:#4a5568;">
            <div style="font-size:3rem; margin-bottom:16px;">👈</div>
            <div style="font-family:'Fraunces',serif; font-size:1.4rem; color:#6b7a99; margin-bottom:8px;">
                Select a topic to begin
            </div>
            <div style="font-size:0.85rem;">
                Choose from the topic list on the left to start a study session
            </div>
        </div>
        """, unsafe_allow_html=True)
        if not get_topics(subject):
            st.warning("No topics found. Go to **Upload Syllabus** to upload your PDF first.")
        st.stop()

    # Header row
    hcol1, hcol2, hcol3 = st.columns([4, 1, 1])
    with hcol1:
        st.markdown(f"""
        <div style="font-family:'Fraunces',serif; font-size:1.5rem; font-weight:600;
                    color:#f0f4ff; padding: 4px 0 12px 0; letter-spacing:-0.3px;">
            {selected_topic}
        </div>
        """, unsafe_allow_html=True)
    with hcol2:
        # Save to Notes button
        if st.session_state.chat_history:
            if st.button("📝 Save Note", use_container_width=True):
                if "notes" not in st.session_state:
                    st.session_state.notes = []
                last_ai = next(
                    (m["content"] for m in reversed(st.session_state.chat_history)
                     if m["role"] == "assistant"), None
                )
                if last_ai:
                    st.session_state.notes.append({
                        "subject": subject,
                        "topic": selected_topic,
                        "content": last_ai,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M")
                    })
                    st.toast("✅ Note saved! View it in the Notes page.", icon="📝")
    with hcol3:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    st.divider()

    # Suggested starter questions (shown only when chat is empty)
    if not st.session_state.chat_history:
        st.markdown('<div style="font-size:0.8rem; color:#4a5568; font-weight:500; letter-spacing:0.05em; text-transform:uppercase; margin-bottom:10px;">Quick start</div>', unsafe_allow_html=True)
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
                m = msg.get('modality', 0)
                st.markdown(f"""
                <div class="meta-row">
                    <span class="meta-pill">🔄 {MODALITY_LABELS.get(m, '')}</span>
                    <span class="meta-pill">⏱️ {msg.get('latency','?')}s</span>
                    <span class="meta-pill">📚 {msg.get('chunks',0)} chunks</span>
                </div>
                """, unsafe_allow_html=True)

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
            st.markdown(f"""
            <div class="meta-row">
                <span class="meta-pill">🔄 {MODALITY_LABELS.get(m_idx, '')}</span>
                <span class="meta-pill">⏱️ {elapsed}s</span>
                <span class="meta-pill">📚 {len(chunks)} chunks retrieved</span>
            </div>
            """, unsafe_allow_html=True)

            if not chunks:
                st.warning("⚠️ No syllabus found — upload your PDF in **Upload Syllabus**.")

        st.session_state.chat_history.append({
            "role": "assistant", "content": response,
            "modality": m_idx, "latency": elapsed, "chunks": len(chunks)
        })
