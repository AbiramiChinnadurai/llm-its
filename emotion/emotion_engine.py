"""
emotion/emotion_engine.py
─────────────────────────────────────────────────────────────────────────────
Multi-signal Emotion Detection Engine for LLM-ITS
─────────────────────────────────────────────────────────────────────────────
Detects 5 affective states from 3 signal sources:
  Signal 1 — Text Sentiment  : keyword + pattern analysis on student messages
  Signal 2 — Interaction Timing : response latency patterns
  Signal 3 — Answer Patterns   : consecutive correct/wrong streaks

Fuses all 3 into a composite Affective State Vector and returns:
  - dominant emotional state
  - re-routing action (what the ITS should do)
  - XAI explanation (why the path is being changed)
"""

import time
import re
from dataclasses import dataclass, field
from typing import Optional

# ─── Affective State Constants ────────────────────────────────────────────────
FRUSTRATION  = "frustration"
BOREDOM      = "boredom"
ANXIETY      = "anxiety"
CONFUSION    = "confusion"
CONFIDENCE   = "confidence"
NEUTRAL      = "neutral"

# ─── Re-routing Actions ───────────────────────────────────────────────────────
ACTION_SIMPLIFY    = "simplify"       # reduce difficulty, inject encouragement
ACTION_ADVANCE     = "advance"        # skip mastered content, go to harder level
ACTION_SCAFFOLD    = "scaffold"       # show worked examples first, then practice
ACTION_REMEDIATE   = "remediate"      # re-route to prerequisite concept
ACTION_CHALLENGE   = "challenge"      # interleaved practice, application-level
ACTION_NONE        = "none"           # no re-routing needed

# ─── Thresholds ───────────────────────────────────────────────────────────────
THRESHOLDS = {
    FRUSTRATION: 0.20,
    BOREDOM:     0.18,
    ANXIETY:     0.20,
    CONFUSION:   0.18,
    CONFIDENCE:  0.22,
}

# ─── Text Signal: Keyword Banks ───────────────────────────────────────────────
FRUSTRATION_KEYWORDS = [
    "don't understand", "dont understand", "i give up", "this is hard",
    "i can't", "i cant", "doesn't make sense", "doesnt make sense",
    "so confused", "no idea", "makes no sense", "stuck", "frustrated",
    "this is too hard", "i hate this", "impossible", "nothing makes sense",
    "lost", "completely lost", "absolutely no idea", "i'm lost", "im lost",
    "this sucks", "i don't get it", "i dont get it", "why is this so hard",
    "forget it", "forget this", "this is terrible", "i quit"
]

BOREDOM_KEYWORDS = [
    "this is easy", "too easy", "i know this", "already know",
    "boring", "i know all of this", "way too simple", "so simple",
    "i mastered this", "been through this", "done this before",
    "already covered", "skip this", "move on", "next topic",
    "can we go faster", "speed this up", "this is basic", "too basic"
]

ANXIETY_KEYWORDS = [
    "i'm not sure", "im not sure", "i think", "maybe", "not confident",
    "probably wrong", "i might be wrong", "i'm scared", "im scared",
    "what if i fail", "afraid", "nervous", "worried about",
    "not ready", "not prepared", "will i fail", "exam anxiety",
    "pressure", "stressed", "stressed out", "don't think i can",
    "dont think i can", "i hope this is right", "unsure"
]

CONFUSION_KEYWORDS = [
    "what does", "what is", "i don't follow", "i dont follow",
    "can you explain", "what do you mean", "clarify", "confused",
    "unclear", "not clear", "what's the difference", "whats the difference",
    "how does this work", "why does", "i don't see how", "i dont see how",
    "repeat that", "say that again", "can you rephrase", "huh",
    "i'm confused", "im confused", "explain again", "one more time",
    "i still don't understand", "i still dont understand"
]

CONFIDENCE_KEYWORDS = [
    "got it", "i understand", "makes sense", "clear now",
    "i see", "that makes sense", "i figured it out", "solved it",
    "i know this", "easy", "simple", "no problem", "this is clear",
    "understood", "yes exactly", "that's right", "thats right",
    "i'm confident", "im confident", "ready for next", "let's continue",
    "lets continue", "i can do this", "i nailed it"
]


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class AffectiveStateVector:
    """Composite emotion scores from all three signal sources (0.0 – 1.0 each)."""
    frustration: float = 0.0
    boredom:     float = 0.0
    anxiety:     float = 0.0
    confusion:   float = 0.0
    confidence:  float = 0.0

    def dominant(self) -> str:
        """Return the emotion with the highest score above its threshold."""
        scores = {
            FRUSTRATION: self.frustration,
            BOREDOM:     self.boredom,
            ANXIETY:     self.anxiety,
            CONFUSION:   self.confusion,
            CONFIDENCE:  self.confidence,
        }
        # Filter to only those above threshold
        above = {k: v for k, v in scores.items() if v >= THRESHOLDS[k]}
        if not above:
            return NEUTRAL
        return max(above, key=above.get)

    def to_dict(self) -> dict:
        return {
            "frustration": round(self.frustration, 3),
            "boredom":     round(self.boredom, 3),
            "anxiety":     round(self.anxiety, 3),
            "confusion":   round(self.confusion, 3),
            "confidence":  round(self.confidence, 3),
            "dominant":    self.dominant()
        }


@dataclass
class EmotionSignal:
    """Result from a single signal source."""
    source: str        # "text", "timing", "pattern"
    scores: AffectiveStateVector = field(default_factory=AffectiveStateVector)
    notes:  str = ""


@dataclass
class EmotionResult:
    """Final fused emotion detection result."""
    state:          str                   # dominant affective state
    vector:         AffectiveStateVector  # all scores
    action:         str                   # re-routing action
    xai_reason:     str                   # human-readable explanation
    should_reroute: bool                  # True if action != none
    signals:        list = field(default_factory=list)  # individual signal results


# ─── Signal 1: Text Sentiment Analysis ───────────────────────────────────────

def analyze_text_signal(text: str) -> EmotionSignal:
    """
    Keyword + pattern based sentiment analysis on student text.
    No external NLP model needed — fast, dependency-free.
    """
    if not text:
        return EmotionSignal(source="text")

    text_lower = text.lower().strip()
    scores = AffectiveStateVector()

    def keyword_score(keywords: list, text: str) -> float:
        """Count keyword matches, normalize to 0-1."""
        matches = sum(1 for kw in keywords if kw in text)
        return min(1.0, matches * 0.55)

    # Direct keyword matching
    scores.frustration = keyword_score(FRUSTRATION_KEYWORDS, text_lower)
    scores.boredom     = keyword_score(BOREDOM_KEYWORDS,     text_lower)
    scores.anxiety     = keyword_score(ANXIETY_KEYWORDS,     text_lower)
    scores.confusion   = keyword_score(CONFUSION_KEYWORDS,   text_lower)
    scores.confidence  = keyword_score(CONFIDENCE_KEYWORDS,  text_lower)

    # Boost: multiple exclamation marks / caps → frustration
    if text.count("!") >= 2 or (len(text) > 10 and text == text.upper()):
        scores.frustration = min(1.0, scores.frustration + 0.2)

    # Boost: question marks → confusion
    if text.count("?") >= 2:
        scores.confusion = min(1.0, scores.confusion + 0.15)

    # Very short answers (1-2 words) when a detailed response expected → possible boredom
    word_count = len(text_lower.split())
    if word_count <= 2 and word_count > 0:
        scores.boredom = min(1.0, scores.boredom + 0.15)

    notes = f"Text analysis on {word_count} words"
    return EmotionSignal(source="text", scores=scores, notes=notes)


# ─── Signal 2: Interaction Timing Analysis ───────────────────────────────────

def analyze_timing_signal(response_latency_s: float, avg_latency_s: float = 30.0) -> EmotionSignal:
    """
    Analyze response latency relative to the student's personal average.
    
    Very fast (< 30% of avg) → boredom or impulsive anxiety
    Very slow (> 250% of avg) → disengagement / frustration
    Moderately slow (150-250%) → confusion or anxiety
    Normal → neutral
    """
    scores = AffectiveStateVector()

    if response_latency_s <= 0 or avg_latency_s <= 0:
        return EmotionSignal(source="timing", scores=scores, notes="No timing data")

    ratio = response_latency_s / avg_latency_s

    if ratio < 0.3:
        # Extremely fast — either bored or anxious/impulsive
        scores.boredom  = 0.5
        scores.anxiety  = 0.35
        notes = f"Very fast response ({response_latency_s:.1f}s vs avg {avg_latency_s:.1f}s) — possible boredom or anxiety"

    elif ratio < 0.6:
        # Faster than average — mild boredom signal
        scores.boredom = 0.3
        notes = f"Faster than average ({response_latency_s:.1f}s) — mild boredom signal"

    elif ratio <= 1.5:
        # Normal range
        scores.confidence = 0.3
        notes = f"Normal response time ({response_latency_s:.1f}s)"

    elif ratio <= 2.5:
        # Slow — confusion or anxiety
        scores.confusion = 0.45
        scores.anxiety   = 0.35
        notes = f"Slower than average ({response_latency_s:.1f}s) — possible confusion"

    else:
        # Very slow — possible disengagement / frustration
        scores.frustration = 0.55
        scores.confusion   = 0.35
        notes = f"Very slow response ({response_latency_s:.1f}s) — possible frustration or disengagement"

    return EmotionSignal(source="timing", scores=scores, notes=notes)


# ─── Signal 3: Answer Pattern Analysis ───────────────────────────────────────

def analyze_pattern_signal(recent_results: list) -> EmotionSignal:
    """
    Analyze recent answer correctness patterns.
    
    recent_results: list of bools (True=correct, False=wrong), most recent last.
    Uses last N results (up to 5).
    
    Consecutive wrongs → frustration / confusion
    Consecutive rights → confidence / possible boredom
    Alternating (random) → anxiety / guessing
    """
    scores = AffectiveStateVector()

    if not recent_results:
        return EmotionSignal(source="pattern", scores=scores, notes="No answer history")

    window = recent_results[-5:]  # Use last 5
    n = len(window)
    correct_count = sum(window)
    wrong_count = n - correct_count
    accuracy = correct_count / n if n > 0 else 0.5

    # Count consecutive wrongs at the END of the window
    consec_wrong = 0
    for r in reversed(window):
        if not r:
            consec_wrong += 1
        else:
            break

    # Count consecutive rights at the END of the window
    consec_right = 0
    for r in reversed(window):
        if r:
            consec_right += 1
        else:
            break

    # Detect alternating pattern (guessing: WRCWRC)
    alternating = 0
    for i in range(1, len(window)):
        if window[i] != window[i-1]:
            alternating += 1
    is_alternating = (alternating >= n - 1) and n >= 4

    notes_parts = []

    if consec_wrong >= 3:
        scores.frustration = min(1.0, 0.4 + consec_wrong * 0.12)
        scores.confusion   = min(1.0, 0.3 + consec_wrong * 0.10)
        notes_parts.append(f"{consec_wrong} consecutive wrong answers")

    elif consec_wrong == 2:
        scores.confusion   = 0.45
        scores.frustration = 0.30
        notes_parts.append("2 consecutive wrong answers")

    if consec_right >= 4:
        scores.confidence = min(1.0, 0.5 + consec_right * 0.1)
        scores.boredom    = min(1.0, 0.3 + consec_right * 0.05)
        notes_parts.append(f"{consec_right} consecutive correct answers")

    elif consec_right >= 2:
        scores.confidence = 0.5
        notes_parts.append("Good streak of correct answers")

    if is_alternating:
        scores.anxiety = min(1.0, scores.anxiety + 0.35)
        notes_parts.append("Alternating pattern detected (possible guessing)")

    if accuracy < 0.35 and n >= 4:
        scores.frustration = min(1.0, scores.frustration + 0.2)
        scores.confusion   = min(1.0, scores.confusion   + 0.2)
        notes_parts.append(f"Low accuracy ({accuracy:.0%}) in recent window")

    elif accuracy > 0.85 and n >= 4:
        scores.confidence = min(1.0, scores.confidence + 0.2)
        notes_parts.append(f"High accuracy ({accuracy:.0%}) maintained")

    notes = "; ".join(notes_parts) if notes_parts else f"Normal pattern (accuracy: {accuracy:.0%})"
    return EmotionSignal(source="pattern", scores=scores, notes=notes)


# ─── Fusion: Weighted Ensemble ────────────────────────────────────────────────

def fuse_signals(signals: list) -> AffectiveStateVector:
    """
    Weighted average of all signal scores.
    Weights: text=0.45, timing=0.25, pattern=0.30
    (Text is strongest signal; timing is weakest alone)
    """
    weights = {"text": 0.45, "timing": 0.25, "pattern": 0.30}
    fused = AffectiveStateVector()

    for sig in signals:
        w = weights.get(sig.source, 0.33)
        fused.frustration += sig.scores.frustration * w
        fused.boredom     += sig.scores.boredom     * w
        fused.anxiety     += sig.scores.anxiety     * w
        fused.confusion   += sig.scores.confusion   * w
        fused.confidence  += sig.scores.confidence  * w

    return fused


# ─── Action Mapping ───────────────────────────────────────────────────────────

def get_action(state: str) -> str:
    """Map dominant affective state to re-routing action."""
    return {
        FRUSTRATION: ACTION_SIMPLIFY,
        BOREDOM:     ACTION_ADVANCE,
        ANXIETY:     ACTION_SCAFFOLD,
        CONFUSION:   ACTION_REMEDIATE,
        CONFIDENCE:  ACTION_CHALLENGE,
        NEUTRAL:     ACTION_NONE,
    }.get(state, ACTION_NONE)


def get_xai_reason(state: str, action: str, signals: list, topic: str = "") -> str:
    """
    Generate a human-readable XAI explanation for why the path is being changed.
    This is what gets shown to the student in the UI.
    """
    topic_str = f" while studying **{topic}**" if topic else ""

    signal_notes = [f"*{s.source.capitalize()}*: {s.notes}" for s in signals if s.notes and s.notes != "No timing data" and s.notes != "No answer history"]
    evidence_str = " | ".join(signal_notes) if signal_notes else "multiple signals"

    reasons = {
        FRUSTRATION: (
            f"🔴 **Frustration detected**{topic_str}\n\n"
            f"I noticed signs of difficulty in your responses ({evidence_str}). "
            f"I'm adjusting the content to a simpler level to help you rebuild understanding "
            f"before we continue to harder material."
        ),
        BOREDOM: (
            f"💤 **You seem ready for more challenge**{topic_str}\n\n"
            f"Your responses suggest you've already mastered this content ({evidence_str}). "
            f"I'm advancing to a more challenging level to keep you engaged."
        ),
        ANXIETY: (
            f"😟 **Anxiety or uncertainty detected**{topic_str}\n\n"
            f"I picked up on signs of uncertainty in your responses ({evidence_str}). "
            f"I'm switching to worked examples first so you can build confidence step by step "
            f"before tackling practice questions."
        ),
        CONFUSION: (
            f"❓ **Confusion detected**{topic_str}\n\n"
            f"Your responses suggest you may be missing a prerequisite concept ({evidence_str}). "
            f"I'm re-routing to cover that foundation first so this topic will make more sense."
        ),
        CONFIDENCE: (
            f"⭐ **Strong confidence detected**{topic_str}\n\n"
            f"You're performing excellently ({evidence_str}). "
            f"I'm introducing an application-level challenge to consolidate your learning "
            f"through transfer and deeper thinking."
        ),
        NEUTRAL: (
            f"✅ **Learning session on track**{topic_str}\n\nNo path changes needed — continuing normally."
        ),
    }

    return reasons.get(state, f"Emotion state: {state}. Action: {action}.")


# ─── Main Detection Function ──────────────────────────────────────────────────

def detect_emotion(
    text: str = "",
    response_latency_s: float = 0.0,
    avg_latency_s: float = 30.0,
    recent_results: list = None,
    topic: str = ""
) -> EmotionResult:
    """
    Main entry point. Call this after every 1-3 student interactions.
    
    Args:
        text              : student's latest message/answer text
        response_latency_s: how long the student took to respond (seconds)
        avg_latency_s     : this student's historical average response time
        recent_results    : list of recent bool results [True, False, True, ...]
        topic             : current topic being studied (for XAI explanation)
    
    Returns:
        EmotionResult with state, action, XAI reason, and all signal details
    """
    if recent_results is None:
        recent_results = []

    # Run all three signals
    text_sig    = analyze_text_signal(text)
    timing_sig  = analyze_timing_signal(response_latency_s, avg_latency_s)
    pattern_sig = analyze_pattern_signal(recent_results)

    signals = [text_sig, timing_sig, pattern_sig]

    # Fuse signals
    fused_vector = fuse_signals(signals)

    # Get dominant state
    dominant_state = fused_vector.dominant()

    # Get action and XAI explanation
    action     = get_action(dominant_state)
    xai_reason = get_xai_reason(dominant_state, action, signals, topic)

    return EmotionResult(
        state          = dominant_state,
        vector         = fused_vector,
        action         = action,
        xai_reason     = xai_reason,
        should_reroute = (action != ACTION_NONE),
        signals        = signals
    )


# ─── LLM Prompt Modifier ─────────────────────────────────────────────────────

def get_emotion_prompt_modifier(emotion_result: EmotionResult) -> str:
    """
    Returns an instruction string to inject into LLM prompts
    when emotion-based re-routing is triggered.
    
    Inject this into the system prompt of generate_explanation() 
    and generate_learning_plan() in llm_engine.py.
    """
    if not emotion_result.should_reroute:
        return ""

    modifiers = {
        ACTION_SIMPLIFY: (
            "EMOTION-AWARE INSTRUCTION: The student shows signs of frustration. "
            "Simplify your explanation significantly. Use very basic language, short sentences, "
            "and a single concrete analogy. Be encouraging and supportive. "
            "Do NOT introduce new concepts. Focus on rebuilding confidence."
        ),
        ACTION_ADVANCE: (
            "EMOTION-AWARE INSTRUCTION: The student appears bored — they may already know this material. "
            "Skip basic definitions. Jump directly to advanced applications, edge cases, or challenging problems. "
            "Use technical language appropriate for an expert learner."
        ),
        ACTION_SCAFFOLD: (
            "EMOTION-AWARE INSTRUCTION: The student shows signs of anxiety or low confidence. "
            "Lead with a fully worked example BEFORE asking any questions. "
            "Break every step down explicitly. Use a calm, reassuring tone. "
            "Celebrate small victories."
        ),
        ACTION_REMEDIATE: (
            "EMOTION-AWARE INSTRUCTION: The student appears confused — they may be missing a prerequisite. "
            "Step back to the foundational concept that underpins this topic. "
            "Explain that foundation clearly before returning to the current topic. "
            "Ask a diagnostic question to find the exact gap."
        ),
        ACTION_CHALLENGE: (
            "EMOTION-AWARE INSTRUCTION: The student is highly confident and performing well. "
            "Introduce an advanced application problem or real-world scenario. "
            "Use interleaved practice by mixing this concept with related ones. "
            "Challenge them to explain or teach the concept back."
        ),
    }

    return modifiers.get(emotion_result.action, "")


# ─── Session Tracker ─────────────────────────────────────────────────────────

class EmotionSessionTracker:
    """
    Tracks emotion state across a study/quiz session.
    Maintains rolling window of results and latencies.
    Enforces max 2 re-routes per session to prevent instability.
    """

    MAX_REROUTES = 2
    WINDOW_SIZE  = 3  # Evaluate emotion every N interactions

    def __init__(self):
        self.results:        list  = []   # list of bool (correct/wrong)
        self.latencies:      list  = []   # list of float (response times)
        self.texts:          list  = []   # list of str (student messages)
        self.reroute_count:  int   = 0
        self.last_state:     str   = NEUTRAL
        self.interaction_count: int = 0
        self.emotion_log:    list  = []   # history of EmotionResult objects

    def record(self, text: str = "", latency_s: float = 0.0, correct: bool = None):
        """Record a single student interaction."""
        if text:
            self.texts.append(text)
        if latency_s > 0:
            self.latencies.append(latency_s)
        if correct is not None:
            self.results.append(correct)
        self.interaction_count += 1

    def should_evaluate(self) -> bool:
        """Returns True every WINDOW_SIZE interactions."""
        return self.interaction_count > 0  # evaluate every interaction for live bar updates

    def evaluate(self, topic: str = "") -> Optional[EmotionResult]:
        """
        Run emotion detection on current session data.
        Returns EmotionResult if re-routing is warranted, else None.
        """
        # Get most recent text
        latest_text = self.texts[-1] if self.texts else ""

        # Average latency for this student (session baseline)
        avg_latency = (sum(self.latencies) / len(self.latencies)) if self.latencies else 30.0
        latest_latency = self.latencies[-1] if self.latencies else 0.0

        result = detect_emotion(
            text               = latest_text,
            response_latency_s = latest_latency,
            avg_latency_s      = avg_latency,
            recent_results     = self.results,
            topic              = topic
        )

        self.last_state = result.state
        self.emotion_log.append(result)

        # Enforce max re-routes
        if result.should_reroute:
            if self.reroute_count >= self.MAX_REROUTES:
                result.should_reroute = False
                result.action         = ACTION_NONE
                result.xai_reason     = (
                    f"ℹ️ Emotion detected ({result.state}) but max re-routes "
                    f"({self.MAX_REROUTES}) reached for this session. Continuing normally."
                )
            else:
                self.reroute_count += 1

        return result

    def get_session_summary(self) -> dict:
        """Return a summary of emotion states during this session."""
        if not self.emotion_log:
            return {"states": [], "reroutes": 0, "dominant_overall": NEUTRAL}

        state_counts = {}
        for r in self.emotion_log:
            state_counts[r.state] = state_counts.get(r.state, 0) + 1

        dominant = max(state_counts, key=state_counts.get)
        return {
            "states":           state_counts,
            "reroutes":         self.reroute_count,
            "dominant_overall": dominant,
            "total_interactions": self.interaction_count
        }

    def reset(self):
        """Reset for a new session."""
        self.__init__()