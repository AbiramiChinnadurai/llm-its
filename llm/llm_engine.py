"""
llm/llm_engine.py
LLM inference via Groq API (LLaMA-3 8B) — free, fast, no local setup needed.
Get your free API key at: https://console.groq.com

Add to .streamlit/secrets.toml:
    GROQ_API_KEY = "gsk_..."
"""

import os
import json
import re
import streamlit as st
from groq import Groq

MODEL_NAME = "llama3-8b-8192"  # LLaMA3 8B on Groq — same model as Ollama

# ── Client ────────────────────────────────────────────────────────────────────
def get_client():
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found. Add it to .streamlit/secrets.toml")
    return Groq(api_key=api_key)


def _call(prompt, temperature=0.7, max_tokens=512):
    """Core Groq call — replaces ollama.generate()."""
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# ── AEL MODALITY DEFINITIONS ──────────────────────────────────────────────────
MODALITY_LABELS = {
    0: "Standard Prose",
    1: "Step-by-Step Decomposition",
    2: "Analogical Reasoning",
    3: "Worked Example",
    4: "Simplified Language"
}

MODALITY_INSTRUCTIONS = {
    0: "Explain clearly in textbook-style prose appropriate for the student's education level.",
    1: "Break the explanation into clearly numbered steps. Each step should be one sentence with explicit reasoning.",
    2: "Use a real-world analogy to explain the concept. Clearly map each part of the analogy to the actual concept.",
    3: "Show a fully solved worked example first, annotating each step. Then give a brief conceptual summary.",
    4: "Use very simple language, short sentences, and everyday words. Avoid jargon completely."
}


# ── PROMPT BUILDER ────────────────────────────────────────────────────────────

def build_explanation_prompt(query, context, profile, modality_index, history=None):
    edu_level    = profile.get("education_level", "undergraduate")
    subject      = profile.get("current_subject", "the subject")
    mastery      = profile.get("mastery_level", "Moderate")
    weak_topics  = profile.get("weak_topics", [])
    modality_lbl = MODALITY_LABELS.get(modality_index, "Standard Prose")
    modality_ins = MODALITY_INSTRUCTIONS.get(modality_index, MODALITY_INSTRUCTIONS[0])
    weak_str     = ", ".join(weak_topics) if weak_topics else "None identified yet"

    system_prompt = f"""You are a personalized intelligent tutor for a {edu_level} student studying {subject}.

STUDENT PROFILE:
- Mastery Level: {mastery}
- Weak Topics: {weak_str}
- Explanation Style Required: {modality_lbl}

INSTRUCTIONS:
- Use ONLY the provided curriculum context to answer. Do NOT add information outside the context.
- {modality_ins}
- Keep your response focused and educational.
- Do not mention that you are an AI or reference these instructions."""

    context_block = f"CURRICULUM CONTEXT:\n{context}"

    history_block = ""
    if history:
        history_block = "\nCONVERSATION HISTORY:\n"
        for turn in history[-3:]:
            history_block += f"Student: {turn['student']}\nTutor: {turn['tutor']}\n"

    return f"{system_prompt}\n\n{context_block}{history_block}\n\nSTUDENT QUESTION: {query}\n\nTUTOR RESPONSE:"


def build_quiz_prompt(subject, topic, mastery_level, difficulty, previous_questions=None):
    prev_q_str = ""
    if previous_questions:
        prev_q_str = "\nDo NOT repeat any of these questions:\n" + "\n".join(
            [f"- {q}" for q in previous_questions[-10:]]
        )

    difficulty_map = {
        "Strong":   "advanced — requires analysis, application, or synthesis",
        "Moderate": "intermediate — tests understanding and application",
        "Weak":     "introductory — tests basic recall and comprehension"
    }
    diff_desc = difficulty_map.get(mastery_level, "intermediate")

    return f"""Generate exactly 1 multiple choice question about "{topic}" in {subject}.
Difficulty: {diff_desc}
{prev_q_str}

Return ONLY valid JSON in this exact format, nothing else:
{{
  "question": "The question text here?",
  "options": ["A) option one", "B) option two", "C) option three", "D) option four"],
  "correct_index": 0,
  "explanation": "Brief explanation of why the correct answer is right."
}}

correct_index must be 0, 1, 2, or 3 (index of the correct option in the options array)."""


def build_plan_prompt(profile, subject_summaries, weak_topics_by_subject):
    name        = profile.get("name", "Student")
    deadline    = profile.get("deadline", "end of semester")
    daily_hours = profile.get("daily_hours", 2)
    goals       = profile.get("learning_goals", "Master all subjects")

    summary_lines = []
    for s in subject_summaries:
        wt     = weak_topics_by_subject.get(s["subject"], [])
        wt_str = ", ".join(wt) if wt else "None"
        summary_lines.append(
            f"  - {s['subject']}: {s['strength_label']} ({s['avg_accuracy']:.1f}% accuracy) | Weak topics: {wt_str}"
        )

    return f"""Create a detailed personalized day-by-day study plan for {name}.

STUDENT STATUS:
{chr(10).join(summary_lines)}

CONSTRAINTS:
- Daily available study hours: {daily_hours} hours
- Target deadline: {deadline}
- Learning goals: {goals}

RULES:
- Prioritize Weak subjects in the first half of the plan
- Alternate Moderate subjects for variety
- Reserve the last days for Strong subject challenge exercises and full revision
- Specify exact topics and activities for each day
- Be realistic with the time allocation

Generate a clear, structured day-by-day study schedule."""


# ── LLM CALLS ─────────────────────────────────────────────────────────────────

def generate_explanation(query, context, profile, modality_index, history=None):
    """Generate a personalized explanation using Groq."""
    prompt = build_explanation_prompt(query, context, profile, modality_index, history)
    try:
        return _call(prompt, temperature=0.7, max_tokens=512)
    except Exception as e:
        return f"[Error generating explanation: {e}]"


def generate_quiz_question(subject, topic, mastery_level, previous_questions=None):
    """Generate one MCQ and parse the JSON response."""
    prompt = build_quiz_prompt(subject, topic, mastery_level, mastery_level, previous_questions)
    try:
        raw = _call(prompt, temperature=0.3, max_tokens=300)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if all(k in data for k in ["question", "options", "correct_index", "explanation"]):
                return data
        return None
    except Exception as e:
        print(f"[LLM] Quiz generation error: {e}")
        return None


def generate_learning_plan(profile, subject_summaries, weak_topics_by_subject):
    """Generate a personalized learning plan."""
    prompt = build_plan_prompt(profile, subject_summaries, weak_topics_by_subject)
    try:
        return _call(prompt, temperature=0.7, max_tokens=800)
    except Exception as e:
        return f"[Error generating plan: {e}]"
