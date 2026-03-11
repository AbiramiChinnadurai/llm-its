"""
emotion/emotion_widget.py
Premium Emotion Monitor UI — unique radial gauge + animated bars design.
All styles fully inlined (no CSS classes) for Streamlit sidebar compatibility.
"""

import streamlit as st
from emotion.emotion_engine import (
    EmotionSessionTracker, EmotionResult,
    FRUSTRATION, BOREDOM, ANXIETY, CONFUSION, CONFIDENCE, NEUTRAL,
    ACTION_SIMPLIFY, ACTION_ADVANCE, ACTION_SCAFFOLD,
    ACTION_REMEDIATE, ACTION_CHALLENGE, ACTION_NONE
)

EMOTION_CONFIG = {
    FRUSTRATION: {
        "icon": "🔴", "emoji": "😤", "label": "Frustrated",
        "color": "#ef4444", "bg": "#1c0808", "border": "#7f1d1d",
        "gradient": "linear-gradient(135deg,#ef4444,#b91c1c)",
        "action_label": "Simplifying content to reduce difficulty",
        "tip": "Take a breath — I'll slow things down."
    },
    BOREDOM: {
        "icon": "💤", "emoji": "😴", "label": "Bored",
        "color": "#a78bfa", "bg": "#1a0d2e", "border": "#6d28d9",
        "gradient": "linear-gradient(135deg,#a78bfa,#7c3aed)",
        "action_label": "Advancing to a more challenging level",
        "tip": "Let's kick it up a notch!"
    },
    ANXIETY: {
        "icon": "😟", "emoji": "😰", "label": "Anxious",
        "color": "#f59e0b", "bg": "#1c1005", "border": "#92400e",
        "gradient": "linear-gradient(135deg,#f59e0b,#d97706)",
        "action_label": "Switching to worked examples first",
        "tip": "I'll guide you step by step."
    },
    CONFUSION: {
        "icon": "❓", "emoji": "😵", "label": "Confused",
        "color": "#38bdf8", "bg": "#0c1a24", "border": "#0369a1",
        "gradient": "linear-gradient(135deg,#38bdf8,#0284c7)",
        "action_label": "Re-routing to prerequisite concept",
        "tip": "Let's go back to basics first."
    },
    CONFIDENCE: {
        "icon": "⭐", "emoji": "😎", "label": "Confident",
        "color": "#34d399", "bg": "#081810", "border": "#065f35",
        "gradient": "linear-gradient(135deg,#34d399,#059669)",
        "action_label": "Introducing an advanced challenge",
        "tip": "You're on fire — time to level up!"
    },
    NEUTRAL: {
        "icon": "✅", "emoji": "🙂", "label": "Focused",
        "color": "#94a3b8", "bg": "#0d1120", "border": "#1e2d40",
        "gradient": "linear-gradient(135deg,#94a3b8,#64748b)",
        "action_label": "Continuing normally",
        "tip": "Steady progress — keep going."
    },
}

EMOTION_ORDER = [
    ("Frustration", "frustration", "#ef4444"),
    ("Boredom",     "boredom",     "#a78bfa"),
    ("Anxiety",     "anxiety",     "#f59e0b"),
    ("Confusion",   "confusion",   "#38bdf8"),
    ("Confidence",  "confidence",  "#34d399"),
]


# ─── Helper: SVG Arc for radial gauge ────────────────────────────────────────

def _arc_path(pct: float, r: int = 28) -> str:
    """Generate SVG arc path for a percentage fill (0-100) on a circle."""
    import math
    pct = max(0.0, min(1.0, pct))
    angle = pct * 2 * math.pi - math.pi / 2  # start from top
    x = 32 + r * math.cos(-math.pi / 2)
    y = 32 + r * math.sin(-math.pi / 2)
    ex = 32 + r * math.cos(angle - math.pi / 2 + math.pi / 2)
    ey = 32 + r * math.sin(angle - math.pi / 2 + math.pi / 2)

    # Use proper arc calculation
    start_angle = -math.pi / 2
    end_angle   = start_angle + pct * 2 * math.pi
    sx = 32 + r * math.cos(start_angle)
    sy = 32 + r * math.sin(start_angle)
    ex2 = 32 + r * math.cos(end_angle)
    ey2 = 32 + r * math.sin(end_angle)
    large = 1 if pct > 0.5 else 0
    if pct >= 0.999:
        return f"M {sx:.1f} {sy:.1f} A {r} {r} 0 1 1 {sx-0.01:.2f} {sy:.1f}"
    return f"M {sx:.1f} {sy:.1f} A {r} {r} 0 {large} 1 {ex2:.1f} {ey2:.1f}"


def _radial_gauge(pct: float, color: str, emoji: str, label: str) -> str:
    """Build a mini SVG radial gauge showing dominant emotion."""
    arc = _arc_path(pct / 100)
    return f"""
<svg width="64" height="64" viewBox="0 0 64 64" style="display:block;">
  <circle cx="32" cy="32" r="28" fill="none" stroke="#1a2540" stroke-width="5"/>
  <path d="{arc}" fill="none" stroke="{color}" stroke-width="5"
        stroke-linecap="round" style="filter:drop-shadow(0 0 4px {color}88);"/>
  <text x="32" y="29" text-anchor="middle" font-size="16" dominant-baseline="middle">{emoji}</text>
  <text x="32" y="46" text-anchor="middle" font-size="8" fill="{color}" font-weight="700">{pct}%</text>
</svg>"""


# ─── Widget 1: Premium Emotion Monitor (Sidebar) ─────────────────────────────

def render_emotion_sidebar(tracker: EmotionSessionTracker):
    """
    Premium sidebar emotion monitor with:
    - Central radial gauge showing dominant emotion
    - Segmented horizontal bars per emotion
    - Glowing dominant bar
    - State label + tip
    """

    # ── IDLE STATE (no interactions yet) ─────────────────────────────────────
    if not tracker.emotion_log:
        idle_bars = ""
        for label, _, color in EMOTION_ORDER:
            idle_bars += f"""
<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
  <span style="width:68px;font-size:0.69rem;color:#2a3a50;text-align:right;flex-shrink:0;letter-spacing:0.02em;">{label}</span>
  <div style="flex:1;height:6px;background:#0d1a28;border-radius:4px;border:1px solid #1a2540;"></div>
  <span style="width:26px;font-size:0.67rem;color:#1e2d3d;text-align:right;flex-shrink:0;">—</span>
</div>"""

        st.markdown(f"""
<div style="background:linear-gradient(160deg,#0d1524 0%,#080c14 100%);
            border:1px solid #1a2540;border-radius:16px;
            padding:16px 14px;margin-bottom:6px;position:relative;overflow:hidden;">

  <!-- Watermark -->
  <div style="position:absolute;right:-8px;top:50%;transform:translateY(-50%) rotate(-90deg);
              font-size:3.5rem;font-weight:900;color:rgba(255,255,255,0.018);
              letter-spacing:0.2em;pointer-events:none;user-select:none;white-space:nowrap;">
    AFFECT
  </div>

  <!-- Header -->
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
    <div style="width:6px;height:6px;border-radius:50%;background:#3b82f6;
                box-shadow:0 0 8px #3b82f688;flex-shrink:0;"></div>
    <span style="font-size:0.67rem;font-weight:800;text-transform:uppercase;
                 letter-spacing:0.15em;color:#3b82f6;">Emotion Monitor</span>
  </div>

  <!-- Idle gauge placeholder -->
  <div style="display:flex;justify-content:center;margin-bottom:14px;">
    <div style="width:64px;height:64px;border-radius:50%;
                border:5px solid #0d1a28;background:#080c14;
                display:flex;align-items:center;justify-content:center;
                font-size:1.6rem;">🧠</div>
  </div>

  {idle_bars}

  <div style="margin-top:10px;text-align:center;font-size:0.69rem;
              color:#1e3050;letter-spacing:0.05em;">
    ● awaiting first message
  </div>
</div>
""", unsafe_allow_html=True)
        return

    # ── ACTIVE STATE ─────────────────────────────────────────────────────────
    latest = tracker.emotion_log[-1]
    v      = latest.vector
    cfg    = EMOTION_CONFIG.get(latest.state, EMOTION_CONFIG[NEUTRAL])
    reroutes_left = tracker.MAX_REROUTES - tracker.reroute_count

    # Dominant score for gauge
    dom_score = round(getattr(v, latest.state, 0) * 100) if latest.state != NEUTRAL else 0
    gauge_svg = _radial_gauge(dom_score, cfg["color"], cfg["emoji"], cfg["label"])

    # Build bars
    bars_html = ""
    for label, key, color in EMOTION_ORDER:
        score  = getattr(v, key)
        pct    = round(score * 100)
        is_dom = (key == latest.state)

        if is_dom and pct > 0:
            bar_inner = f"""
<div style="position:relative;flex:1;height:{'11px' if is_dom else '7px'};
            background:#0d1a28;border-radius:4px;overflow:hidden;
            border:1px solid {color}44;">
  <div style="position:absolute;inset:0;width:{pct}%;
              background:{cfg['gradient'] if is_dom else color};
              border-radius:4px;
              box-shadow:0 0 10px {color}99,0 0 20px {color}44;">
  </div>
  <div style="position:absolute;right:4px;top:50%;transform:translateY(-50%);
              font-size:0.6rem;font-weight:800;color:#fff;line-height:1;">{pct}%</div>
</div>"""
            label_color = "#f0f6ff"
            label_weight = "800"
            row_margin = "margin-bottom:8px;"
        else:
            bar_inner = f"""
<div style="flex:1;height:7px;background:#0d1a28;border-radius:4px;
            overflow:hidden;border:1px solid #1a2540;">
  <div style="width:{pct}%;height:100%;background:{color};
              border-radius:4px;opacity:{'0.9' if pct > 0 else '0.3'};"></div>
</div>"""
            label_color = "#3a5070"
            label_weight = "400"
            row_margin = "margin-bottom:6px;"

        bars_html += f"""
<div style="display:flex;align-items:center;gap:6px;{row_margin}">
  <span style="width:68px;font-size:0.69rem;color:{label_color};
               font-weight:{label_weight};text-align:right;flex-shrink:0;
               letter-spacing:0.02em;">{label}</span>
  {bar_inner}
</div>"""

    # Re-route indicator dots
    route_dots = ""
    for i in range(tracker.MAX_REROUTES):
        used  = i < tracker.reroute_count
        color = "#ef4444" if used else "#1a2540"
        glow  = f"box-shadow:0 0 6px #ef444488;" if used else ""
        route_dots += f'<div style="width:8px;height:8px;border-radius:50%;background:{color};{glow}"></div>'

    st.markdown(f"""
<div style="background:linear-gradient(160deg,#0d1524 0%,#080c14 100%);
            border:1px solid {cfg['border']};border-radius:16px;
            padding:16px 14px;margin-bottom:6px;position:relative;overflow:hidden;">

  <!-- Glow top edge -->
  <div style="position:absolute;top:0;left:0;right:0;height:2px;
              background:{cfg['gradient']};border-radius:16px 16px 0 0;"></div>

  <!-- Watermark -->
  <div style="position:absolute;right:-8px;top:50%;transform:translateY(-50%) rotate(-90deg);
              font-size:3.5rem;font-weight:900;color:rgba(255,255,255,0.022);
              letter-spacing:0.2em;pointer-events:none;user-select:none;white-space:nowrap;">
    AFFECT
  </div>

  <!-- Header row -->
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
    <div style="display:flex;align-items:center;gap:7px;">
      <div style="width:6px;height:6px;border-radius:50%;background:{cfg['color']};
                  box-shadow:0 0 8px {cfg['color']}88;flex-shrink:0;"></div>
      <span style="font-size:0.67rem;font-weight:800;text-transform:uppercase;
                   letter-spacing:0.15em;color:{cfg['color']};">Emotion Monitor</span>
    </div>
    <span style="font-size:0.67rem;color:#2a3a50;font-weight:500;">
      #{tracker.interaction_count}
    </span>
  </div>

  <!-- Gauge + State label -->
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
    <div style="flex-shrink:0;">{gauge_svg}</div>
    <div style="flex:1;">
      <div style="font-size:1.05rem;font-weight:800;color:{cfg['color']};
                  letter-spacing:-0.02em;line-height:1.1;margin-bottom:4px;">
        {cfg['emoji']} {cfg['label']}
      </div>
      <div style="font-size:0.71rem;color:#4a6080;line-height:1.4;font-style:italic;">
        "{cfg['tip']}"
      </div>
    </div>
  </div>

  <!-- Bars -->
  {bars_html}

  <!-- Footer: re-route dots + count -->
  <div style="margin-top:10px;padding-top:8px;border-top:1px solid #0d1a28;
              display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;gap:5px;">
      <span style="font-size:0.64rem;color:#2a3a50;margin-right:2px;">RE-ROUTES</span>
      {route_dots}
    </div>
    <span style="font-size:0.64rem;color:#2a3a50;">{reroutes_left} remaining</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Widget 2: Re-routing Banner ─────────────────────────────────────────────

def render_reroute_banner(result: EmotionResult):
    """Full-width re-routing banner with gradient top border and XAI explanation."""
    if not result.should_reroute:
        return

    cfg = EMOTION_CONFIG.get(result.state, EMOTION_CONFIG[NEUTRAL])
    import re as _re
    reason = _re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#e2e8f0;">\1</strong>', result.xai_reason)
    reason = reason.replace('\n\n', '<br><br>').replace('\n', '<br>')
    # Strip the first line (it's the header) to avoid duplication
    lines = result.xai_reason.strip().split('\n')
    body_text = '\n'.join(lines[2:]) if len(lines) > 2 else result.xai_reason
    body_text = _re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#e2e8f0;">\1</strong>', body_text)
    body_text = body_text.replace('\n\n', '<br><br>').replace('\n', '<br>')

    st.markdown(f"""
<div style="position:relative;background:{cfg['bg']};
            border:1px solid {cfg['border']};border-radius:14px;
            padding:16px 20px;margin:14px 0;overflow:hidden;">

  <!-- Left accent bar -->
  <div style="position:absolute;left:0;top:0;bottom:0;width:4px;
              background:{cfg['gradient']};border-radius:14px 0 0 14px;"></div>

  <!-- Top shimmer line -->
  <div style="position:absolute;top:0;left:4px;right:0;height:1px;
              background:linear-gradient(90deg,{cfg['color']}88,transparent);"></div>

  <div style="padding-left:8px;">
    <!-- Icon + title -->
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
      <div style="width:32px;height:32px;border-radius:10px;
                  background:{cfg['gradient']};display:flex;align-items:center;
                  justify-content:center;font-size:1.1rem;flex-shrink:0;
                  box-shadow:0 4px 12px {cfg['color']}44;">
        {cfg['emoji']}
      </div>
      <div>
        <div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.15em;color:{cfg['color']};margin-bottom:2px;">
          ↻ Path Adjusted
        </div>
        <div style="font-size:0.95rem;font-weight:700;color:#f0f6ff;">
          {cfg['label']} detected
        </div>
      </div>
    </div>

    <!-- Body text -->
    <div style="font-size:0.83rem;line-height:1.7;color:#8090a8;margin-bottom:12px;">
      {body_text}
    </div>

    <!-- Action pill -->
    <div style="display:inline-flex;align-items:center;gap:6px;
                background:{cfg['bg']};border:1px solid {cfg['border']};
                border-radius:20px;padding:5px 14px;">
      <div style="width:6px;height:6px;border-radius:50%;
                  background:{cfg['color']};box-shadow:0 0 6px {cfg['color']};"></div>
      <span style="font-size:0.72rem;font-weight:600;color:{cfg['color']};
                   letter-spacing:0.05em;text-transform:uppercase;">
        {cfg['action_label']}
      </span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Widget 3: Emotion Chip ───────────────────────────────────────────────────

def render_emotion_chip(state: str):
    """Inline pill chip showing emotion state after each AI response."""
    cfg = EMOTION_CONFIG.get(state, EMOTION_CONFIG[NEUTRAL])
    st.markdown(f"""
<span style="display:inline-flex;align-items:center;gap:5px;
             background:{cfg['bg']};border:1px solid {cfg['border']};
             border-radius:20px;padding:3px 10px 3px 8px;">
  <span style="width:7px;height:7px;border-radius:50%;flex-shrink:0;
               background:{cfg['color']};box-shadow:0 0 5px {cfg['color']}88;"></span>
  <span style="font-size:0.72rem;font-weight:600;color:{cfg['color']};">
    {cfg['emoji']} {cfg['label']}
  </span>
</span>
""", unsafe_allow_html=True)


# ─── Widget 4: Session Summary ───────────────────────────────────────────────

def render_session_emotion_summary(tracker: EmotionSessionTracker):
    """End-of-session emotion journey card shown in Session History expander."""
    summary = tracker.get_session_summary()
    if not summary["states"]:
        return

    rows = ""
    for state, count in sorted(summary["states"].items(), key=lambda x: -x[1]):
        cfg  = EMOTION_CONFIG.get(state, EMOTION_CONFIG[NEUTRAL])
        fill = min(100, count * 30)
        rows += f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
  <div style="width:28px;height:28px;border-radius:8px;
              background:{cfg['bg']};border:1px solid {cfg['border']};
              display:flex;align-items:center;justify-content:center;
              font-size:0.9rem;flex-shrink:0;">{cfg['emoji']}</div>
  <div style="flex:1;">
    <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
      <span style="font-size:0.75rem;color:{cfg['color']};font-weight:600;">{cfg['label']}</span>
      <span style="font-size:0.7rem;color:#4a6080;">{count}×</span>
    </div>
    <div style="height:5px;background:#0d1a28;border-radius:3px;overflow:hidden;border:1px solid #1a2540;">
      <div style="width:{fill}%;height:100%;background:{cfg['gradient']};border-radius:3px;"></div>
    </div>
  </div>
</div>"""

    dom_cfg = EMOTION_CONFIG.get(summary["dominant_overall"], EMOTION_CONFIG[NEUTRAL])

    st.markdown(f"""
<div style="background:linear-gradient(160deg,#0d1524,#080c14);
            border:1px solid #1a2540;border-radius:14px;
            padding:16px;margin-top:12px;position:relative;overflow:hidden;">

  <div style="position:absolute;top:0;left:0;right:0;height:2px;
              background:{dom_cfg['gradient']};border-radius:14px 14px 0 0;"></div>

  <div style="font-size:0.67rem;font-weight:800;text-transform:uppercase;
              letter-spacing:0.15em;color:{dom_cfg['color']};margin-bottom:14px;">
    🧠 Emotion Journey
  </div>

  {rows}

  <div style="margin-top:12px;padding-top:10px;border-top:1px solid #0d1a28;
              display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="font-size:1rem;">{dom_cfg['emoji']}</span>
      <span style="font-size:0.75rem;color:{dom_cfg['color']};font-weight:700;">
        {dom_cfg['label']} session
      </span>
    </div>
    <span style="font-size:0.7rem;color:#2a3a50;">
      {summary['reroutes']} re-route{"s" if summary["reroutes"] != 1 else ""} triggered
    </span>
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_tracker(session_key: str = "emotion_tracker") -> EmotionSessionTracker:
    if session_key not in st.session_state:
        st.session_state[session_key] = EmotionSessionTracker()
    return st.session_state[session_key]


def reset_tracker(session_key: str = "emotion_tracker"):
    st.session_state[session_key] = EmotionSessionTracker()