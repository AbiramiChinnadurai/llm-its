"""
xai/xai_widget.py
─────────────────────────────────────────────────────────────────────────────
Premium XAI UI components — fully inlined styles for Streamlit compatibility.
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
from xai.xai_engine import XAIExplanation, CounterfactualExplanation


# ─── Source badge config ──────────────────────────────────────────────────────

SOURCE_CONFIG = {
    "kg":      {"icon": "🕸️", "label": "KG Trace",    "color": "#34d399", "bg": "#081810", "border": "#065f35"},
    "mastery": {"icon": "📊", "label": "Performance",  "color": "#60a5fa", "bg": "#0d1a2e", "border": "#1d4ed8"},
    "emotion": {"icon": "🧠", "label": "Affective",    "color": "#f59e0b", "bg": "#1c1005", "border": "#92400e"},
    "llm":     {"icon": "⚡", "label": "CoT Reasoning","color": "#a78bfa", "bg": "#1a0d2e", "border": "#6d28d9"},
    "combined":{"icon": "✦",  "label": "Multi-source", "color": "#38bdf8", "bg": "#0c1a24", "border": "#0369a1"},
}

DIFFICULTY_CONFIG = {
    1: {"label": "Foundational", "color": "#34d399", "dots": "●○○○○"},
    2: {"label": "Conceptual",   "color": "#60a5fa", "dots": "●●○○○"},
    3: {"label": "Applied",      "color": "#f59e0b", "dots": "●●●○○"},
    4: {"label": "Advanced",     "color": "#ef4444", "dots": "●●●●○"},
    5: {"label": "Expert",       "color": "#a78bfa", "dots": "●●●●●"},
}


def _md_to_html(text: str) -> str:
    """Convert **bold** markdown to HTML strong tags."""
    import re
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#e2e8f0;">\1</strong>', text)
    return text.replace('\n\n', '<br><br>').replace('\n', '<br>')


# ─── Widget 1: Full XAI Explanation Panel ────────────────────────────────────

def render_xai_panel(xai: XAIExplanation):
    """
    Full expandable XAI explanation panel shown below each AI response.
    Contains all 5 explanation fields + source badges + progress trace.
    """
    diff_cfg = DIFFICULTY_CONFIG.get(xai.difficulty, DIFFICULTY_CONFIG[2])
    conf_pct = round(xai.confidence * 100)
    conf_color = "#34d399" if conf_pct >= 75 else "#f59e0b" if conf_pct >= 50 else "#ef4444"

    # Source badges
    badges_html = ""
    for src in xai.sources_used:
        cfg = SOURCE_CONFIG.get(src, SOURCE_CONFIG["kg"])
        badges_html += f"""
<span style="display:inline-flex;align-items:center;gap:4px;
             background:{cfg['bg']};border:1px solid {cfg['border']};
             border-radius:20px;padding:2px 9px;font-size:0.67rem;
             font-weight:600;color:{cfg['color']};margin-right:5px;">
  {cfg['icon']} {cfg['label']}
</span>"""

    with st.expander("✦ Why am I learning this? — XAI Explanation", expanded=False):

        # Header row
        st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #1a2540;">
  <div>
    <div style="font-size:0.67rem;font-weight:800;text-transform:uppercase;
                letter-spacing:0.15em;color:#3b82f6;margin-bottom:4px;">
      ✦ XAI — Path Decision Explained
    </div>
    <div style="font-size:1rem;font-weight:700;color:#f0f6ff;">{xai.topic}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:1.3rem;font-weight:800;color:{conf_color};">{conf_pct}%</div>
    <div style="font-size:0.62rem;color:#3a5070;text-transform:uppercase;letter-spacing:0.1em;">Confidence</div>
  </div>
</div>
<div style="margin-bottom:14px;">{badges_html}</div>
""", unsafe_allow_html=True)

        # Progress trace
        st.markdown(f"""
<div style="background:#080c14;border:1px solid #1a2540;border-radius:10px;
            padding:10px 14px;margin-bottom:14px;">
  <div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.12em;color:#3a5070;margin-bottom:6px;">
    📍 Your Position in the Learning Chain
  </div>
  <div style="font-size:0.8rem;color:#8090a8;line-height:1.6;font-family:monospace;">
    {xai.progress_trace}
  </div>
</div>
""", unsafe_allow_html=True)

        # 4 explanation cards in 2x2 grid
        col1, col2 = st.columns(2)

        with col1:
            _xai_card("🕸️ Why this topic?",   xai.why_this_topic,   "#3b82f6", "#0d1a2e", "#1d4ed8")
            _xai_card("⚡ Difficulty level",   xai.difficulty_note,  diff_cfg["color"], "#0d1120", "#1a2540")

        with col2:
            _xai_card("📊 Why now?",           xai.why_now,          "#10b981", "#081810", "#065f35")
            _xai_card("🔄 If you struggle",    xai.what_if_struggle, "#f59e0b", "#1c1005", "#92400e")

        # CoT reasoning (only if generated)
        if xai.cot_reasoning:
            st.markdown(f"""
<div style="background:#1a0d2e;border:1px solid #6d28d9;border-radius:10px;
            padding:12px 14px;margin-top:8px;">
  <div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.12em;color:#a78bfa;margin-bottom:6px;">
    ⚡ AI Chain-of-Thought Reasoning
  </div>
  <div style="font-size:0.8rem;color:#c4b5fd;line-height:1.6;font-style:italic;">
    "{xai.cot_reasoning}"
  </div>
</div>
""", unsafe_allow_html=True)

        # Difficulty visual bar
        diff_fill = xai.difficulty * 20
        st.markdown(f"""
<div style="margin-top:12px;padding-top:10px;border-top:1px solid #0d1a28;">
  <div style="display:flex;align-items:center;gap:10px;">
    <span style="font-size:0.68rem;color:#3a5070;width:70px;flex-shrink:0;">Difficulty</span>
    <div style="flex:1;height:6px;background:#0d1a28;border-radius:4px;overflow:hidden;">
      <div style="width:{diff_fill}%;height:100%;
                  background:linear-gradient(90deg,#34d399,{diff_cfg['color']});
                  border-radius:4px;"></div>
    </div>
    <span style="font-size:0.72rem;font-weight:700;color:{diff_cfg['color']};
                 width:80px;text-align:right;">{diff_cfg['dots']} {diff_cfg['label']}</span>
  </div>
</div>
""", unsafe_allow_html=True)


def _xai_card(title: str, body: str, color: str, bg: str, border: str):
    """Render a single XAI explanation card."""
    st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:10px;
            padding:12px 13px;margin-bottom:8px;height:100%;">
  <div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.12em;color:{color};margin-bottom:7px;">{title}</div>
  <div style="font-size:0.78rem;color:#8090a8;line-height:1.65;">
    {_md_to_html(body)}
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Widget 2: Compact XAI Strip (inline, after response) ────────────────────

def render_xai_strip(xai: XAIExplanation):
    """
    A single-line compact XAI strip shown inline after each response.
    Shows: difficulty pill + confidence + dominant source + progress position.
    Clicking expands to full panel (handled by render_xai_panel).
    """
    diff_cfg   = DIFFICULTY_CONFIG.get(xai.difficulty, DIFFICULTY_CONFIG[2])
    conf_pct   = round(xai.confidence * 100)
    conf_color = "#34d399" if conf_pct >= 75 else "#f59e0b" if conf_pct >= 50 else "#ef4444"

    # Show only first source badge
    primary_src = xai.sources_used[0] if xai.sources_used else "kg"
    src_cfg     = SOURCE_CONFIG.get(primary_src, SOURCE_CONFIG["kg"])

    # Position in chain: count ✓ vs ▶ vs ○
    chain_parts  = xai.progress_trace.split(" → ")
    done_count   = sum(1 for p in chain_parts if p.startswith("✓"))
    total_count  = len(chain_parts)

    st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;
            padding:6px 0;border-top:1px solid #0d1a28;margin-top:8px;">

  <span style="font-size:0.67rem;font-weight:700;text-transform:uppercase;
               letter-spacing:0.1em;color:#2a3a50;">✦ XAI</span>

  <span style="display:inline-flex;align-items:center;gap:4px;
               background:{diff_cfg['color']}18;border:1px solid {diff_cfg['color']}44;
               border-radius:20px;padding:2px 9px;font-size:0.68rem;
               font-weight:600;color:{diff_cfg['color']};">
    {diff_cfg['dots']} {diff_cfg['label']}
  </span>

  <span style="display:inline-flex;align-items:center;gap:4px;
               background:{src_cfg['bg']};border:1px solid {src_cfg['border']};
               border-radius:20px;padding:2px 9px;font-size:0.68rem;
               font-weight:600;color:{src_cfg['color']};">
    {src_cfg['icon']} {src_cfg['label']}
  </span>

  <span style="font-size:0.68rem;color:{conf_color};font-weight:700;">
    {conf_pct}% confidence
  </span>

  <span style="font-size:0.68rem;color:#2a3a50;margin-left:auto;">
    Step {done_count + 1} of {total_count}
  </span>

</div>
""", unsafe_allow_html=True)


# ─── Widget 3: Counterfactual Explanation Panel ───────────────────────────────

def render_counterfactual(cf: CounterfactualExplanation):
    """Show why a rejected topic was not recommended."""
    prereq_html = ""
    if cf.missing_prereqs:
        prereq_html = f"""
<div style="margin-top:8px;">
  <span style="font-size:0.68rem;color:#4a6080;">Missing prerequisites: </span>
  {''.join(f'<span style="display:inline-block;background:#1c0808;border:1px solid #7f1d1d;border-radius:6px;padding:2px 8px;font-size:0.68rem;color:#f87171;margin:2px;">{p}</span>' for p in cf.missing_prereqs)}
</div>"""

    st.markdown(f"""
<div style="background:#0c1a24;border:1px solid #0369a1;border-radius:12px;
            padding:14px 16px;margin:8px 0;">
  <div style="font-size:0.67rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.12em;color:#38bdf8;margin-bottom:8px;">
    ❓ Why not "{cf.rejected_topic}"?
  </div>
  <div style="font-size:0.82rem;color:#8090a8;line-height:1.65;">
    {_md_to_html(cf.reason)}
  </div>
  {prereq_html}
</div>
""", unsafe_allow_html=True)


# ─── Widget 4: XAI Summary for Learning Plan ─────────────────────────────────

def render_plan_xai_card(day_num: int, topic: str, subject: str,
                          rationale: str, difficulty: int):
    """
    Compact XAI card shown on each roadmap day node.
    Explains why this topic was scheduled on this day.
    """
    diff_cfg = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG[2])

    st.markdown(f"""
<div style="background:#0a0f1a;border:1px solid #1a2540;border-left:3px solid #3b82f6;
            border-radius:10px;padding:10px 14px;margin:6px 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <span style="font-size:0.62rem;font-weight:700;text-transform:uppercase;
                 letter-spacing:0.1em;color:#3b82f6;">✦ Why Day {day_num}?</span>
    <span style="font-size:0.68rem;font-weight:600;color:{diff_cfg['color']};">
      {diff_cfg['dots']} {diff_cfg['label']}
    </span>
  </div>
  <div style="font-size:0.78rem;color:#6b7a99;line-height:1.6;">
    {_md_to_html(rationale)}
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Widget 5: XAI Sidebar Summary ───────────────────────────────────────────

def render_xai_sidebar(xai: XAIExplanation):
    """
    Compact XAI status in the sidebar showing current explanation confidence
    and dominant reasoning source.
    """
    if not xai:
        st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:12px;
            padding:12px 14px;margin-bottom:8px;">
  <div style="font-size:0.67rem;font-weight:800;text-transform:uppercase;
              letter-spacing:0.15em;color:#3b82f6;margin-bottom:8px;">
    ✦ XAI Explainer
  </div>
  <div style="font-size:0.72rem;color:#2a3a50;">
    Select a topic to see explanations
  </div>
</div>""", unsafe_allow_html=True)
        return

    diff_cfg   = DIFFICULTY_CONFIG.get(xai.difficulty, DIFFICULTY_CONFIG[2])
    conf_pct   = round(xai.confidence * 100)
    conf_color = "#34d399" if conf_pct >= 75 else "#f59e0b" if conf_pct >= 50 else "#ef4444"
    conf_fill  = conf_pct

    sources_badges = ""
    for src in xai.sources_used:
        cfg = SOURCE_CONFIG.get(src, SOURCE_CONFIG["kg"])
        sources_badges += f"""
<span style="display:inline-flex;align-items:center;gap:3px;
             background:{cfg['bg']};border:1px solid {cfg['border']};
             border-radius:12px;padding:1px 7px;font-size:0.62rem;
             color:{cfg['color']};margin:2px;">{cfg['icon']} {cfg['label']}</span>"""

    st.markdown(f"""
<div style="background:linear-gradient(160deg,#0d1524,#080c14);
            border:1px solid #1a2540;border-radius:14px;
            padding:14px 14px;margin-bottom:8px;position:relative;overflow:hidden;">

  <div style="position:absolute;top:0;left:0;right:0;height:2px;
              background:linear-gradient(90deg,#3b82f6,#8b5cf6);
              border-radius:14px 14px 0 0;"></div>

  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <span style="font-size:0.67rem;font-weight:800;text-transform:uppercase;
                 letter-spacing:0.15em;color:#3b82f6;">✦ XAI Explainer</span>
    <span style="font-size:0.78rem;font-weight:800;color:{conf_color};">{conf_pct}%</span>
  </div>

  <!-- Confidence bar -->
  <div style="height:5px;background:#0d1a28;border-radius:3px;
              overflow:hidden;margin-bottom:10px;">
    <div style="width:{conf_fill}%;height:100%;
                background:linear-gradient(90deg,#3b82f6,{conf_color});
                border-radius:3px;"></div>
  </div>

  <!-- Difficulty -->
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
    <span style="font-size:0.68rem;color:{diff_cfg['color']};font-weight:600;">
      {diff_cfg['dots']}
    </span>
    <span style="font-size:0.7rem;color:#4a6080;">{diff_cfg['label']}</span>
  </div>

  <!-- Sources -->
  <div style="margin-bottom:4px;font-size:0.62rem;color:#2a3a50;
              text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">
    Sources
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:2px;">
    {sources_badges}
  </div>
</div>
""", unsafe_allow_html=True)
