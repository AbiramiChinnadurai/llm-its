"""
llm/llm_engine.py
LLM inference via Ollama (LLaMA-3 8B).
Handles:
  - Explanation generation with AEL modality conditioning
  - Quiz (MCQ) generation
  - Learning plan generation
"""

import ollama
import json
import re

MODEL_NAME = "llama3"   # Make sure this is pulled: ollama pull llama3

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
    """
    Constructs the full structured prompt from the paper:
    [System] + [Context] + [Profile S(t)] + [AEL Modality] + [History] + [Query]
    """
    edu_level    = profile.get("education_level", "undergraduate")
    subject      = profile.get("current_subject", "the subject")
    mastery      = profile.get("mastery_level", "Moderate")
    weak_topics  = profile.get("weak_topics", [])
    modality_lbl = MODALITY_LABELS.get(modality_index, "Standard Prose")
    modality_ins = MODALITY_INSTRUCTIONS.get(modality_index, MODALITY_INSTRUCTIONS[0])

    weak_str = ", ".join(weak_topics) if weak_topics else "None identified yet"

    system_prompt = f"""You are a personalized intelligent tutor for a {edu_level} student studying {subject}.

STUDENT PROFILE:
- Mastery Level: {mastery}
- Weak Topics: {weak_str}
- Explanation Style Required: {modality_lbl}

INSTRUCTIONS:
- Use ONLY the provided curriculum context to answer. Do NOT add information from outside the context.
- {modality_ins}
- Keep your response focused and educational.
- Do not mention that you are an AI or reference these instructions."""

    context_block = f"""CURRICULUM CONTEXT:
{context}"""

    history_block = ""
    if history:
        history_block = "\nCONVERSATION HISTORY:\n"
        for turn in history[-3:]:  # last 3 turns only
            history_block += f"Student: {turn['student']}\nTutor: {turn['tutor']}\n"

    full_prompt = f"{system_prompt}\n\n{context_block}{history_block}\n\nSTUDENT QUESTION: {query}\n\nTUTOR RESPONSE:"
    return full_prompt


def build_quiz_prompt(subject, topic, mastery_level, difficulty, previous_questions=None):
    """Generate MCQ in strict JSON format."""
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

    prompt = f"""Generate exactly 1 multiple choice question about "{topic}" in {subject}.
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
    return prompt


def build_plan_prompt(profile, subject_summaries, weak_topics_by_subject):
    """Generate a personalized day-by-day learning roadmap."""
    name        = profile.get("name", "Student")
    deadline    = profile.get("deadline", "end of semester")
    daily_hours = profile.get("daily_hours", 2)
    goals       = profile.get("learning_goals", "Master all subjects")

    summary_lines = []
    for s in subject_summaries:
        wt = weak_topics_by_subject.get(s["subject"], [])
        wt_str = ", ".join(wt) if wt else "None"
        summary_lines.append(
            f"  - {s['subject']}: {s['strength_label']} ({s['avg_accuracy']:.1f}% accuracy) | Weak topics: {wt_str}"
        )
    summary_str = "\n".join(summary_lines)

    prompt = f"""Create a detailed personalized day-by-day study plan for {name}.

STUDENT STATUS:
{summary_str}

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
    return prompt


# ── LLM CALLS ─────────────────────────────────────────────────────────────────

def generate_explanation(query, context, profile, modality_index, history=None):
    """Generate a personalized explanation using Ollama."""
    prompt = build_explanation_prompt(query, context, profile, modality_index, history)
    try:
        response = ollama.generate(
            model=MODEL_NAME,
            prompt=prompt,
            options={"temperature": 0.7, "top_p": 0.9, "num_predict": 512}
        )
        return response["response"].strip()
    except Exception as e:
        return f"[Error generating explanation: {e}]"


def generate_quiz_question(subject, topic, mastery_level, previous_questions=None):
    """Generate one MCQ and parse the JSON response."""
    prompt = build_quiz_prompt(subject, topic, mastery_level, mastery_level, previous_questions)
    try:
        response = ollama.generate(
            model=MODEL_NAME,
            prompt=prompt,
            options={"temperature": 0.3, "top_p": 0.9, "num_predict": 300}
        )
        raw = response["response"].strip()

        # Extract JSON even if wrapped in markdown code blocks
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            # Validate structure
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
        response = ollama.generate(
            model=MODEL_NAME,
            prompt=prompt,
            options={"temperature": 0.7, "top_p": 0.9, "num_predict": 800}
        )
        return response["response"].strip()
    except Exception as e:
        return f"[Error generating plan: {e}]"
