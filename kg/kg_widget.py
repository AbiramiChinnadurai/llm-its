"""
kg/kg_widget.py
─────────────────────────────────────────────────────────────────────────────
Streamlit UI components for the Knowledge Graph system.
All styles fully inlined for Streamlit sidebar compatibility.
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
from kg.kg_engine import KnowledgeGraph, build_kg_context


# ─── Widget 1: KG Status Badge (sidebar) ─────────────────────────────────────

def render_kg_status(kg: KnowledgeGraph, subject: str):
    """Show KG stats in sidebar — node count, edge count, status."""
    if kg is None:
        st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:12px;
            padding:12px 14px;margin-bottom:8px;">
  <div style="font-size:0.67rem;font-weight:800;text-transform:uppercase;
              letter-spacing:0.15em;color:#4a6080;margin-bottom:8px;">
    🕸️ Knowledge Graph
  </div>
  <div style="font-size:0.75rem;color:#2a3a50;">
    Not built yet for <strong style="color:#4a6080;">{subject}</strong>
  </div>
  <div style="font-size:0.68rem;color:#1e2d3d;margin-top:4px;">
    Go to Upload Syllabus → Build KG
  </div>
</div>""", unsafe_allow_html=True)
        return

    stats = kg.stats()
    st.markdown(f"""
<div style="background:linear-gradient(160deg,#0d1524,#080c14);
            border:1px solid #065f35;border-radius:12px;
            padding:12px 14px;margin-bottom:8px;position:relative;overflow:hidden;">

  <div style="position:absolute;top:0;left:0;right:0;height:2px;
              background:linear-gradient(90deg,#10b981,#059669);border-radius:12px 12px 0 0;"></div>

  <div style="font-size:0.67rem;font-weight:800;text-transform:uppercase;
              letter-spacing:0.15em;color:#10b981;margin-bottom:10px;">
    🕸️ Knowledge Graph
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
    <div style="background:#081810;border:1px solid #064e2e;border-radius:8px;padding:8px 10px;text-align:center;">
      <div style="font-size:1.3rem;font-weight:800;color:#34d399;line-height:1;">{stats['nodes']}</div>
      <div style="font-size:0.62rem;color:#2d5a40;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">Concepts</div>
    </div>
    <div style="background:#081810;border:1px solid #064e2e;border-radius:8px;padding:8px 10px;text-align:center;">
      <div style="font-size:1.3rem;font-weight:800;color:#34d399;line-height:1;">{stats['edges']}</div>
      <div style="font-size:0.62rem;color:#2d5a40;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">Relations</div>
    </div>
  </div>

  <div style="font-size:0.68rem;color:#2d5a40;text-align:center;">
    ✓ Active — hallucination guard ON
  </div>
</div>""", unsafe_allow_html=True)


# ─── Widget 2: Prerequisite Chain Visualizer ─────────────────────────────────

def render_prereq_chain(kg: KnowledgeGraph, topic: str, mastered_topics: list):
    """
    Show the prerequisite chain for the current topic as a visual node path.
    Mastered nodes are green, current is blue, locked are grey.
    """
    if kg is None:
        return

    chain = kg.get_learning_chain(topic)
    if len(chain) <= 1:
        st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:10px;
            padding:10px 14px;margin-bottom:10px;">
  <span style="font-size:0.75rem;color:#4a6080;">
    🕸️ <strong style="color:#10b981;">{topic}</strong> is a foundational concept — no prerequisites needed.
  </span>
</div>""", unsafe_allow_html=True)
        return

    mastered_set = {m.lower() for m in mastered_topics}
    nodes_html   = ""

    for i, t in enumerate(chain):
        is_current  = (t.lower() == topic.lower())
        is_mastered = (t.lower() in mastered_set)
        is_last     = (i == len(chain) - 1)

        if is_current:
            color, bg, border, icon = "#60a5fa", "#0d1a2e", "#1d4ed8", "▶"
        elif is_mastered:
            color, bg, border, icon = "#34d399", "#081810", "#065f35", "✓"
        else:
            color, bg, border, icon = "#4a6080", "#0d1120", "#1a2540", str(i + 1)

        nodes_html += f"""
<div style="display:flex;flex-direction:column;align-items:center;flex:1;min-width:0;">
  <div style="width:36px;height:36px;border-radius:50%;background:{bg};
              border:2px solid {border};display:flex;align-items:center;
              justify-content:center;font-size:0.75rem;font-weight:800;
              color:{color};flex-shrink:0;
              {'box-shadow:0 0 10px ' + border + '66;' if is_current else ''}">
    {icon}
  </div>
  <div style="font-size:0.6rem;color:{color};text-align:center;margin-top:4px;
              max-width:60px;word-wrap:break-word;line-height:1.2;font-weight:{'700' if is_current else '400'};">
    {t[:20]}{'…' if len(t)>20 else ''}
  </div>
</div>"""

        if not is_last:
            nodes_html += """
<div style="flex-shrink:0;color:#1a2540;font-size:1rem;padding:0 2px;margin-top:-12px;">→</div>"""

    st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:12px;
            padding:12px 14px;margin-bottom:12px;">
  <div style="font-size:0.67rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.12em;color:#3b82f6;margin-bottom:10px;">
    🕸️ KG Learning Chain — {len(chain)} steps to mastery
  </div>
  <div style="display:flex;align-items:flex-start;justify-content:center;
              gap:4px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:4px;">
    {nodes_html}
  </div>
</div>""", unsafe_allow_html=True)


# ─── Widget 3: Next Topics Panel ─────────────────────────────────────────────

def render_next_topics(kg: KnowledgeGraph, mastered_topics: list):
    """Show the next recommended topics unlocked by current mastery."""
    if kg is None:
        return

    next_topics = kg.get_next_topics(mastered_topics)[:5]
    if not next_topics:
        st.markdown(f"""
<div style="background:#081810;border:1px solid #065f35;border-radius:10px;
            padding:10px 14px;font-size:0.78rem;color:#34d399;">
  🏆 All available topics unlocked!
</div>""", unsafe_allow_html=True)
        return

    items_html = ""
    for t in next_topics:
        diff = kg.get_difficulty(t)
        diff_color = ["", "#34d399", "#60a5fa", "#f59e0b", "#ef4444", "#a78bfa"][diff]
        diff_dots  = "●" * diff + "○" * (5 - diff)
        items_html += f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:7px 10px;background:#080c14;border:1px solid #1a2540;
            border-radius:8px;margin-bottom:5px;">
  <span style="font-size:0.78rem;color:#d4dbe8;font-weight:500;">
    {t}
  </span>
  <span style="font-size:0.65rem;color:{diff_color};letter-spacing:0.05em;
               flex-shrink:0;margin-left:8px;">
    {diff_dots}
  </span>
</div>"""

    st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:12px;
            padding:12px 14px;margin-bottom:10px;">
  <div style="font-size:0.67rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.12em;color:#3b82f6;margin-bottom:10px;">
    🔓 Next Unlocked Topics
  </div>
  {items_html}
</div>""", unsafe_allow_html=True)


# ─── Widget 4: KG Context Card (shown in chat) ───────────────────────────────

def render_kg_context_card(kg: KnowledgeGraph, topic: str, mastered_topics: list):
    """
    Show a compact KG insight card above the AI response.
    Tells the student what the KG knows about this topic.
    """
    if kg is None:
        return

    prereqs     = kg.get_prerequisites(topic)
    difficulty  = kg.get_difficulty(topic)
    chain       = kg.get_learning_chain(topic)
    mastered_set = {m.lower() for m in mastered_topics}
    unmastered_prereqs = [p for p in prereqs if p.lower() not in mastered_set]

    diff_label = ["", "Foundational", "Conceptual", "Applied", "Advanced", "Expert"][difficulty]
    diff_color = ["", "#34d399", "#60a5fa", "#f59e0b", "#ef4444", "#a78bfa"][difficulty]

    pills_html = f"""
<span style="display:inline-block;background:#0d1a2e;border:1px solid #1d4ed8;
             border-radius:20px;padding:2px 10px;font-size:0.68rem;
             color:{diff_color};font-weight:600;margin-right:5px;">
  Level {difficulty}/5 · {diff_label}
</span>"""

    if len(chain) > 1:
        pills_html += f"""
<span style="display:inline-block;background:#081810;border:1px solid #065f35;
             border-radius:20px;padding:2px 10px;font-size:0.68rem;
             color:#34d399;font-weight:600;margin-right:5px;">
  {len(chain)} steps in chain
</span>"""

    warn_html = ""
    if unmastered_prereqs:
        warn_html = f"""
<div style="margin-top:8px;padding:7px 10px;background:#1c0808;
            border:1px solid #7f1d1d;border-radius:8px;
            font-size:0.75rem;color:#f87171;">
  ⚠️ Unmastered prerequisites: <strong>{', '.join(unmastered_prereqs)}</strong>
  — consider reviewing these first.
</div>"""

    st.markdown(f"""
<div style="background:#0a0f1a;border:1px solid #1a2540;border-left:3px solid #3b82f6;
            border-radius:10px;padding:10px 14px;margin-bottom:8px;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
    <span style="font-size:0.67rem;font-weight:700;color:#3b82f6;
                 text-transform:uppercase;letter-spacing:0.12em;">🕸️ KG Insight</span>
    <span style="font-size:0.72rem;color:#4a6080;">{topic}</span>
  </div>
  <div style="margin-bottom:4px;">{pills_html}</div>
  {f'<div style="font-size:0.72rem;color:#4a6080;margin-top:6px;">Prerequisites: <span style=\\"color:#8090a8;\\">{", ".join(prereqs) if prereqs else "None (foundational)"}</span></div>' if prereqs else '<div style="font-size:0.72rem;color:#2a3a50;margin-top:4px;">Foundational topic — no prerequisites required.</div>'}
  {warn_html}
</div>""", unsafe_allow_html=True)


# ─── Widget 5: Hallucination Guard Badge ─────────────────────────────────────

def render_hallucination_score(validation: dict):
    """Show a small badge with hallucination risk after AI responses."""
    risk  = validation.get("hallucination_risk", 0)
    total = validation.get("total_mentioned", 0)
    verified = validation.get("verified", 0)

    if total == 0:
        return

    if risk < 0.2:
        color, label, bg, border = "#34d399", "KG Verified", "#081810", "#065f35"
    elif risk < 0.5:
        color, label, bg, border = "#f59e0b", "Partially Verified", "#1c1005", "#92400e"
    else:
        color, label, bg, border = "#ef4444", "Check Sources", "#1c0808", "#7f1d1d"

    st.markdown(f"""
<span style="display:inline-flex;align-items:center;gap:5px;background:{bg};
             border:1px solid {border};border-radius:20px;padding:3px 10px 3px 8px;">
  <span style="width:6px;height:6px;border-radius:50%;background:{color};
               box-shadow:0 0 5px {color}88;flex-shrink:0;"></span>
  <span style="font-size:0.7rem;font-weight:600;color:{color};">
    🕸️ {label} ({verified}/{total})
  </span>
</span>""", unsafe_allow_html=True)


# ─── Helper ───────────────────────────────────────────────────────────────────

def get_or_build_kg(subject: str, topics: list, groq_client,
                    force_rebuild: bool = False) -> KnowledgeGraph:
    """
    Get KG from session state cache, or build it.
    Stores in st.session_state to avoid rebuilding on every rerun.
    """
    cache_key = f"kg_{subject.lower().strip()}"

    if not force_rebuild and cache_key in st.session_state:
        return st.session_state[cache_key]

    from kg.kg_engine import build_knowledge_graph
    kg = build_knowledge_graph(subject, topics, groq_client,
                               force_rebuild=force_rebuild)
    st.session_state[cache_key] = kg
    return kg
