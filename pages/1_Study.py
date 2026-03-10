"""
pages/1_Study.py
Study page — auto-extracted topic list from PDF + RAG explanations with AEL.
Enhanced with Mind Map, Smart Hints, and Socratic Tutor.
"""

import streamlit as st
import time
import json
from groq import Groq
from database.db import (get_subject_summary, get_error_topics,
                          get_ael_modality, get_topics,
                          log_hint_usage, save_socratic_session, get_socratic_history)
from rag.rag_pipeline import retrieve_chunks, format_context, index_exists
from llm.llm_engine import generate_explanation, MODALITY_LABELS, MODEL_NAME

st.set_page_config(page_title="Study | LLM-ITS", page_icon="📖", layout="wide")

# ── Professional CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,300;0,600;1,300&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0f1117; color: #e8e8e8; }

.study-header {
    background: linear-gradient(135deg, #1a1f2e 0%, #12161f 100%);
    border: 1px solid #2a3040; border-radius: 16px;
    padding: 28px 36px; margin-bottom: 24px;
    position: relative; overflow: hidden;
}
.study-header::before {
    content: ''; position: absolute; top: -40px; right: -40px;
    width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(99,179,237,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.study-header h1 {
    font-family: 'Fraunces', serif; font-size: 2rem; font-weight: 600;
    color: #f0f4ff; margin: 0 0 4px 0; letter-spacing: -0.5px;
}
.study-header p { color: #7a8499; font-size: 0.9rem; margin: 0; font-weight: 300; }

.stButton > button {
    border-radius: 10px !important; font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important; font-weight: 400 !important;
    transition: all 0.18s ease !important; border: 1px solid #2a3040 !important;
    background: #161b27 !important; color: #c0c8dc !important; text-align: left !important;
}
.stButton > button:hover {
    background: #1e2535 !important; border-color: #63b3ed !important;
    color: #f0f4ff !important; transform: translateX(3px) !important;
}
button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    border-color: #3b82f6 !important; color: #fff !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    box-shadow: 0 4px 16px rgba(59,130,246,0.3) !important;
}

section[data-testid="stSidebar"] {
    background: #0d1018 !important; border-right: 1px solid #1e2535;
}
.sidebar-label {
    font-size: 0.7rem; font-weight: 500; letter-spacing: 0.12em;
    text-transform: uppercase; color: #4a5568; margin: 20px 0 8px 0;
}
.ael-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: #1a2235; border: 1px solid #2d3a52; border-radius: 20px;
    padding: 6px 14px; font-size: 0.8rem; color: #93c5fd; font-weight: 500; margin-top: 6px;
}
.ael-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #3b82f6; box-shadow: 0 0 6px rgba(59,130,246,0.6); animation: pulse 2s infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

[data-testid="stChatMessage"] {
    background: #161b27 !important; border: 1px solid #1e2a3a !important;
    border-radius: 14px !important; margin-bottom: 12px !important; padding: 16px !important;
}
[data-testid="stChatInput"] {
    background: #161b27 !important; border: 1px solid #2a3040 !important; border-radius: 14px !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}
.weak-tag {
    display: inline-block; background: #2d1a1a; border: 1px solid #7f1d1d;
    color: #f87171; border-radius: 6px; padding: 3px 10px; font-size: 0.75rem; margin: 3px 2px;
}
.meta-row { display: flex; gap: 14px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #1e2535; }
.meta-pill {
    background: #161b27; border: 1px solid #1e2535; border-radius: 6px;
    padding: 3px 10px; font-size: 0.73rem; color: #6b7a99;
}
.status-indexed { background:#0d2818; border:1px solid #166534; color:#4ade80; border-radius:8px; padding:6px 12px; font-size:0.78rem; font-weight:500; }
.status-missing  { background:#2d1a0a; border:1px solid #92400e; color:#fb923c; border-radius:8px; padding:6px 12px; font-size:0.78rem; }
hr { border-color: #1e2535 !important; }
[data-baseweb="select"] { background: #161b27 !important; border-color: #2a3040 !important; border-radius: 10px !important; }
[data-baseweb="input"]  { background: #161b27 !important; border-color: #2a3040 !important; border-radius: 10px !important; }
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

# ── Ollama helper (free, local) ───────────────────────────────────────────────
def call_llm(system_prompt, messages, max_tokens=1000):
    """Call Groq API (LLaMA3 8B) — free, fast, no local setup needed."""
    try:
        import os
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            api_key = os.environ.get("GROQ_API_KEY", "")
        client = Groq(api_key=api_key)
        # Build messages with system prompt
        groq_messages = [{"role": "system", "content": system_prompt}]
        groq_messages += [{"role": m["role"], "content": m["content"]} for m in messages]
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=groq_messages,
            temperature=0.7,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[LLM Error: {e}]"


# ── Mind Map ──────────────────────────────────────────────────────────────────
def render_mind_map(subject, topic):
    cache_key = f"mindmap_{subject}_{topic}"
    if cache_key not in st.session_state:
        with st.spinner("🗺️ Generating mind map..."):
            prompt = f"""Generate a mind map for the topic "{topic}" in {subject}.
Return ONLY a JSON object in this exact format, no other text:
{{
  "center": "{topic}",
  "branches": [
    {{"label": "Branch Name", "children": ["subtopic 1", "subtopic 2", "subtopic 3"]}}
  ]
}}
Include 4-5 branches, each with 2-4 children."""
            try:
                raw = call_llm(
                    "You are an expert educator. Return only valid JSON, no markdown.",
                    [{"role": "user", "content": prompt}],
                    max_tokens=800
                )
                clean = raw.strip().replace("```json", "").replace("```", "")
                st.session_state[cache_key] = json.loads(clean)
            except Exception:
                st.session_state[cache_key] = None

    data = st.session_state.get(cache_key)
    if not data:
        st.warning("Could not generate mind map.")
        return

    center   = data.get("center", topic)
    branches = data.get("branches", [])
    colors   = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0"]

    html = f"""
    <style>
    .mm-wrap  {{ font-family: sans-serif; padding: 10px; }}
    .mm-center {{ background:#1e1e2e; color:white; border-radius:50px; padding:12px 24px;
                  font-size:18px; font-weight:bold; display:inline-block;
                  margin-bottom:20px; border:3px solid #7c3aed; }}
    .mm-branch {{ margin: 8px 0; }}
    .mm-branch-label {{ display:inline-block; padding:6px 16px; border-radius:20px;
                        color:white; font-weight:bold; font-size:14px; margin-right:10px; }}
    .mm-children {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:6px; margin-left:20px; }}
    .mm-child {{ background:#2d2d3f; color:#e0e0e0; padding:4px 12px;
                 border-radius:12px; font-size:13px; border:1px solid #444; }}
    </style>
    <div class="mm-wrap">
        <div class="mm-center">⭐ {center}</div>
    """
    for i, branch in enumerate(branches):
        color    = colors[i % len(colors)]
        label    = branch.get("label", "")
        children = branch.get("children", [])
        kids_html = "".join(f'<span class="mm-child">• {c}</span>' for c in children)
        html += f"""
        <div class="mm-branch">
            <span class="mm-branch-label" style="background:{color};">{label}</span>
            <div class="mm-children">{kids_html}</div>
        </div>"""
    html += "</div>"
    st.components.v1.html(html, height=380, scrolling=True)


# ── Smart Hints ───────────────────────────────────────────────────────────────
def render_hints(uid, subject, topic, question_text):
    hint_level = st.session_state.get(f"hint_level_{topic}", 0)
    hint_labels = ["💛 Subtle Hint", "🟠 Moderate Hint", "🔴 Full Explanation"]
    level_instructions = [
        "Give a very subtle one-sentence hint pointing in the right direction. Do NOT reveal the answer.",
        "Give a moderate hint explaining the key concept needed. Two sentences max. Do NOT reveal the answer.",
        "Give a full conceptual explanation so the student can work out the answer themselves.",
    ]

    if hint_level < 3:
        if st.button(hint_labels[hint_level], key=f"hint_btn_{topic}_{hint_level}"):
            with st.spinner("Generating hint..."):
                hint_text = call_llm(
                    f"You are a helpful tutor for {subject}, topic: {topic}. Never directly state the answer.",
                    [{"role": "user", "content": f"Question: {question_text}\n\n{level_instructions[hint_level]}"}],
                    max_tokens=200
                )
            new_level = hint_level + 1
            st.session_state[f"hint_level_{topic}"]          = new_level
            st.session_state[f"hint_text_{topic}_{hint_level}"] = hint_text
            log_hint_usage(uid, subject, topic, new_level)
            st.rerun()

    # Show all revealed hints
    bg_colors = ["#fff3cd", "#ffe0b2", "#ffcdd2"]
    icons      = ["💛", "🟠", "🔴"]
    for l in range(hint_level):
        hint_text = st.session_state.get(f"hint_text_{topic}_{l}", "")
        if hint_text:
            st.markdown(
                f'<div style="background:{bg_colors[l]};padding:10px;border-radius:8px;'
                f'color:#333;margin:4px 0;">{icons[l]} <b>Hint {l+1}:</b> {hint_text}</div>',
                unsafe_allow_html=True
            )

    if hint_level >= 3:
        st.caption("All hint levels used for this question.")


# ── Socratic Tutor ────────────────────────────────────────────────────────────
def render_socratic_tutor(uid, subject, topic):
    st.markdown("---")
    st.subheader("🤔 Socratic Tutor")
    st.caption("I'll guide you to the answer through questions — not just give it to you.")

    session_key = f"socratic_{uid}_{subject}_{topic}"
    if session_key not in st.session_state:
        history = get_socratic_history(uid, subject, topic)
        st.session_state[session_key] = history if history else []

    messages = st.session_state[session_key]

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if not messages:
        if st.button("🚀 Start Socratic Session", key=f"start_soc_{topic}"):
            with st.spinner("Starting session..."):
                opener = call_llm(
                    f"You are a Socratic tutor for {subject}, topic: {topic}. "
                    f"Guide the student through thoughtful questions. NEVER give direct answers. "
                    f"Start by asking what they already know about {topic}.",
                    [{"role": "user", "content": f"I want to learn about {topic}"}],
                    max_tokens=200
                )
            messages.append({"role": "assistant", "content": opener})
            st.session_state[session_key] = messages
            save_socratic_session(uid, subject, topic, messages)
            st.rerun()

    if messages:
        user_input = st.chat_input("Your response...", key=f"soc_input_{topic}")
        if user_input:
            messages.append({"role": "user", "content": user_input})
            with st.spinner("Thinking..."):
                response = call_llm(
                    f"You are a Socratic tutor for {subject}, topic: {topic}. "
                    f"Never give direct answers. Keep responses to 2-3 sentences. Always end with a question.",
                    messages,
                    max_tokens=300
                )
            messages.append({"role": "assistant", "content": response})
            st.session_state[session_key] = messages
            save_socratic_session(uid, subject, topic, messages)
            st.rerun()

        if st.button("🔄 Reset Session", key=f"reset_soc_{topic}"):
            st.session_state[session_key] = []
            st.rerun()


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

    # AEL status
    st.divider()
    active_topic = st.session_state.selected_topic or "general"
    m_idx = get_ael_modality(uid, subject, active_topic)
    m_lbl = MODALITY_LABELS.get(m_idx, "Standard Prose")
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

# ── MAIN: Chat + AI features ──────────────────────────────────────────────────
with col_main:
    selected_topic = st.session_state.selected_topic

    if not selected_topic:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px; color:#4a5568;">
            <div style="font-size:3rem; margin-bottom:16px;">👈</div>
            <div style="font-family:'Fraunces',serif; font-size:1.4rem; color:#6b7a99; margin-bottom:8px;">
                Select a topic to begin
            </div>
            <div style="font-size:0.85rem;">Choose from the topic list on the left to start a study session</div>
        </div>
        """, unsafe_allow_html=True)
        if not get_topics(subject):
            st.warning("No topics found. Go to **Upload Syllabus** to upload your PDF first.")
        st.stop()

    # ── Topic header ──────────────────────────────────────────────────────────
    hcol1, hcol2, hcol3 = st.columns([4, 1, 1])
    with hcol1:
        st.markdown(f"""
        <div style="font-family:'Fraunces',serif; font-size:1.5rem; font-weight:600;
                    color:#f0f4ff; padding: 4px 0 12px 0; letter-spacing:-0.3px;">
            {selected_topic}
        </div>
        """, unsafe_allow_html=True)
    with hcol2:
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
                        "subject": subject, "topic": selected_topic,
                        "content": last_ai, "timestamp": time.strftime("%Y-%m-%d %H:%M")
                    })
                    st.toast("✅ Note saved! View it in the Notes page.", icon="📝")
    with hcol3:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    st.divider()

    # ── 🗺️ Mind Map (shown once per topic) ───────────────────────────────────
    with st.expander("🗺️ View Mind Map for this Topic", expanded=False):
        render_mind_map(subject, selected_topic)

    st.divider()

    # ── Suggested starter questions ───────────────────────────────────────────
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

    # ── Chat history ──────────────────────────────────────────────────────────
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                m = msg.get("modality", 0)
                st.markdown(f"""
                <div class="meta-row">
                    <span class="meta-pill">🔄 {MODALITY_LABELS.get(m, '')}</span>
                    <span class="meta-pill">⏱️ {msg.get('latency','?')}s</span>
                    <span class="meta-pill">📚 {msg.get('chunks',0)} chunks</span>
                </div>
                """, unsafe_allow_html=True)

    # ── Chat input ────────────────────────────────────────────────────────────
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

                chunks  = retrieve_chunks(subject, q, weak_topics=weak_topics, mastery_level=mastery)
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
                response = generate_explanation(q, context, llm_profile, m_idx, history_turns)
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

            # ── 💡 Smart Hints (shown after each AI response) ─────────────────
            st.divider()
            st.markdown("**💡 Need a hint on your question?**")
            render_hints(uid, subject, selected_topic, q)

        st.session_state.chat_history.append({
            "role": "assistant", "content": response,
            "modality": m_idx, "latency": elapsed, "chunks": len(chunks)
        })

    # ── 🤔 Socratic Tutor (at the bottom) ────────────────────────────────────
    render_socratic_tutor(uid, subject, selected_topic)
