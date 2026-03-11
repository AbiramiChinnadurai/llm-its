"""
xai/xai_engine.py
─────────────────────────────────────────────────────────────────────────────
Explainable AI (XAI) Engine for LLM-ITS
─────────────────────────────────────────────────────────────────────────────
Generates multi-source human-readable explanations for every learning path
decision, drawing from THREE traceable sources simultaneously:

  Source 1 — KG Prerequisite Trace  : WHY this topic, WHY this order
  Source 2 — LLM Chain-of-Thought   : WHY this explanation style
  Source 3 — Affective Rationale    : WHY the path changed (emotion-driven)

Also supports:
  - Counterfactual explanations ("Why NOT topic X?")
  - Confidence scoring per path step
  - Difficulty justification from KG weights
  - Progress visualization (text-based path trace)
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional


# ─── XAI Explanation Sources ─────────────────────────────────────────────────

SOURCE_KG       = "kg"        # Knowledge Graph prerequisite trace
SOURCE_LLM      = "llm"       # LLM Chain-of-Thought reasoning
SOURCE_EMOTION  = "emotion"   # Affective state rationale
SOURCE_MASTERY  = "mastery"   # Performance/accuracy-based reasoning
SOURCE_COMBINED = "combined"  # All sources fused


# ─── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class XAIExplanation:
    """A full XAI explanation for a single path decision."""
    topic:           str
    subject:         str

    # Core explanation fields
    why_this_topic:  str = ""   # KG prerequisite rationale
    why_now:         str = ""   # Performance or emotion-triggered rationale
    difficulty_note: str = ""   # KG difficulty justification
    what_if_struggle:str = ""   # Pre-planned remediation from KG
    progress_trace:  str = ""   # Text-based KG path visualization
    cot_reasoning:   str = ""   # LLM chain-of-thought (generated on demand)

    # Metadata
    confidence:      float = 0.8
    sources_used:    list  = field(default_factory=list)
    emotion_state:   str   = "neutral"
    mastery_level:   str   = "Moderate"
    difficulty:      int   = 2

    def to_dict(self) -> dict:
        return {
            "topic":           self.topic,
            "subject":         self.subject,
            "why_this_topic":  self.why_this_topic,
            "why_now":         self.why_now,
            "difficulty_note": self.difficulty_note,
            "what_if_struggle":self.what_if_struggle,
            "progress_trace":  self.progress_trace,
            "confidence":      round(self.confidence, 2),
            "sources_used":    self.sources_used,
            "emotion_state":   self.emotion_state,
        }


@dataclass
class CounterfactualExplanation:
    """Explains why a topic was NOT chosen."""
    rejected_topic:  str
    reason:          str
    missing_prereqs: list = field(default_factory=list)
    difficulty_gap:  int  = 0


# ─── Source 1: KG Prerequisite Trace ────────────────────────────────────────

def explain_from_kg(topic: str, subject: str, kg, mastered_topics: list) -> dict:
    """
    Generate KG-grounded explanation fields.
    Returns dict with why_this_topic, difficulty_note, what_if_struggle,
    progress_trace, confidence.
    """
    if kg is None:
        return {
            "why_this_topic":   f"**{topic}** is part of your {subject} curriculum.",
            "difficulty_note":  "Difficulty information not available.",
            "what_if_struggle": "Review previous topics if you find this difficult.",
            "progress_trace":   f"→ {topic}",
            "confidence":       0.5,
        }

    prereqs      = kg.get_prerequisites(topic)
    chain        = kg.get_learning_chain(topic)
    difficulty   = kg.get_difficulty(topic)
    remediation  = kg.get_remediation_topic(topic)
    mastered_set = {m.lower() for m in mastered_topics}

    # Difficulty label + justification
    diff_labels = {1: "Foundational", 2: "Conceptual", 3: "Applied",
                   4: "Advanced", 5: "Expert-level"}
    diff_label  = diff_labels.get(difficulty, "Intermediate")

    # WHY THIS TOPIC
    if not prereqs:
        why = (f"**{topic}** is a foundational concept in {subject} — "
               f"it has no prerequisites and is the right starting point.")
    else:
        mastered_prereqs   = [p for p in prereqs if p.lower() in mastered_set]
        unmastered_prereqs = [p for p in prereqs if p.lower() not in mastered_set]

        if not unmastered_prereqs:
            why = (f"You have already mastered all prerequisites for **{topic}** "
                   f"({', '.join(mastered_prereqs)}), so this is the logical next step "
                   f"in your {subject} learning chain.")
        else:
            why = (f"**{topic}** builds directly on {', '.join(prereqs)}. "
                   f"Some prerequisites ({', '.join(unmastered_prereqs)}) "
                   f"may need review — but this topic will help consolidate them.")

    # DIFFICULTY NOTE
    diff_note = (f"This topic is rated **{difficulty}/5 — {diff_label}** in the "
                 f"{subject} knowledge graph. "
                 f"{'It introduces new concepts from scratch.' if difficulty == 1 else ''}"
                 f"{'It requires understanding of earlier concepts.' if difficulty == 2 else ''}"
                 f"{'It requires you to apply concepts to problems.' if difficulty == 3 else ''}"
                 f"{'It involves complex reasoning and analysis.' if difficulty >= 4 else ''}")

    # WHAT IF STRUGGLE
    if remediation and remediation.lower() != topic.lower():
        struggle = (f"If you find **{topic}** difficult, I will re-route you to "
                    f"**{remediation}** first — the most foundational concept in this chain.")
    else:
        struggle = f"If you struggle, try breaking **{topic}** into smaller sub-concepts."

    # PROGRESS TRACE (visual chain)
    if len(chain) > 1:
        trace_parts = []
        for t in chain:
            if t.lower() in mastered_set:
                trace_parts.append(f"✓ {t}")
            elif t.lower() == topic.lower():
                trace_parts.append(f"▶ **{t}**")
            else:
                trace_parts.append(f"○ {t}")
        trace = " → ".join(trace_parts)
    else:
        trace = f"▶ **{topic}** (foundational)"

    # CONFIDENCE: based on how complete the prerequisite mastery is
    if prereqs:
        mastered_count = sum(1 for p in prereqs if p.lower() in mastered_set)
        confidence = 0.5 + 0.5 * (mastered_count / len(prereqs))
    else:
        confidence = 0.9  # foundational topics always high confidence

    return {
        "why_this_topic":   why,
        "difficulty_note":  diff_note,
        "what_if_struggle": struggle,
        "progress_trace":   trace,
        "confidence":       round(confidence, 2),
    }


# ─── Source 2: Mastery/Performance Rationale ────────────────────────────────

def explain_from_mastery(topic: str, subject: str, mastery_level: str,
                          accuracy: float, modality_idx: int) -> str:
    """
    Generate WHY NOW explanation from student performance data.
    """
    modality_labels = {
        0: "standard prose",
        1: "step-by-step breakdown",
        2: "analogical reasoning",
        3: "worked examples",
        4: "simplified language"
    }
    modality_label = modality_labels.get(modality_idx, "adaptive")

    if mastery_level == "Weak" or accuracy < 50:
        return (f"Your recent accuracy in {subject} is **{accuracy:.0f}%**, "
                f"so I'm using **{modality_label}** to explain **{topic}** "
                f"in the most accessible way possible. "
                f"Focus on understanding the concept before attempting practice questions.")

    elif mastery_level == "Strong" or accuracy >= 75:
        return (f"You're performing strongly in {subject} (**{accuracy:.0f}% accuracy**). "
                f"I'm presenting **{topic}** using **{modality_label}** "
                f"at an appropriately challenging level to push your understanding further.")

    else:
        return (f"Based on your **{accuracy:.0f}% accuracy** in {subject}, "
                f"**{topic}** is a well-timed next step. "
                f"I'm using **{modality_label}** to balance clarity with depth.")


# ─── Source 3: Emotion/Affective Rationale ──────────────────────────────────

def explain_from_emotion(emotion_state: str, action: str, topic: str) -> str:
    """
    Generate WHY NOW addendum when path was changed due to emotion detection.
    Returns empty string if state is neutral (no change needed).
    """
    if emotion_state == "neutral" or not action or action == "none":
        return ""

    explanations = {
        "frustration": (
            f"I also detected signs of **frustration** in your recent responses. "
            f"I've simplified the explanation of **{topic}** and slowed the pacing "
            f"to help you rebuild confidence before moving forward."
        ),
        "boredom": (
            f"Your responses suggest you may already be familiar with parts of **{topic}**. "
            f"I've advanced the difficulty level to keep you appropriately challenged."
        ),
        "anxiety": (
            f"I noticed signs of **uncertainty** in your responses. "
            f"I've switched to worked examples for **{topic}** so you can "
            f"follow a complete solution before attempting questions independently."
        ),
        "confusion": (
            f"Your responses suggest **confusion** — possibly a missing prerequisite. "
            f"I've adjusted the explanation of **{topic}** to cover the foundational "
            f"concepts it depends on before building up."
        ),
        "confidence": (
            f"You're showing **strong confidence** — great work! "
            f"I've introduced a more challenging application of **{topic}** "
            f"to consolidate your understanding through transfer."
        ),
    }
    return explanations.get(emotion_state, "")


# ─── Counterfactual: Why NOT a topic ────────────────────────────────────────

def explain_counterfactual(rejected_topic: str, current_topic: str,
                            kg, mastered_topics: list) -> CounterfactualExplanation:
    """
    Explain why rejected_topic was NOT recommended right now.
    Used when student asks "why not X?" or for proactive transparency.
    """
    if kg is None:
        return CounterfactualExplanation(
            rejected_topic = rejected_topic,
            reason         = f"**{rejected_topic}** is not yet in focus — "
                             f"complete **{current_topic}** first to unlock it.",
        )

    mastered_set = {m.lower() for m in mastered_topics}
    prereqs      = kg.get_prerequisites(rejected_topic)
    unmastered   = [p for p in prereqs if p.lower() not in mastered_set]
    difficulty   = kg.get_difficulty(rejected_topic)
    curr_diff    = kg.get_difficulty(current_topic)
    diff_gap     = difficulty - curr_diff

    if unmastered:
        reason = (f"**{rejected_topic}** requires you to first master: "
                  f"**{', '.join(unmastered)}**. "
                  f"Complete these prerequisites and it will be unlocked automatically.")
    elif diff_gap > 2:
        reason = (f"**{rejected_topic}** is rated {difficulty}/5 difficulty — "
                  f"significantly harder than your current level. "
                  f"Build up through intermediate topics first.")
    else:
        reason = (f"**{rejected_topic}** is available but **{current_topic}** "
                  f"was prioritised based on your current mastery gaps. "
                  f"You can switch to it from the topic list.")

    return CounterfactualExplanation(
        rejected_topic  = rejected_topic,
        reason          = reason,
        missing_prereqs = unmastered,
        difficulty_gap  = diff_gap,
    )


# ─── LLM Chain-of-Thought Generator ─────────────────────────────────────────

def generate_cot_explanation(topic: str, subject: str, query: str,
                              groq_client, model_name: str) -> str:
    """
    Ask the LLM to reason step-by-step about WHY it's explaining a topic
    the way it is. Returns a 2-3 sentence reasoning trace.
    Called ONLY when the user explicitly requests an explanation ("why?").
    """
    if groq_client is None:
        return ""

    prompt = f"""A student studying {subject} asked: "{query}"
The topic being explained is: {topic}

In 2-3 sentences, explain your reasoning for HOW you approached this explanation:
- What aspect of the topic you focused on and why
- How the student's likely knowledge level influenced your approach
- What you prioritised to make this maximally useful

Be direct and first-person. Do not say "As an AI". Start with "I focused on..."."""

    try:
        response = groq_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ""


# ─── Master XAI Builder ──────────────────────────────────────────────────────

def build_xai_explanation(
    topic:          str,
    subject:        str,
    query:          str           = "",
    kg                            = None,
    mastered_topics: list         = None,
    mastery_level:  str           = "Moderate",
    accuracy:       float         = 60.0,
    modality_idx:   int           = 0,
    emotion_state:  str           = "neutral",
    emotion_action: str           = "none",
    groq_client                   = None,
    model_name:     str           = "",
    generate_cot:   bool          = False,
) -> XAIExplanation:
    """
    Master function — builds a complete XAI explanation from all sources.

    Args:
        topic           : current topic being studied
        subject         : subject name
        query           : student's question (for CoT)
        kg              : KnowledgeGraph instance (or None)
        mastered_topics : list of mastered topic names
        mastery_level   : "Weak" / "Moderate" / "Strong"
        accuracy        : student's recent accuracy % in this subject
        modality_idx    : current AEL modality index
        emotion_state   : detected emotion state (from EmotionSessionTracker)
        emotion_action  : re-routing action taken (or "none")
        groq_client     : Groq client (for CoT, optional)
        model_name      : Groq model name
        generate_cot    : whether to call LLM for chain-of-thought (slower)

    Returns:
        XAIExplanation with all fields populated
    """
    if mastered_topics is None:
        mastered_topics = []

    sources_used = []

    # Source 1: KG
    kg_data = explain_from_kg(topic, subject, kg, mastered_topics)
    sources_used.append(SOURCE_KG if kg else SOURCE_MASTERY)

    # Source 2: Mastery/performance
    why_now = explain_from_mastery(topic, subject, mastery_level,
                                    accuracy, modality_idx)
    sources_used.append(SOURCE_MASTERY)

    # Source 3: Emotion (addendum to why_now)
    emotion_addendum = explain_from_emotion(emotion_state, emotion_action, topic)
    if emotion_addendum:
        why_now += f"\n\n{emotion_addendum}"
        sources_used.append(SOURCE_EMOTION)

    # Optional: LLM Chain-of-Thought
    cot = ""
    if generate_cot and groq_client and query:
        cot = generate_cot_explanation(topic, subject, query, groq_client, model_name)
        if cot:
            sources_used.append(SOURCE_LLM)

    difficulty = kg.get_difficulty(topic) if kg else 2

    return XAIExplanation(
        topic            = topic,
        subject          = subject,
        why_this_topic   = kg_data["why_this_topic"],
        why_now          = why_now,
        difficulty_note  = kg_data["difficulty_note"],
        what_if_struggle = kg_data["what_if_struggle"],
        progress_trace   = kg_data["progress_trace"],
        cot_reasoning    = cot,
        confidence       = kg_data["confidence"],
        sources_used     = sources_used,
        emotion_state    = emotion_state,
        mastery_level    = mastery_level,
        difficulty       = difficulty,
    )


# ─── XAI Prompt Injection ────────────────────────────────────────────────────

def get_xai_system_note(xai: XAIExplanation) -> str:
    """
    Returns a compact note to prepend to the LLM system prompt,
    giving the model awareness of WHY it's teaching this topic.
    This improves response coherence without bloating the prompt.
    """
    lines = [
        f"XAI TEACHING CONTEXT for {xai.topic}:",
        f"- Curriculum difficulty: {xai.difficulty}/5",
        f"- Student mastery: {xai.mastery_level}",
    ]
    if xai.emotion_state not in ("neutral", ""):
        lines.append(f"- Detected emotional state: {xai.emotion_state}")
    if xai.confidence < 0.6:
        lines.append("- Note: Student may have unmastered prerequisites — explain foundational concepts first.")
    return "\n".join(lines)
