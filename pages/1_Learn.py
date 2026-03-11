"""
pages/1_Learn.py
─────────────────────────────────────────────────────────────────────────────
Unified Learning Hub — Study, Quiz, and Roadmap in one page with tabs.
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import time
import json
import re
from datetime import datetime, date, timedelta
from groq import Groq
from components.sidebar import render_sidebar
render_sidebar()

from database.db import (get_subject_summary, get_error_topics,
                          get_ael_modality, get_topics,
                          log_hint_usage, save_socratic_session, get_socratic_sessions,
                          log_quiz_attempt, update_ael, log_error_topic,
                          get_recent_accuracy, add_xp, get_level_title,
                          save_learning_plan, get_latest_plan, get_latest_plan_id,
                          save_plan_days, get_plan_days,
                          update_day_status, get_profile)
from rag.rag_pipeline import retrieve_chunks, format_context, index_exists
from llm.llm_engine import (generate_explanation, generate_quiz_question,
                              generate_learning_plan, MODALITY_LABELS, MODEL_NAME)
from emotion.emotion_engine import get_emotion_prompt_modifier
from emotion.emotion_widget import (
    get_tracker, reset_tracker,
    render_emotion_sidebar, render_reroute_banner, render_emotion_chip
)
from kg.kg_engine import build_kg_context, validate_topics_against_kg
from kg.kg_widget import (
    render_kg_status, render_prereq_chain,
    render_kg_context_card, render_hallucination_score, get_or_build_kg
)
from xai.xai_engine import build_xai_explanation, explain_counterfactual, get_xai_system_note
from xai.xai_widget import (
    render_xai_panel, render_xai_strip,
    render_counterfactual, render_xai_sidebar
)

st.set_page_config(page_title="Learn | LLM-ITS", page_icon="🎓", layout="wide")

# ── Auth ──────────────────────────────────────────────────────────────────────
if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

# ── Shared CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=Instrument+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Instrument Sans', sans-serif; }
.stApp { background: #080c14; color: #d4dbe8; }

/* Tab styling */
[data-baseweb="tab-list"] {
    background: #0d1524 !important;
    border-radius: 14px !important;
    padding: 6px !important;
    gap: 4px !important;
    border: 1px solid #1a2540 !important;
    margin-bottom: 24px !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 10px !important;
    color: #4a6080 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    padding: 10px 24px !important;
    border: none !important;
    transition: all 0.18s !important;
}
[data-baseweb="tab"]:hover { color: #d4dbe8 !important; background: #1a2540 !important; }
[aria-selected="true"][data-baseweb="tab"] {
    background: linear-gradient(135deg,#2563eb,#1d4ed8) !important;
    color: #fff !important;
    box-shadow: 0 4px 16px rgba(37,99,235,0.35) !important;
}
[data-baseweb="tab-highlight"] { display: none !important; }
[data-baseweb="tab-border"] { display: none !important; }

/* Common components */
.hud-header {
    background: linear-gradient(160deg, #0d1524 0%, #080c14 60%);
    border: 1px solid #1a2540; border-radius: 20px;
    padding: 28px 36px; margin-bottom: 28px;
    position: relative; overflow: hidden;
}
.hud-header::after {
    position: absolute; right: 32px; top: 50%;
    transform: translateY(-50%); font-family: 'Syne', sans-serif;
    font-size: 5rem; font-weight: 800; color: rgba(255,255,255,0.022);
    letter-spacing: 0.15em; pointer-events: none; user-select: none;
}
.hud-title { font-family:'Syne',sans-serif; font-size:2rem; font-weight:800; color:#f0f6ff; margin:0 0 4px 0; }
.hud-sub   { color:#4a6080; font-size:0.88rem; margin:0; font-weight:300; }

.stButton > button {
    border-radius:10px !important; font-family:'Instrument Sans',sans-serif !important;
    font-size:0.84rem !important; font-weight:500 !important;
    transition:all 0.2s !important; border:1px solid #1a2540 !important;
    background:#0d1524 !important; color:#8090a8 !important;
}
.stButton > button:hover { background:#1a2540 !important; border-color:#3b82f6 !important; color:#d4dbe8 !important; transform:translateY(-2px) !important; }
button[kind="primary"] {
    background:linear-gradient(135deg,#2563eb,#1d4ed8) !important;
    border-color:#3b82f6 !important; color:#fff !important; font-weight:600 !important;
}
button[kind="primary"]:hover {
    background:linear-gradient(135deg,#3b82f6,#2563eb) !important;
    box-shadow:0 4px 20px rgba(37,99,235,0.35) !important;
}
section[data-testid="stSidebar"] { background:#080c14 !important; border-right:1px solid #1a2540; }
.ael-badge { display:inline-flex;align-items:center;gap:8px;background:#0d1524;border:1px solid #1a2540;border-radius:20px;padding:6px 14px;font-size:0.8rem;color:#3b82f6;font-weight:500;margin-top:6px; }
.ael-dot { width:8px;height:8px;border-radius:50%;background:#3b82f6;box-shadow:0 0 6px rgba(59,130,246,0.6);animation:pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.4} }
.weak-tag { display:inline-block;background:#2d1a1a;border:1px solid #7f1d1d;color:#f87171;border-radius:6px;padding:3px 10px;font-size:0.75rem;margin:3px 2px; }
.meta-row { display:flex;gap:14px;margin-top:8px;padding-top:8px;border-top:1px solid #1a2540; }
.meta-pill { background:#0d1524;border:1px solid #1a2540;border-radius:6px;padding:3px 10px;font-size:0.73rem;color:#4a6080; }
.status-indexed { background:#064e2e;border:1px solid #10b981;color:#34d399;border-radius:8px;padding:6px 12px;font-size:0.78rem;font-weight:500; }
.status-missing  { background:#1c1005;border:1px solid #92400e;color:#fbbf24;border-radius:8px;padding:6px 12px;font-size:0.78rem; }
.sidebar-label { font-size:0.7rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#4a6080;margin:20px 0 8px 0; }
.q-card { background:#0d1524;border:1px solid #1a2540;border-radius:16px;padding:24px 28px;margin-bottom:20px; }
.q-meta { display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap; }
.q-badge { font-size:0.68rem;border-radius:8px;padding:3px 10px;font-weight:600;border:1px solid; }
.badge-subject { background:#0d1a2e;color:#60a5fa;border-color:#1d4ed8; }
.badge-topic   { background:#0f1a10;color:#4ade80;border-color:#166534; }
.badge-mastery { background:#1c1005;color:#fbbf24;border-color:#92400e; }
.badge-mode    { background:#1a0d2e;color:#c084fc;border-color:#7c3aed; }
.q-text { font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:600;color:#f0f6ff;line-height:1.5; }
.result-correct { background:#081810;border:1px solid #065f35;border-radius:12px;padding:16px 20px;margin:12px 0; }
.result-wrong   { background:#180808;border:1px solid #7f1d1d;border-radius:12px;padding:16px 20px;margin:12px 0; }
.result-partial { background:#141005;border:1px solid #78350f;border-radius:12px;padding:16px 20px;margin:12px 0; }
.result-title { font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:8px; }
.result-correct .result-title { color:#34d399; }
.result-wrong   .result-title { color:#f87171; }
.result-partial .result-title { color:#fbbf24; }
.result-body { font-size:0.84rem;color:#8090a8;line-height:1.7; }
.xp-popup { background:linear-gradient(135deg,#1d4ed8,#7c3aed);border-radius:12px;padding:12px 20px;margin:12px 0;font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;color:#fff;text-align:center;box-shadow:0 4px 20px rgba(124,58,237,0.3); }
.stat-card { background:#0d1524;border:1px solid #1a2540;border-radius:12px;padding:14px 16px;margin-bottom:10px; }
.stat-val   { font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;color:#f0f6ff; }
.stat-label { font-size:0.68rem;color:#3a5070;text-transform:uppercase;letter-spacing:0.1em; }
.section-label { font-size:0.68rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#2a4060;margin:16px 0 8px 0; }
.code-wrap { background:#0a0e18;border:1px solid #1a2540;border-radius:12px;padding:4px;margin:16px 0; }
textarea { background:#0a0e18 !important;border-color:#1a2540 !important;border-radius:10px !important;font-family:'JetBrains Mono',monospace !important;font-size:0.85rem !important;color:#e2e8f0 !important; }
[data-baseweb="select"] { background:#0d1524 !important;border-color:#1a2540 !important;border-radius:10px !important; }
[data-baseweb="input"]  { background:#0d1524 !important;border-color:#1a2540 !important;border-radius:10px !important; }
hr { border-color:#1a2540 !important; }
[data-testid="stChatMessage"] { background:#0d1524 !important;border:1px solid #1a2540 !important;border-radius:14px !important;margin-bottom:12px !important;padding:16px !important; }
[data-testid="stChatInput"] { background:#0d1524 !important;border:1px solid #1a2540 !important;border-radius:14px !important; }
[data-testid="stChatInput"]:focus-within { border-color:#3b82f6 !important;box-shadow:0 0 0 3px rgba(59,130,246,0.1) !important; }

/* Roadmap styles */
.progress-hud { display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px; }
.hud-cell { background:#0d1524;border:1px solid #1a2540;border-radius:14px;padding:18px 20px;position:relative;overflow:hidden; }
.hud-cell::before { content:'';position:absolute;bottom:0;left:0;right:0;height:2px; }
.hud-cell.completed::before { background:linear-gradient(90deg,#10b981,#059669); }
.hud-cell.pending::before   { background:linear-gradient(90deg,#3b82f6,#1d4ed8); }
.hud-cell.total::before     { background:linear-gradient(90deg,#8b5cf6,#6d28d9); }
.hud-cell.xp::before        { background:linear-gradient(90deg,#f59e0b,#d97706); }
.hud-num { font-family:'Syne',sans-serif;font-size:2.4rem;font-weight:800;line-height:1;margin-bottom:4px; }
.hud-cell.completed .hud-num { color:#10b981; }
.hud-cell.pending   .hud-num { color:#3b82f6; }
.hud-cell.total     .hud-num { color:#8b5cf6; }
.hud-cell.xp        .hud-num { color:#f59e0b; }
.hud-label { font-size:0.7rem;color:#3a5070;text-transform:uppercase;letter-spacing:0.1em;font-weight:500; }
.progress-track-bar { height:6px;background:#0d1524;border-radius:10px;overflow:hidden;margin:8px 0 6px 0;border:1px solid #1a2540; }
.progress-track-fill { height:100%;border-radius:10px;background:linear-gradient(90deg,#10b981,#3b82f6,#8b5cf6);transition:width 0.6s ease; }
.progress-caption { display:flex;justify-content:space-between;font-size:0.72rem;color:#3a5070; }
.road-node-row { display:flex;align-items:center;margin-bottom:0;position:relative; }
.node-label-card { background:#0d1524;border:1px solid #1a2540;border-radius:12px;padding:10px 14px;max-width:200px;margin:0 14px;transition:all 0.2s; }
.node-label-card.done   { border-color:#064e2e;background:#081810; }
.node-label-card.active { border-color:#2563eb;background:#0d1a2e;box-shadow:0 0 0 1px rgba(59,130,246,0.2); }
.node-label-card.locked { opacity:0.4; }
.nlc-day   { font-size:0.62rem;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;margin-bottom:3px; }
.nlc-day.done   { color:#10b981; }
.nlc-day.active { color:#60a5fa; }
.nlc-day.locked { color:#2a4060; }
.nlc-day.skipped{ color:#f59e0b; }
.nlc-title { font-family:'Syne',sans-serif;font-size:0.82rem;font-weight:600;color:#d4dbe8; }
.nlc-title.done   { color:#6b7a80;text-decoration:line-through; }
.nlc-title.locked { color:#2a4060; }
.nlc-badge { display:inline-block;font-size:0.62rem;border-radius:20px;padding:2px 8px;margin-top:4px;font-weight:500; }
.badge-done    { background:#064e2e;color:#34d399;border:1px solid #059669; }
.badge-active  { background:#1d4ed8;color:#fff;border:1px solid #3b82f6; }
.badge-locked  { background:#0d1120;color:#2a4060;border:1px solid #1a2540; }
.badge-skipped { background:#1c1005;color:#fbbf24;border:1px solid #92400e; }
.badge-pending { background:#0d1a2e;color:#60a5fa;border:1px solid #1d4ed8; }
.milestone-flag { background:linear-gradient(135deg,#7c3aed,#4f46e5);border:1px solid #6d28d9;border-radius:12px;padding:8px 16px;margin:8px auto;text-align:center;font-family:'Syne',sans-serif;font-size:0.75rem;font-weight:700;color:#e9d5ff;letter-spacing:0.05em;max-width:200px;box-shadow:0 0 16px rgba(109,40,217,0.3); }
.detail-panel { background:#0d1524;border:1px solid #2563eb;border-radius:16px;padding:20px 24px;margin:16px 0;box-shadow:0 0 0 1px rgba(59,130,246,0.15),0 8px 32px rgba(0,0,0,0.4); }
.dp-header { font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#f0f6ff;margin-bottom:10px; }
.dp-content { font-size:0.84rem;color:#8090a8;line-height:1.75; }
.dp-subject-tag { display:inline-block;background:#1d4ed8;color:#bfdbfe;border-radius:8px;padding:3px 10px;font-size:0.7rem;font-weight:600;margin-bottom:10px;border:1px solid #2563eb; }
.mastery-row { display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px; }
.mastery-chip { border-radius:12px;padding:12px 18px;display:flex;flex-direction:column;gap:2px;flex:1;min-width:120px;border:1px solid; }
.mastery-chip.strong   { background:#081810;border-color:#064e2e; }
.mastery-chip.moderate { background:#141005;border-color:#78350f; }
.mastery-chip.weak     { background:#180808;border-color:#7f1d1d; }
.mastery-chip .subj { font-family:'Syne',sans-serif;font-size:0.8rem;font-weight:600; }
.mastery-chip.strong   .subj { color:#34d399; }
.mastery-chip.moderate .subj { color:#fbbf24; }
.mastery-chip.weak     .subj { color:#f87171; }
.mastery-chip .pct { font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;color:#d4dbe8; }
.mastery-chip .wk  { font-size:0.68rem;color:#4a6080; }
.meta-grid { display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px; }
.meta-cell { background:#0d1524;border:1px solid #1a2540;border-radius:12px;padding:14px 16px; }
.meta-cell .val { font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;color:#f0f6ff; }
.meta-cell .lbl { font-size:0.68rem;color:#3a5070;text-transform:uppercase;letter-spacing:0.1em; }
.dynamic-alert { background:#0f1a0f;border:1px solid #166534;border-radius:12px;padding:12px 18px;margin-bottom:20px;font-size:0.82rem;color:#4ade80;display:flex;align-items:center;gap:10px; }
.dynamic-alert.warn { background:#1c1005;border-color:#92400e;color:#fbbf24; }
.roadmap-container { position:relative;padding:20px 0 40px 0; }
</style>
""", unsafe_allow_html=True)



# ── Tab navigation ────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📖  Study",
    "🧠  Quiz",  
    "🗺️  Roadmap",
])

# ══ TAB 1: STUDY ══════════════════════════════════════════════════════════════
with tab1:
    def _run_study():
        uid      = st.session_state.uid
        profile  = st.session_state.profile
        subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

        if "chat_history"   not in st.session_state: st.session_state.chat_history   = []
        if "study_subject"  not in st.session_state: st.session_state.study_subject  = subjects[0]
        if "selected_topic" not in st.session_state: st.session_state.selected_topic = None

        # ── Emotion tracker (one per study session) ───────────────────────────────────
        study_tracker = get_tracker("study_emotion_tracker")

        # ── Ollama helper (free, local) ───────────────────────────────────────────────
        def _get_groq_client():
            """Get a Groq client for KG building."""
            try:
                import os
                try:
                    api_key = st.secrets["GROQ_API_KEY"]
                except Exception:
                    try:
                        api_key = st.secrets["supabase"]["GROQ_API_KEY"]
                    except Exception:
                        api_key = os.environ.get("GROQ_API_KEY", "")
                from groq import Groq
                return Groq(api_key=api_key)
            except Exception:
                return None


        def call_llm(system_prompt, messages, max_tokens=1000):
            """Call Groq API (LLaMA3 8B) — free, fast, no local setup needed."""
            try:
                import os
                try:
                    # First try direct access
                    api_key = st.secrets["GROQ_API_KEY"]
                except Exception:
                    try:
                        # Then try inside the [supabase] block if the user put it there
                        api_key = st.secrets["supabase"]["GROQ_API_KEY"]
                    except Exception:
                        # Fallback to environment variable
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
                history = get_socratic_sessions(uid, subject, topic)
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
                reset_tracker("study_emotion_tracker")
                study_tracker = get_tracker("study_emotion_tracker")

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

            # ── Emotion Monitor ───────────────────────────────────────────────────────
            st.divider()
            render_emotion_sidebar(study_tracker)

            # ── Knowledge Graph Status ────────────────────────────────────────────────
            st.divider()
            kg = get_or_build_kg(subject, get_topics(subject), _get_groq_client()) if get_topics(subject) else None
            render_kg_status(kg, subject)

        # ── MAIN: Chat + AI features ──────────────────────────────────────────────────
        with col_main:
            selected_topic = st.session_state.selected_topic

            if not selected_topic:
                st.markdown("""
                <div style="text-align:center; padding:60px 20px; color:#4a6080;">
                    <div style="font-size:3rem; margin-bottom:16px;">👈</div>
                    <div style="font-family:'Syne',sans-serif; font-size:1.4rem; color:#6b7a99; margin-bottom:8px;">
                        Select a topic to begin
                    </div>
                    <div style="font-size:0.85rem;">Choose from the topic list on the left to start a study session</div>
                </div>
                """, unsafe_allow_html=True)
                if not get_topics(subject):
                    st.warning("No topics found. Go to **Upload Syllabus** to upload your PDF first.")
                return

            # ── Topic header ──────────────────────────────────────────────────────────
            hcol1, hcol2, hcol3 = st.columns([4, 1, 1])
            with hcol1:
                st.markdown(f"""
                <div style="font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:800;
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

                # ── XAI: detect "why not X?" counterfactual queries ──────────────────
                import re as _re
                _cf_pattern = r"why (?:not|skip|avoid)\s+([A-Za-z ]{3,40})"
                _cf_match = _re.search(_cf_pattern, q, _re.IGNORECASE)
                if _cf_match and _kg:
                    _rejected = _cf_match.group(1).strip()
                    _cf = explain_counterfactual(_rejected, selected_topic, _kg, _mastered if '_mastered' in dir() else [])
                    with st.chat_message("assistant"):
                        render_counterfactual(_cf)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"**Why not '{_rejected}'?** {_cf.reason}",
                        "modality": 0, "latency": 0, "chunks": 0
                    })
                    return

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

                        # ── KG: build context for this topic ──────────────────────────
                        _kg = get_or_build_kg(subject, get_topics(subject), _get_groq_client()) if get_topics(subject) else None
                        _mastered = [t for t in get_topics(subject)
                                     if next((s["avg_accuracy"] for s in summaries
                                              if s["subject"] == subject), 0) >= 75]
                        kg_context = build_kg_context(_kg, selected_topic, _mastered) if _kg else ""

                        # ── Emotion: record text signal NOW (before LLM) ─────────────
                        study_tracker.record(text=q)

                        emotion_modifier = ""
                        # Evaluate every 3 messages (text + pattern signals only at this point)
                        if study_tracker.should_evaluate():
                            _pre_result = study_tracker.evaluate(topic=selected_topic)
                            emotion_modifier = get_emotion_prompt_modifier(_pre_result)
                            st.session_state["_emotion_result"] = _pre_result
                            if _pre_result.should_reroute:
                                st.session_state["_show_reroute_banner"] = True
                                st.session_state["_banner_result"] = _pre_result

                        # ── XAI: build explanation from all 3 sources ─────────────────
                        _accuracy = next((s["avg_accuracy"] for s in summaries
                                           if s["subject"] == subject), 60.0)
                        _emotion_state  = study_tracker.last_state
                        _emotion_action = st.session_state.get("_last_emotion_action", "none")
                        xai_explanation = build_xai_explanation(
                            topic          = selected_topic,
                            subject        = subject,
                            query          = q,
                            kg             = _kg,
                            mastered_topics= _mastered,
                            mastery_level  = mastery,
                            accuracy       = _accuracy,
                            modality_idx   = m_idx,
                            emotion_state  = _emotion_state,
                            emotion_action = _emotion_action,
                        )
                        st.session_state["_last_xai"] = xai_explanation

                        # ── LLM call (KG + XAI context prepended) ────────────────────
                        xai_note        = get_xai_system_note(xai_explanation)
                        enriched_context = (xai_note + "\n\n" + kg_context + "\n\n" + context) if kg_context else (xai_note + "\n\n" + context)

                        t0       = time.time()
                        response = generate_explanation(
                            q, enriched_context, llm_profile, m_idx, history_turns,
                            emotion_modifier=emotion_modifier
                        )
                        elapsed  = round(time.time() - t0, 2)

                        # ── Emotion: now update tracker with real latency ─────────────
                        study_tracker.latencies.append(elapsed)
                        emotion_result = st.session_state.pop("_emotion_result", None)

                    # ── Show re-routing banner only when freshly triggered ───────────
                    _show_banner = st.session_state.pop("_show_reroute_banner", False)
                    _banner_result = st.session_state.pop("_banner_result", None)
                    if _show_banner and _banner_result:
                        render_reroute_banner(_banner_result)

                    # ── KG Insight card above response ────────────────────────────────
                    if _kg:
                        render_kg_context_card(_kg, selected_topic, _mastered)

                    st.markdown(response)

                    # ── Meta row: AEL + timing + chunks + emotion chip ────────────────
                    current_emotion = study_tracker.last_state
                    st.markdown(f"""
                    <div class="meta-row">
                        <span class="meta-pill">🔄 {MODALITY_LABELS.get(m_idx, '')}</span>
                        <span class="meta-pill">⏱️ {elapsed}s</span>
                        <span class="meta-pill">📚 {len(chunks)} chunks</span>
                    </div>
                    """, unsafe_allow_html=True)
                    render_emotion_chip(current_emotion)

                    # ── KG hallucination guard badge ──────────────────────────────────
                    if _kg:
                        validation = validate_topics_against_kg(_kg, response)
                        render_hallucination_score(validation)

                    # ── XAI: strip + full panel ───────────────────────────────────────
                    _xai = st.session_state.get("_last_xai")
                    if _xai:
                        render_xai_strip(_xai)
                        render_xai_panel(_xai)

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

    _run_study()

# ══ TAB 2: QUIZ ═══════════════════════════════════════════════════════════════
with tab2:
    def _run_quiz():
        uid      = st.session_state.uid
        profile  = st.session_state.profile
        subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")
        CODING_KEYWORDS = [
            "dsa", "data structure", "algorithm", "python", "java", "c++", "c#",
            "javascript", "programming", "coding", "software", "computer science",
            "cs", "code", "development", "oop", "database", "sql", "web"
        ]

        def is_coding_subject(subject_name):
            return any(kw in subject_name.lower() for kw in CODING_KEYWORDS)

        # ── LLM helpers ───────────────────────────────────────────────────────────────
        def call_llm(prompt, max_tokens=600):
            try:
                import os
                try:
                    # First try direct access
                    api_key = st.secrets["GROQ_API_KEY"]
                except Exception:
                    try:
                        # Then try inside the [supabase] block if the user put it there
                        api_key = st.secrets["supabase"]["GROQ_API_KEY"]
                    except Exception:
                        # Fallback to environment variable
                        api_key = os.environ.get("GROQ_API_KEY", "")

                client   = Groq(api_key=api_key)
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"[Error: {e}]"


        def generate_coding_question(subject, topic, mastery):
            """Generate a coding challenge with starter code."""
            difficulty_map = {
                "Strong":   "hard — requires optimization, edge cases, or complex logic",
                "Moderate": "medium — standard implementation with a small twist",
                "Weak":     "easy — basic implementation, well-defined problem"
            }
            diff = difficulty_map.get(mastery, "medium")

            prompt = f"""Generate a coding problem about "{topic}" in {subject}.
        Difficulty: {diff}

        Return ONLY valid JSON, no markdown, no explanation:
        {{
          "question": "Clear problem statement here",
          "starter_code": "def solution():\\n    # Write your code here\\n    pass",
          "expected_output": "Brief description of what correct output looks like",
          "hint": "One helpful hint without giving away the answer",
          "sample_input": "Example input if applicable",
          "sample_output": "Example output if applicable"
        }}"""
            raw = call_llm(prompt, max_tokens=500)
            try:
                clean = re.search(r'\{.*\}', raw, re.DOTALL)
                if clean:
                    return __import__('json').loads(clean.group())
            except:
                pass
            return None


        def generate_short_answer_question(subject, topic, mastery):
            """Generate a short answer question for theory subjects."""
            difficulty_map = {
                "Strong":   "challenging — requires analysis, comparison, or evaluation",
                "Moderate": "intermediate — requires explanation with examples",
                "Weak":     "basic — requires simple definition or description"
            }
            diff = difficulty_map.get(mastery, "intermediate")

            prompt = f"""Generate a short answer question about "{topic}" in {subject}.
        Difficulty: {diff}

        Return ONLY valid JSON, no markdown:
        {{
          "question": "The question here (should require 2-4 sentences to answer)",
          "key_points": ["key point 1", "key point 2", "key point 3"],
          "model_answer": "A complete model answer in 3-4 sentences",
          "hint": "A subtle hint to guide the student"
        }}"""
            raw = call_llm(prompt, max_tokens=400)
            try:
                clean = re.search(r'\{.*\}', raw, re.DOTALL)
                if clean:
                    return __import__('json').loads(clean.group())
            except:
                pass
            return None


        def grade_code_answer(question, starter_code, student_code, expected_output, topic):
            """Use LLM to grade student's code submission."""
            prompt = f"""You are a coding instructor grading a student's solution.

        Problem: {question}
        Expected: {expected_output}

        Student's code:
        ```
        {student_code}
        ```

        Grade the solution and return ONLY valid JSON:
        {{
          "score": 0,
          "max_score": 10,
          "verdict": "Correct" or "Partial" or "Incorrect",
          "feedback": "Specific feedback on their approach, what's right and what's wrong",
          "correct_solution": "A clean correct solution in code",
          "time_complexity": "O(?)",
          "improvements": "Suggestions for improvement"
        }}

        Be fair but strict. Score 0-10 where 10 is perfect."""
            raw = call_llm(prompt, max_tokens=600)
            try:
                clean = re.search(r'\{.*\}', raw, re.DOTALL)
                if clean:
                    return __import__('json').loads(clean.group())
            except:
                pass
            return {"score": 0, "max_score": 10, "verdict": "Error", "feedback": "Could not grade. Try again.", "correct_solution": "", "time_complexity": "N/A", "improvements": ""}


        def grade_short_answer(question, key_points, model_answer, student_answer, topic):
            """Use LLM to grade a short answer response."""
            prompt = f"""You are grading a student's short answer response.

        Question: {question}
        Key points expected: {', '.join(key_points)}
        Model answer: {model_answer}

        Student's answer: {student_answer}

        Grade fairly and return ONLY valid JSON:
        {{
          "score": 0,
          "max_score": 10,
          "verdict": "Excellent" or "Good" or "Partial" or "Needs Improvement",
          "feedback": "Specific feedback mentioning what they got right and what they missed",
          "missed_points": ["point they missed 1", "point they missed 2"],
          "model_answer": "{model_answer}"
        }}"""
            raw = call_llm(prompt, max_tokens=500)
            try:
                clean = re.search(r'\{.*\}', raw, re.DOTALL)
                if clean:
                    return __import__('json').loads(clean.group())
            except:
                pass
            return {"score": 0, "max_score": 10, "verdict": "Error", "feedback": "Could not grade.", "missed_points": [], "model_answer": model_answer}


        # ── Session state ─────────────────────────────────────────────────────────────
        for key, default in [
            ("quiz_question",     None),
            ("quiz_answered",     False),
            ("quiz_score",        0),
            ("quiz_total",        0),
            ("quiz_start_time",   None),
            ("prev_questions",    []),
            ("quiz_subject",      subjects[0]),
            ("quiz_topic",        ""),
            ("session_results",   []),
            ("quiz_mode",         "mcq"),
            ("code_question",     None),
            ("short_q",           None),
            ("grading_result",    None),
            ("student_code",      ""),
            ("student_answer",    ""),
        ]:
            if key not in st.session_state:
                st.session_state[key] = default

        # ── Header ────────────────────────────────────────────────────────────────────
        st.markdown("""
        <div class="quiz-header">
            <div class="quiz-title">🧠 Quiz Mode</div>
            <div class="quiz-sub">AI-generated questions adapted to your mastery — MCQ, Code, or Short Answer.</div>
        </div>
        """, unsafe_allow_html=True)

        col_main, col_side = st.columns([3, 1])

        # ══ SIDEBAR ═══════════════════════════════════════════════════════════════════
        with col_side:
            st.markdown('<div class="section-label">Settings</div>', unsafe_allow_html=True)
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

            coding = is_coding_subject(subject)
            st.markdown(f"**Type:** {'💻 Coding' if coding else '📖 Theory'} subject")

            active_topic = topic if topic else "general"
            modality_idx = get_ael_modality(uid, subject, active_topic)
            st.markdown(f"**AEL:** M={modality_idx} — {MODALITY_LABELS.get(modality_idx,'')}")

            st.divider()
            st.markdown('<div class="section-label">Session Score</div>', unsafe_allow_html=True)
            total = st.session_state.quiz_total
            score = st.session_state.quiz_score
            if total > 0:
                pct = round((score / total) * 100, 1)
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-val">{pct}%</div>
                    <div class="stat-label">Accuracy — {score}/{total} correct</div>
                </div>
                """, unsafe_allow_html=True)
                st.progress(pct / 100)
            else:
                st.caption("No attempts yet.")

            if st.button("🔄 New Session", use_container_width=True):
                for k in ["quiz_score","quiz_total","prev_questions","session_results",
                          "quiz_question","code_question","short_q","grading_result",
                          "quiz_answered","student_code","student_answer"]:
                    st.session_state[k] = [] if "results" in k or "questions" in k or "code" in k or "answer" in k else None if k not in ["quiz_score","quiz_total"] else 0
                st.rerun()

        # ══ MAIN ══════════════════════════════════════════════════════════════════════
        with col_main:

            if not topic:
                st.info("👆 Enter a topic in the sidebar and choose a quiz mode to begin.")
                return

            coding = is_coding_subject(subject)

            # ── Mode selector ─────────────────────────────────────────────────────────
            if coding:
                modes = [
                    ("mcq",  "🎯", "MCQ",         "Multiple choice questions"),
                    ("code", "💻", "Code Editor", "Write actual code to solve problems"),
                ]
            else:
                modes = [
                    ("mcq",   "🎯", "MCQ",          "Multiple choice questions"),
                    ("short", "✍️", "Short Answer", "AI-graded written responses"),
                ]

            current_mode = st.session_state.quiz_mode

            # Render mode tabs using columns
            mode_cols = st.columns(len(modes))
            for col, (mode_key, icon, label, desc) in zip(mode_cols, modes):
                with col:
                    active_style = "border:2px solid #2563eb; background:#0d1a2e;" if current_mode == mode_key else "border:1px solid #1a2540; background:#0d1524;"
                    st.markdown(
                        f'<div style="{active_style} border-radius:14px; padding:14px; text-align:center; cursor:pointer;">'
                        f'<div style="font-size:1.4rem">{icon}</div>'
                        f'<div style="font-family:Syne,sans-serif; font-size:0.8rem; font-weight:700; color:{"#60a5fa" if current_mode==mode_key else "#d4dbe8"};">{label}</div>'
                        f'<div style="font-size:0.68rem; color:#4a6080;">{desc}</div></div>',
                        unsafe_allow_html=True
                    )
                    if st.button(f"Select {label}", key=f"mode_{mode_key}", use_container_width=True):
                        st.session_state.quiz_mode     = mode_key
                        st.session_state.quiz_question = None
                        st.session_state.code_question = None
                        st.session_state.short_q       = None
                        st.session_state.quiz_answered = False
                        st.session_state.grading_result= None
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════════════════════════
            # MODE 1: MCQ (existing, unchanged logic)
            # ══════════════════════════════════════════════════════════════════════════
            if st.session_state.quiz_mode == "mcq":

                if st.button("🎯 Generate MCQ Question", type="primary", use_container_width=True):
                    with st.spinner("Generating question..."):
                        q = generate_quiz_question(subject, topic, mastery, st.session_state.prev_questions)
                    if q:
                        st.session_state.quiz_question   = q
                        st.session_state.quiz_answered   = False
                        st.session_state.quiz_start_time = time.time()
                        st.session_state.grading_result  = None
                    else:
                        st.error("Could not generate question. Try again.")

                q = st.session_state.quiz_question
                if q:
                    st.markdown(
                        f'<div class="q-card">'
                        f'<div class="q-meta">'
                        f'<span class="q-badge badge-subject">{subject}</span>'
                        f'<span class="q-badge badge-topic">{topic}</span>'
                        f'<span class="q-badge badge-mastery">{mastery}</span>'
                        f'<span class="q-badge badge-mode">🎯 MCQ</span>'
                        f'</div>'
                        f'<div class="q-text">{q["question"]}</div></div>',
                        unsafe_allow_html=True
                    )

                    if not st.session_state.quiz_answered:
                        choice = st.radio("Select your answer:", q["options"], index=None,
                                          key=f"radio_{st.session_state.quiz_total}")
                        if st.button("✅ Submit Answer", type="primary",
                                     disabled=(choice is None), use_container_width=True):
                            elapsed      = round(time.time() - (st.session_state.quiz_start_time or time.time()), 2)
                            selected_idx = q["options"].index(choice)
                            correct_idx  = q["correct_index"]
                            is_correct   = (selected_idx == correct_idx)

                            st.session_state.quiz_answered = True
                            st.session_state.quiz_total   += 1
                            if is_correct:
                                st.session_state.quiz_score += 1

                            accuracy = log_quiz_attempt(uid, subject, topic, 1 if is_correct else 0, 1, elapsed, modality_idx)
                            if not is_correct:
                                log_error_topic(uid, subject, topic)
                            recent_acc = get_recent_accuracy(uid, subject, topic, n=2)
                            new_m      = update_ael(uid, subject, topic, recent_acc)

                            # XP
                            xp_gained, _, new_level, leveled_up = add_xp(uid, accuracy)
                            st.session_state.session_results.append({
                                "topic": topic, "correct": is_correct,
                                "latency": elapsed, "modality": modality_idx,
                                "new_m": new_m, "xp": xp_gained, "mode": "MCQ"
                            })
                            st.session_state.prev_questions.append(q["question"])
                            st.session_state["_last_xp"]      = xp_gained
                            st.session_state["_last_leveled"]  = leveled_up
                            st.session_state["_last_level"]    = new_level
                            st.rerun()

                    else:
                        last        = st.session_state.session_results[-1] if st.session_state.session_results else {}
                        correct_idx = q["correct_index"]

                        if last.get("correct"):
                            st.markdown('<div class="result-correct"><div class="result-title">✅ Correct!</div><div class="result-body">Well done — you got it right.</div></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="result-wrong"><div class="result-title">❌ Incorrect</div><div class="result-body">Correct answer: <strong>{q["options"][correct_idx]}</strong></div></div>', unsafe_allow_html=True)

                        st.info(f"💡 **Explanation:** {q['explanation']}")

                        xp = st.session_state.pop("_last_xp", 0)
                        if xp:
                            st.markdown(f'<div class="xp-popup">✨ +{xp} XP earned!</div>', unsafe_allow_html=True)
                        if st.session_state.pop("_last_leveled", False):
                            level = st.session_state.pop("_last_level", 1)
                            st.balloons()
                            st.success(f"🎉 LEVEL UP! You are now Level {level} — {get_level_title(level)}!")

                        new_m     = last.get("new_m", modality_idx)
                        new_label = MODALITY_LABELS.get(new_m, "")
                        if new_m != modality_idx:
                            direction = "simplified" if new_m > modality_idx else "advanced"
                            st.warning(f"🔄 AEL → M={new_m}: {new_label} ({direction})")

                        if st.button("➡️ Next Question", type="primary", use_container_width=True):
                            st.session_state.quiz_question = None
                            st.session_state.quiz_answered = False
                            st.rerun()

            # ══════════════════════════════════════════════════════════════════════════
            # MODE 2: CODE EDITOR
            # ══════════════════════════════════════════════════════════════════════════
            elif st.session_state.quiz_mode == "code":

                if st.button("💻 Generate Coding Challenge", type="primary", use_container_width=True):
                    with st.spinner("Generating coding challenge..."):
                        cq = generate_coding_question(subject, topic, mastery)
                    if cq:
                        st.session_state.code_question  = cq
                        st.session_state.quiz_answered  = False
                        st.session_state.grading_result = None
                        st.session_state.student_code   = cq.get("starter_code", "# Write your solution here\n")
                        st.session_state.quiz_start_time= time.time()
                    else:
                        st.error("Could not generate challenge. Try again.")

                cq = st.session_state.code_question
                if cq:
                    st.markdown(
                        f'<div class="q-card">'
                        f'<div class="q-meta">'
                        f'<span class="q-badge badge-subject">{subject}</span>'
                        f'<span class="q-badge badge-topic">{topic}</span>'
                        f'<span class="q-badge badge-mastery">{mastery}</span>'
                        f'<span class="q-badge badge-mode">💻 Code</span>'
                        f'</div>'
                        f'<div class="q-text">{cq["question"]}</div></div>',
                        unsafe_allow_html=True
                    )

                    # Sample I/O
                    if cq.get("sample_input"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**Sample Input:**")
                            st.code(cq["sample_input"], language="text")
                        with c2:
                            st.markdown("**Expected Output:**")
                            st.code(cq["sample_output"], language="text")

                    if not st.session_state.quiz_answered:
                        # Hint
                        with st.expander("💡 Show Hint"):
                            st.info(cq.get("hint", "Think carefully about edge cases."))

                        st.markdown("**✍️ Your Solution:**")
                        st.markdown(
                            '<div class="code-wrap"><div class="code-header">'
                            '<span>Python Editor</span><span>Write your solution below</span></div></div>',
                            unsafe_allow_html=True
                        )

                        student_code = st.text_area(
                            "Code Editor",
                            value=st.session_state.student_code,
                            height=280,
                            label_visibility="collapsed",
                            key="code_editor_input",
                            placeholder="Write your Python solution here..."
                        )
                        st.session_state.student_code = student_code

                        if st.button("🚀 Submit Code", type="primary", use_container_width=True,
                                     disabled=not student_code.strip()):
                            elapsed = round(time.time() - (st.session_state.quiz_start_time or time.time()), 2)
                            with st.spinner("Grading your solution..."):
                                result = grade_code_answer(
                                    cq["question"], cq["starter_code"],
                                    student_code, cq["expected_output"], topic
                                )
                            st.session_state.grading_result = result
                            st.session_state.quiz_answered  = True
                            st.session_state.quiz_total    += 1

                            score_pct = (result["score"] / result["max_score"]) * 100
                            is_correct = score_pct >= 70
                            if is_correct:
                                st.session_state.quiz_score += 1

                            accuracy = log_quiz_attempt(uid, subject, topic,
                                                        result["score"], result["max_score"],
                                                        elapsed, modality_idx)
                            if not is_correct:
                                log_error_topic(uid, subject, topic)
                            recent_acc = get_recent_accuracy(uid, subject, topic, n=2)
                            update_ael(uid, subject, topic, recent_acc)

                            xp_gained, _, new_level, leveled_up = add_xp(uid, score_pct)
                            st.session_state.session_results.append({
                                "topic": topic, "correct": is_correct,
                                "latency": elapsed, "modality": modality_idx,
                                "new_m": modality_idx, "xp": xp_gained, "mode": "Code",
                                "score": f"{result['score']}/{result['max_score']}"
                            })
                            st.session_state["_last_xp"]     = xp_gained
                            st.session_state["_last_leveled"] = leveled_up
                            st.session_state["_last_level"]   = new_level
                            st.rerun()

                    else:
                        result = st.session_state.grading_result
                        if result:
                            verdict = result.get("verdict", "")
                            score_v = result.get("score", 0)
                            max_v   = result.get("max_score", 10)
                            panel_class = "result-correct" if verdict == "Correct" else "result-partial" if verdict == "Partial" else "result-wrong"
                            icon = "✅" if verdict == "Correct" else "🟡" if verdict == "Partial" else "❌"

                            st.markdown(
                                f'<div class="{panel_class}">'
                                f'<div class="result-title">{icon} {verdict} — {score_v}/{max_v}</div>'
                                f'<div class="result-body">{result.get("feedback","")}</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown(f"**⏱️ Time Complexity:** `{result.get('time_complexity','N/A')}`")
                            with c2:
                                st.markdown(f"**💡 Improvements:** {result.get('improvements','')}")

                            if result.get("correct_solution"):
                                with st.expander("✅ View Model Solution"):
                                    st.code(result["correct_solution"], language="python")

                            xp = st.session_state.pop("_last_xp", 0)
                            if xp:
                                st.markdown(f'<div class="xp-popup">✨ +{xp} XP earned!</div>', unsafe_allow_html=True)
                            if st.session_state.pop("_last_leveled", False):
                                level = st.session_state.pop("_last_level", 1)
                                st.balloons()
                                st.success(f"🎉 LEVEL UP! Level {level} — {get_level_title(level)}!")

                        if st.button("➡️ Next Challenge", type="primary", use_container_width=True):
                            st.session_state.code_question  = None
                            st.session_state.quiz_answered  = False
                            st.session_state.grading_result = None
                            st.session_state.student_code   = ""
                            st.rerun()

            # ══════════════════════════════════════════════════════════════════════════
            # MODE 3: SHORT ANSWER (theory subjects)
            # ══════════════════════════════════════════════════════════════════════════
            elif st.session_state.quiz_mode == "short":

                if st.button("✍️ Generate Short Answer Question", type="primary", use_container_width=True):
                    with st.spinner("Generating question..."):
                        sq = generate_short_answer_question(subject, topic, mastery)
                    if sq:
                        st.session_state.short_q        = sq
                        st.session_state.quiz_answered  = False
                        st.session_state.grading_result = None
                        st.session_state.student_answer = ""
                        st.session_state.quiz_start_time= time.time()
                    else:
                        st.error("Could not generate question. Try again.")

                sq = st.session_state.short_q
                if sq:
                    st.markdown(
                        f'<div class="q-card">'
                        f'<div class="q-meta">'
                        f'<span class="q-badge badge-subject">{subject}</span>'
                        f'<span class="q-badge badge-topic">{topic}</span>'
                        f'<span class="q-badge badge-mastery">{mastery}</span>'
                        f'<span class="q-badge badge-mode">✍️ Short Answer</span>'
                        f'</div>'
                        f'<div class="q-text">{sq["question"]}</div></div>',
                        unsafe_allow_html=True
                    )

                    if not st.session_state.quiz_answered:
                        with st.expander("💡 Show Hint"):
                            st.info(sq.get("hint", "Think about the core concepts."))

                        st.markdown("**Your Answer:**")
                        student_answer = st.text_area(
                            "Answer",
                            value=st.session_state.student_answer,
                            height=160,
                            label_visibility="collapsed",
                            placeholder="Write your answer here in 2-4 sentences...",
                            key="short_answer_input"
                        )
                        st.session_state.student_answer = student_answer

                        word_count = len(student_answer.split()) if student_answer.strip() else 0
                        st.caption(f"Word count: {word_count}")

                        if st.button("✅ Submit Answer", type="primary", use_container_width=True,
                                     disabled=word_count < 5):
                            elapsed = round(time.time() - (st.session_state.quiz_start_time or time.time()), 2)
                            with st.spinner("Grading your answer..."):
                                result = grade_short_answer(
                                    sq["question"], sq["key_points"],
                                    sq["model_answer"], student_answer, topic
                                )
                            st.session_state.grading_result = result
                            st.session_state.quiz_answered  = True
                            st.session_state.quiz_total    += 1

                            score_pct  = (result["score"] / result["max_score"]) * 100
                            is_correct = score_pct >= 60
                            if is_correct:
                                st.session_state.quiz_score += 1

                            accuracy = log_quiz_attempt(uid, subject, topic,
                                                        result["score"], result["max_score"],
                                                        elapsed, modality_idx)
                            if not is_correct:
                                log_error_topic(uid, subject, topic)
                            recent_acc = get_recent_accuracy(uid, subject, topic, n=2)
                            update_ael(uid, subject, topic, recent_acc)

                            xp_gained, _, new_level, leveled_up = add_xp(uid, score_pct)
                            st.session_state.session_results.append({
                                "topic": topic, "correct": is_correct,
                                "latency": elapsed, "modality": modality_idx,
                                "new_m": modality_idx, "xp": xp_gained, "mode": "Short Answer",
                                "score": f"{result['score']}/{result['max_score']}"
                            })
                            st.session_state["_last_xp"]     = xp_gained
                            st.session_state["_last_leveled"] = leveled_up
                            st.session_state["_last_level"]   = new_level
                            st.rerun()

                    else:
                        result = st.session_state.grading_result
                        if result:
                            verdict   = result.get("verdict", "")
                            score_v   = result.get("score", 0)
                            max_v     = result.get("max_score", 10)
                            icon_map  = {"Excellent": "🌟", "Good": "✅", "Partial": "🟡", "Needs Improvement": "❌"}
                            panel_map = {"Excellent": "result-correct", "Good": "result-correct",
                                         "Partial": "result-partial", "Needs Improvement": "result-wrong"}
                            icon       = icon_map.get(verdict, "📝")
                            panel_cls  = panel_map.get(verdict, "result-partial")

                            st.markdown(
                                f'<div class="{panel_cls}">'
                                f'<div class="result-title">{icon} {verdict} — {score_v}/{max_v}</div>'
                                f'<div class="result-body">{result.get("feedback","")}</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                            missed = result.get("missed_points", [])
                            if missed:
                                st.markdown("**Points you missed:**")
                                for pt in missed:
                                    st.markdown(f"- {pt}")

                            with st.expander("📖 Model Answer"):
                                st.info(result.get("model_answer", sq["model_answer"]))

                            xp = st.session_state.pop("_last_xp", 0)
                            if xp:
                                st.markdown(f'<div class="xp-popup">✨ +{xp} XP earned!</div>', unsafe_allow_html=True)
                            if st.session_state.pop("_last_leveled", False):
                                level = st.session_state.pop("_last_level", 1)
                                st.balloons()
                                st.success(f"🎉 LEVEL UP! Level {level} — {get_level_title(level)}!")

                        if st.button("➡️ Next Question", type="primary", use_container_width=True):
                            st.session_state.short_q        = None
                            st.session_state.quiz_answered  = False
                            st.session_state.grading_result = None
                            st.session_state.student_answer = ""
                            st.rerun()

            # ── Session history ───────────────────────────────────────────────────────
            if st.session_state.session_results:
                st.divider()
                with st.expander("📋 Session History", expanded=False):
                    for i, r in enumerate(st.session_state.session_results, 1):
                        icon  = "✅" if r["correct"] else "❌"
                        score = r.get("score", "")
                        score_str = f" | Score: {score}" if score else ""
                        st.caption(
                            f"{i}. {icon} [{r['mode']}] {r['topic']}"
                            f" | ⏱️ {r['latency']}s"
                            f" | +{r.get('xp',0)} XP"
                            f"{score_str}"
                        )

    _run_quiz()

# ══ TAB 3: ROADMAP ════════════════════════════════════════════════════════════
with tab3:
    def _run_plan():
        uid      = st.session_state.uid
        profile  = st.session_state.profile
        subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")
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
                        return

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
                return

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
                return

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
                            st.switch_page("pages/1_Learn.py")


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

    _run_plan()
