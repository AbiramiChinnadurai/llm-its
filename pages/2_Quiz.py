"""
pages/2_Quiz.py
Quiz page — MCQ + Code Editor (coding subjects) + Short Answer (theory subjects).
Auto-detects subject type based on name.
"""

import streamlit as st
import time
from groq import Groq
import re
from database.db import (log_quiz_attempt, get_error_topics, get_ael_modality,
                          update_ael, log_error_topic, get_recent_accuracy,
                          get_subject_summary, add_xp, get_level_title)
from llm.llm_engine import generate_quiz_question, MODALITY_LABELS, MODEL_NAME

# ── Emotion-Aware Re-Routing ──────────────────────────────────────────────────
from emotion.emotion_engine import get_emotion_prompt_modifier
from emotion.emotion_widget import (
    get_tracker, reset_tracker,
    render_emotion_sidebar, render_reroute_banner,
    render_session_emotion_summary
)

st.set_page_config(page_title="Quiz | LLM-ITS", page_icon="🧠", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=Instrument+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Instrument Sans', sans-serif; }
.stApp { background: #080c14; color: #d4dbe8; }

.quiz-header {
    background: linear-gradient(160deg, #0d1524 0%, #080c14 60%);
    border: 1px solid #1a2540; border-radius: 20px;
    padding: 32px 40px; margin-bottom: 32px;
    position: relative; overflow: hidden;
}
.quiz-header::after {
    content: 'QUIZ'; position: absolute; right: 32px; top: 50%;
    transform: translateY(-50%); font-family: 'Syne', sans-serif;
    font-size: 5rem; font-weight: 800; color: rgba(255,255,255,0.025);
    letter-spacing: 0.15em; pointer-events: none; user-select: none;
}
.quiz-title { font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800; color:#f0f6ff; margin:0 0 4px 0; }
.quiz-sub   { color:#4a6080; font-size:0.88rem; margin:0; font-weight:300; }

/* Mode tabs */
.mode-tab-row { display:flex; gap:10px; margin-bottom:24px; }
.mode-tab {
    flex:1; padding:14px 16px; border-radius:14px; border:1px solid #1a2540;
    background:#0d1524; cursor:pointer; text-align:center; transition:all 0.2s;
}
.mode-tab.active { border-color:#2563eb; background:#0d1a2e; box-shadow:0 0 0 1px rgba(59,130,246,0.2); }
.mode-tab .mt-icon { font-size:1.5rem; margin-bottom:4px; }
.mode-tab .mt-label { font-family:'Syne',sans-serif; font-size:0.8rem; font-weight:700; color:#d4dbe8; }
.mode-tab .mt-desc  { font-size:0.7rem; color:#4a6080; margin-top:2px; }
.mode-tab.active .mt-label { color:#60a5fa; }

/* Question card */
.q-card {
    background:#0d1524; border:1px solid #1a2540; border-radius:16px;
    padding:24px 28px; margin-bottom:20px;
}
.q-meta { display:flex; gap:10px; margin-bottom:14px; flex-wrap:wrap; }
.q-badge {
    font-size:0.68rem; border-radius:8px; padding:3px 10px;
    font-weight:600; border:1px solid;
}
.badge-subject  { background:#0d1a2e; color:#60a5fa; border-color:#1d4ed8; }
.badge-topic    { background:#0f1a10; color:#4ade80; border-color:#166534; }
.badge-mastery  { background:#1c1005; color:#fbbf24; border-color:#92400e; }
.badge-mode     { background:#1a0d2e; color:#c084fc; border-color:#7c3aed; }
.q-text { font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:600; color:#f0f6ff; line-height:1.5; }

/* Code editor area */
.code-wrap {
    background:#0a0e18; border:1px solid #1a2540; border-radius:12px;
    padding:4px; margin:16px 0;
}
.code-header {
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; border-bottom:1px solid #1a2540;
    font-size:0.72rem; color:#4a6080; font-family:'JetBrains Mono',monospace;
}

/* Result panels */
.result-correct {
    background:#081810; border:1px solid #065f35; border-radius:12px;
    padding:16px 20px; margin:12px 0;
}
.result-wrong {
    background:#180808; border:1px solid #7f1d1d; border-radius:12px;
    padding:16px 20px; margin:12px 0;
}
.result-partial {
    background:#141005; border:1px solid #78350f; border-radius:12px;
    padding:16px 20px; margin:12px 0;
}
.result-title { font-family:'Syne',sans-serif; font-size:1rem; font-weight:700; margin-bottom:8px; }
.result-correct .result-title { color:#34d399; }
.result-wrong   .result-title { color:#f87171; }
.result-partial .result-title { color:#fbbf24; }
.result-body { font-size:0.84rem; color:#8090a8; line-height:1.7; }

/* XP popup */
.xp-popup {
    background:linear-gradient(135deg,#1d4ed8,#7c3aed);
    border-radius:12px; padding:12px 20px; margin:12px 0;
    font-family:'Syne',sans-serif; font-size:0.9rem;
    font-weight:700; color:#fff; text-align:center;
    box-shadow:0 4px 20px rgba(124,58,237,0.3);
}

/* Sidebar */
.stat-card {
    background:#0d1524; border:1px solid #1a2540; border-radius:12px;
    padding:14px 16px; margin-bottom:10px;
}
.stat-val   { font-family:'Syne',sans-serif; font-size:1.8rem; font-weight:800; color:#f0f6ff; }
.stat-label { font-size:0.68rem; color:#3a5070; text-transform:uppercase; letter-spacing:0.1em; }

.section-label { font-size:0.68rem; font-weight:600; letter-spacing:0.12em;
                 text-transform:uppercase; color:#2a4060; margin:16px 0 8px 0; }

.stButton > button {
    border-radius:12px !important; font-family:'Instrument Sans',sans-serif !important;
    font-size:0.84rem !important; font-weight:500 !important;
    transition:all 0.2s !important; border:1px solid #1a2540 !important;
    background:#0d1524 !important; color:#8090a8 !important;
}
.stButton > button:hover { background:#1a2540 !important; border-color:#3b82f6 !important; color:#f0f4ff !important; transform: translateY(-2px) !important; }
button[kind="primary"] {
    background:linear-gradient(135deg,#2563eb,#1d4ed8) !important;
    border-color:#3b82f6 !important; color:#fff !important; font-weight:600 !important;
}
button[kind="primary"]:hover {
    background:linear-gradient(135deg,#3b82f6,#2563eb) !important;
    box-shadow:0 4px 20px rgba(37,99,235,0.35) !important;
}
hr { border-color:#1a2540 !important; }
[data-baseweb="select"] { background:#0d1524 !important; border-color:#1a2540 !important; border-radius:10px !important; }
[data-baseweb="input"]  { background:#0d1524 !important; border-color:#1a2540 !important; border-radius:10px !important; }
textarea { background:#0a0e18 !important; border-color:#1a2540 !important;
           border-radius:10px !important; font-family:'JetBrains Mono',monospace !important;
           font-size:0.85rem !important; color:#e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────
if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid      = st.session_state.uid
profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

# ── Detect if subject is coding-related ───────────────────────────────────────
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

# ── Emotion tracker (one per quiz session) ────────────────────────────────────
quiz_tracker = get_tracker("quiz_emotion_tracker")

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
        reset_tracker("quiz_emotion_tracker")
        quiz_tracker = get_tracker("quiz_emotion_tracker")
        st.rerun()

    # ── Emotion Monitor ───────────────────────────────────────────────────────
    st.divider()
    render_emotion_sidebar(quiz_tracker)

# ══ MAIN ══════════════════════════════════════════════════════════════════════
with col_main:

    if not topic:
        st.info("👆 Enter a topic in the sidebar and choose a quiz mode to begin.")
        st.stop()

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

                    # ── Emotion Detection ─────────────────────────────────────
                    quiz_tracker.record(
                        text=choice,
                        latency_s=elapsed,
                        correct=is_correct
                    )

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

                    # Evaluate emotion every 3 answers
                    if quiz_tracker.should_evaluate():
                        emotion_result = quiz_tracker.evaluate(topic=topic)
                        st.session_state["_emotion_result"] = emotion_result
                    else:
                        st.session_state.pop("_emotion_result", None)

                    st.rerun()

            else:
                last        = st.session_state.session_results[-1] if st.session_state.session_results else {}
                correct_idx = q["correct_index"]

                if last.get("correct"):
                    st.markdown('<div class="result-correct"><div class="result-title">✅ Correct!</div><div class="result-body">Well done — you got it right.</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="result-wrong"><div class="result-title">❌ Incorrect</div><div class="result-body">Correct answer: <strong>{q["options"][correct_idx]}</strong></div></div>', unsafe_allow_html=True)

                st.info(f"💡 **Explanation:** {q['explanation']}")

                # ── Emotion re-routing banner ─────────────────────────────────
                emotion_result = st.session_state.pop("_emotion_result", None)
                if emotion_result and emotion_result.should_reroute:
                    render_reroute_banner(emotion_result)

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
            # ── Emotion journey summary ───────────────────────────────────────
            render_session_emotion_summary(quiz_tracker)
