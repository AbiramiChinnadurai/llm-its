# emotion/__init__.py
from emotion.emotion_engine import (
    detect_emotion,
    EmotionSessionTracker,
    EmotionResult,
    AffectiveStateVector,
    get_emotion_prompt_modifier,
    FRUSTRATION, BOREDOM, ANXIETY, CONFUSION, CONFIDENCE, NEUTRAL,
    ACTION_SIMPLIFY, ACTION_ADVANCE, ACTION_SCAFFOLD,
    ACTION_REMEDIATE, ACTION_CHALLENGE, ACTION_NONE,
)
from emotion.emotion_widget import (
    get_tracker, reset_tracker,
    render_emotion_sidebar,
    render_reroute_banner,
    render_emotion_chip,
    render_session_emotion_summary,
)
