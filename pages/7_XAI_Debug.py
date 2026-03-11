"""
pages/7_XAI_Debug.py
─────────────────────────────────────────────────────────────────────────────
Live XAI Debug Dashboard — inspect all three novel components in real time.

Sections:
  1. XAI Live Inspector     — test any topic and see full explanation breakdown
  2. Emotion Signal Tester  — type text and see emotion scores fire live
  3. KG Explorer            — browse prerequisite chains and topic graph
  4. Session State Viewer   — see what's stored in st.session_state live
  5. Component Health Check — verify all three modules loaded correctly
"""

import streamlit as st
import time
import json

st.set_page_config(page_title="XAI Debug | LLM-ITS", page_icon="🔬", layout="wide")

# ── Auth ──────────────────────────────────────────────────────────────────────
if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid      = st.session_state.uid
profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=Instrument+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Instrument Sans', sans-serif; }
.stApp { background: #080c14; color: #d4dbe8; }
hr { border-color: #1a2540 !important; }
[data-baseweb="select"] { background: #0d1524 !important; border-color: #1a2540 !important; border-radius: 10px !important; }
[data-baseweb="input"]  { background: #0d1524 !important; border-color: #1a2540 !important; border-radius: 10px !important; }
textarea { background: #0a0e18 !important; border-color: #1a2540 !important; border-radius: 10px !important;
           font-family: 'JetBrains Mono', monospace !important; font-size: 0.83rem !important; color: #e2e8f0 !important; }
.stButton > button { border-radius: 10px !important; border: 1px solid #1a2540 !important;
    background: #0d1524 !important; color: #8090a8 !important; font-family: 'Instrument Sans', sans-serif !important; }
.stButton > button:hover { background: #1a2540 !important; border-color: #3b82f6 !important; color: #f0f4ff !important; }
button[kind="primary"] { background: linear-gradient(135deg,#2563eb,#1d4ed8) !important;
    border-color: #3b82f6 !important; color: #fff !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(160deg,#0d1524 0%,#080c14 60%);
            border:1px solid #1a2540;border-radius:20px;padding:28px 36px;
            margin-bottom:28px;position:relative;overflow:hidden;">
  <div style="position:absolute;right:32px;top:50%;transform:translateY(-50%);
              font-family:'Syne',sans-serif;font-size:5rem;font-weight:800;
              color:rgba(255,255,255,0.022);letter-spacing:0.15em;
              pointer-events:none;user-select:none;">DEBUG</div>
  <div style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;
              color:#f0f6ff;margin-bottom:4px;">🔬 XAI Debug Dashboard</div>
  <div style="color:#4a6080;font-size:0.88rem;">
    Live inspector for Emotion Detection · Knowledge Graph · XAI Explainer
  </div>
</div>
""", unsafe_allow_html=True)

# ── Component Health Check (always shown at top) ──────────────────────────────
st.markdown("### ⚙️ Component Health Check")

col1, col2, col3, col4 = st.columns(4)

def health_badge(label, ok, detail=""):
    color  = "#34d399" if ok else "#ef4444"
    bg     = "#081810" if ok else "#1c0808"
    border = "#065f35" if ok else "#7f1d1d"
    icon   = "✓" if ok else "✗"
    return f"""
<div style="background:{bg};border:1px solid {border};border-radius:12px;
            padding:14px;text-align:center;">
  <div style="font-size:1.4rem;font-weight:800;color:{color};">{icon}</div>
  <div style="font-size:0.75rem;font-weight:700;color:{color};margin-top:4px;">{label}</div>
  <div style="font-size:0.65rem;color:#3a5070;margin-top:3px;">{detail}</div>
</div>"""

# Check each component
checks = {}

try:
    from emotion.emotion_engine import EmotionSessionTracker, detect_emotion
    test = detect_emotion(text="i dont get it", recent_results=[False, False])
    checks["emotion"] = (True, f"State: {test.state}")
except Exception as e:
    checks["emotion"] = (False, str(e)[:40])

try:
    from kg.kg_engine import KnowledgeGraph
    checks["kg"] = (True, f"{len([s for s in subjects if KnowledgeGraph.exists(s)])} KG(s) built")
except Exception as e:
    checks["kg"] = (False, str(e)[:40])

try:
    from xai.xai_engine import build_xai_explanation, XAIExplanation
    checks["xai"] = (True, "Engine loaded")
except Exception as e:
    checks["xai"] = (False, str(e)[:40])

try:
    from llm.llm_engine import MODEL_NAME
    checks["llm"] = (True, MODEL_NAME)
except Exception as e:
    checks["llm"] = (False, str(e)[:40])

with col1: st.markdown(health_badge("🧠 Emotion Engine", *checks["emotion"]), unsafe_allow_html=True)
with col2: st.markdown(health_badge("🕸️ Knowledge Graph", *checks["kg"]),     unsafe_allow_html=True)
with col3: st.markdown(health_badge("✦ XAI Engine",       *checks["xai"]),    unsafe_allow_html=True)
with col4: st.markdown(health_badge("⚡ LLM (Groq)",       *checks["llm"]),    unsafe_allow_html=True)

st.divider()

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "✦ XAI Inspector",
    "🧠 Emotion Tester",
    "🕸️ KG Explorer",
    "📦 Session State",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — XAI Live Inspector
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("#### Test XAI explanation for any topic + configuration")
    st.caption("Fill in the fields below and click **Generate XAI**. This shows exactly what your student sees.")

    c1, c2 = st.columns([1, 1])
    with c1:
        xai_subject  = st.selectbox("Subject", subjects, key="xai_subj")
        from database.db import get_topics
        xai_topics   = get_topics(xai_subject) or ["Introduction", "Core Concepts", "Advanced Topics"]
        xai_topic    = st.selectbox("Topic", xai_topics, key="xai_topic")
        xai_query    = st.text_input("Student question", value="Can you explain this topic?", key="xai_q")

    with c2:
        xai_mastery  = st.selectbox("Mastery Level", ["Weak", "Moderate", "Strong"], index=1, key="xai_mastery")
        xai_accuracy = st.slider("Accuracy %", 0, 100, 60, key="xai_acc")
        xai_emotion  = st.selectbox("Emotion State", ["neutral","frustration","boredom","anxiety","confusion","confidence"], key="xai_emo")
        xai_action   = st.selectbox("Emotion Action", ["none","simplify","advance","scaffold","remediate","challenge"], key="xai_act")
        xai_modality = st.selectbox("AEL Modality", [0,1,2,3,4],
                                     format_func=lambda x: {0:"Standard",1:"Step-by-Step",2:"Analogical",3:"Worked Example",4:"Simplified"}[x],
                                     key="xai_mod")

    mastered_input = st.text_input("Mastered topics (comma separated)", placeholder="e.g. Arrays, Linked Lists", key="xai_mastered")
    mastered_list  = [t.strip() for t in mastered_input.split(",") if t.strip()]

    if st.button("✦ Generate XAI Explanation", type="primary", use_container_width=True):
        with st.spinner("Building XAI explanation from all 3 sources..."):
            try:
                from xai.xai_engine import build_xai_explanation
                from xai.xai_widget import render_xai_panel, render_xai_strip
                from kg.kg_widget  import get_or_build_kg

                def _get_client():
                    import os
                    try:
                        api_key = st.secrets["GROQ_API_KEY"]
                    except Exception:
                        try: api_key = st.secrets["supabase"]["GROQ_API_KEY"]
                        except Exception: api_key = os.environ.get("GROQ_API_KEY","")
                    from groq import Groq
                    return Groq(api_key=api_key)

                kg  = get_or_build_kg(xai_subject, xai_topics, _get_client())
                xai = build_xai_explanation(
                    topic           = xai_topic,
                    subject         = xai_subject,
                    query           = xai_query,
                    kg              = kg,
                    mastered_topics = mastered_list,
                    mastery_level   = xai_mastery,
                    accuracy        = float(xai_accuracy),
                    modality_idx    = xai_modality,
                    emotion_state   = xai_emotion,
                    emotion_action  = xai_action,
                    generate_cot    = False,
                )

                st.success("✅ XAI explanation generated")
                st.divider()

                # Show XAI strip
                render_xai_strip(xai)

                # Show full panel
                render_xai_panel(xai)

                # Show raw JSON for debugging
                with st.expander("🔍 Raw XAI JSON (debug)", expanded=False):
                    st.code(json.dumps(xai.to_dict(), indent=2), language="json")

            except Exception as e:
                st.error(f"❌ XAI failed: {e}")
                import traceback
                st.code(traceback.format_exc(), language="python")

    # Show last XAI from Study session
    st.divider()
    st.markdown("#### 📌 Last XAI from Study Session")
    last_xai = st.session_state.get("_last_xai")
    if last_xai:
        st.success(f"Topic: **{last_xai.topic}** | Confidence: **{round(last_xai.confidence*100)}%** | Sources: {last_xai.sources_used}")
        from xai.xai_widget import render_xai_panel, render_xai_strip
        render_xai_strip(last_xai)
        render_xai_panel(last_xai)
    else:
        st.info("No XAI data yet — go to the Study page, ask a question, then come back here.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Emotion Signal Tester
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("#### Type any student message and see emotion scores fire live")

    emo_col1, emo_col2 = st.columns([1, 1])

    with emo_col1:
        test_text    = st.text_area("Student message", height=100,
                                     placeholder="e.g. I dont get it, this is too hard",
                                     key="emo_text")
        test_latency = st.slider("Response latency (seconds)", 0.0, 120.0, 15.0, key="emo_lat")
        test_avg_lat = st.slider("Student avg latency (seconds)", 5.0, 60.0, 30.0, key="emo_avg")

        results_input = st.text_input("Recent answer results (T/F comma separated)",
                                       placeholder="e.g. F,F,F,T,F", key="emo_results")
        recent_results = []
        if results_input.strip():
            for r in results_input.split(","):
                r = r.strip().upper()
                if r in ("T","TRUE","1","CORRECT"):   recent_results.append(True)
                elif r in ("F","FALSE","0","WRONG"):  recent_results.append(False)

    if st.button("🧠 Detect Emotion", type="primary", use_container_width=True, key="emo_btn"):
        from emotion.emotion_engine import detect_emotion, analyze_text_signal, analyze_timing_signal, analyze_pattern_signal, fuse_signals

        t_sig  = analyze_text_signal(test_text)
        tm_sig = analyze_timing_signal(test_latency, test_avg_lat)
        p_sig  = analyze_pattern_signal(recent_results)
        result = detect_emotion(test_text, test_latency, test_avg_lat, recent_results, topic="debug")

        with emo_col2:
            # Dominant state card
            state_colors = {"frustration":"#ef4444","boredom":"#a78bfa","anxiety":"#f59e0b",
                            "confusion":"#38bdf8","confidence":"#34d399","neutral":"#94a3b8"}
            state_emojis = {"frustration":"😤","boredom":"😴","anxiety":"😰",
                            "confusion":"😵","confidence":"😎","neutral":"🙂"}
            sc = state_colors.get(result.state, "#94a3b8")
            se = state_emojis.get(result.state, "🙂")

            st.markdown(f"""
<div style="background:#0d1524;border:2px solid {sc};border-radius:14px;
            padding:16px;text-align:center;margin-bottom:12px;">
  <div style="font-size:2.5rem;">{se}</div>
  <div style="font-size:1.2rem;font-weight:800;color:{sc};margin-top:6px;">
    {result.state.upper()}
  </div>
  <div style="font-size:0.75rem;color:#4a6080;margin-top:4px;">
    Action: <strong style="color:{sc};">{result.action}</strong>
  </div>
  <div style="font-size:0.75rem;color:#4a6080;margin-top:2px;">
    Re-route: <strong style="color:{'#34d399' if result.should_reroute else '#4a6080'};">
    {'YES' if result.should_reroute else 'NO'}</strong>
  </div>
</div>""", unsafe_allow_html=True)

        st.divider()

        # Signal breakdown
        st.markdown("**📡 Signal Breakdown**")
        sig_cols = st.columns(3)
        sig_data = [
            ("📝 Text Signal",    t_sig,  ["Frustration","Boredom","Anxiety","Confusion","Confidence"]),
            ("⏱️ Timing Signal",  tm_sig, ["Frustration","Boredom","Anxiety","Confusion","Confidence"]),
            ("🎯 Pattern Signal", p_sig,  ["Frustration","Boredom","Anxiety","Confusion","Confidence"]),
        ]
        bar_colors = ["#ef4444","#a78bfa","#f59e0b","#38bdf8","#34d399"]

        for col, (title, sig, labels) in zip(sig_cols, sig_data):
            with col:
                scores = [sig.scores.frustration, sig.scores.boredom,
                          sig.scores.anxiety, sig.scores.confusion, sig.scores.confidence]
                bars = ""
                for label, score, color in zip(labels, scores, bar_colors):
                    pct = round(score * 100)
                    bars += f"""
<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
  <span style="width:68px;font-size:0.67rem;color:#4a6080;text-align:right;flex-shrink:0;">{label}</span>
  <div style="flex:1;height:8px;background:#1a2540;border-radius:4px;overflow:hidden;">
    <div style="width:{pct}%;height:100%;background:{color};border-radius:4px;"></div>
  </div>
  <span style="width:28px;font-size:0.67rem;color:#4a6080;flex-shrink:0;">{pct}%</span>
</div>"""
                st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:12px;padding:12px;">
  <div style="font-size:0.7rem;font-weight:700;color:#3b82f6;margin-bottom:10px;">{title}</div>
  {bars}
  <div style="font-size:0.65rem;color:#2a3a50;margin-top:6px;font-style:italic;">{sig.notes[:60]}{"…" if len(sig.notes)>60 else ""}</div>
</div>""", unsafe_allow_html=True)

        # Fused vector
        st.divider()
        st.markdown("**🔀 Fused Vector (weighted: text 45%, pattern 30%, timing 25%)**")
        v = result.vector
        fused_data = [
            ("Frustration", v.frustration, "#ef4444"),
            ("Boredom",     v.boredom,     "#a78bfa"),
            ("Anxiety",     v.anxiety,     "#f59e0b"),
            ("Confusion",   v.confusion,   "#38bdf8"),
            ("Confidence",  v.confidence,  "#34d399"),
        ]
        fused_bars = ""
        for label, score, color in fused_data:
            pct = round(score * 100)
            is_dom = label.lower() == result.state
            glow = f"box-shadow:0 0 8px {color}88;" if is_dom else ""
            fused_bars += f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
  <span style="width:80px;font-size:0.72rem;color:{'#f0f6ff' if is_dom else '#4a6080'};
               font-weight:{'700' if is_dom else '400'};flex-shrink:0;">{label}</span>
  <div style="flex:1;height:12px;background:#1a2540;border-radius:6px;overflow:hidden;border:1px solid {'#2a3a50' if is_dom else '#1a2540'};">
    <div style="width:{pct}%;height:100%;background:{color};border-radius:6px;{glow}"></div>
  </div>
  <span style="width:36px;font-size:0.72rem;color:{'#f0f6ff' if is_dom else '#4a6080'};
               font-weight:{'700' if is_dom else '400'};flex-shrink:0;">{pct}%</span>
  {"<span style='font-size:0.65rem;color:" + color + ";'>◀ DOMINANT</span>" if is_dom and pct > 0 else ""}
</div>"""

        st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:12px;padding:14px;">
  {fused_bars}
</div>""", unsafe_allow_html=True)

        # XAI reason text
        if result.should_reroute:
            st.divider()
            st.markdown("**✦ XAI Re-routing Explanation (what the student sees)**")
            from emotion.emotion_widget import render_reroute_banner
            render_reroute_banner(result)

    # Quick test phrases
    st.divider()
    st.markdown("**⚡ Quick test phrases — click to auto-fill**")
    phrases = [
        ("😤 Frustration", "i dont get it this is too hard i give up"),
        ("😴 Boredom",     "this is too easy i already know this boring"),
        ("😰 Anxiety",     "im not sure maybe i think i might be wrong"),
        ("😵 Confusion",   "what does this mean can you explain again huh"),
        ("😎 Confidence",  "got it makes sense easy i understand perfectly"),
    ]
    pcols = st.columns(5)
    for col, (label, phrase) in zip(pcols, phrases):
        with col:
            if st.button(label, use_container_width=True, key=f"quick_{label}"):
                st.session_state["emo_text"] = phrase
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — KG Explorer
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("#### Browse your Knowledge Graph — prerequisites, chains, next topics")

    kg_subject = st.selectbox("Subject", subjects, key="kg_subj_debug")

    from kg.kg_engine import KnowledgeGraph
    from database.db import get_topics as _get_topics

    if not KnowledgeGraph.exists(kg_subject):
        st.warning(f"⚠️ No KG built for **{kg_subject}** yet. Go to **Upload Syllabus** → Build KG.")
    else:
        def _get_client_kg():
            import os
            try: api_key = st.secrets["GROQ_API_KEY"]
            except Exception:
                try: api_key = st.secrets["supabase"]["GROQ_API_KEY"]
                except Exception: api_key = os.environ.get("GROQ_API_KEY","")
            from groq import Groq
            return Groq(api_key=api_key)

        from kg.kg_widget import get_or_build_kg
        kg = get_or_build_kg(kg_subject, _get_topics(kg_subject) or [], _get_client_kg())

        if kg:
            stats = kg.stats()

            # Stats row
            s1, s2, s3 = st.columns(3)
            with s1:
                st.markdown(f"""
<div style="background:#081810;border:1px solid #065f35;border-radius:12px;padding:14px;text-align:center;">
  <div style="font-size:2rem;font-weight:800;color:#34d399;">{stats['nodes']}</div>
  <div style="font-size:0.68rem;color:#2d5a40;text-transform:uppercase;">Concept Nodes</div>
</div>""", unsafe_allow_html=True)
            with s2:
                st.markdown(f"""
<div style="background:#0d1a2e;border:1px solid #1d4ed8;border-radius:12px;padding:14px;text-align:center;">
  <div style="font-size:2rem;font-weight:800;color:#60a5fa;">{stats['edges']}</div>
  <div style="font-size:0.68rem;color:#1e3a6e;text-transform:uppercase;">Prerequisite Edges</div>
</div>""", unsafe_allow_html=True)
            with s3:
                density = round(stats['edges'] / max(1, stats['nodes'] * (stats['nodes']-1)) * 100, 1)
                st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:12px;padding:14px;text-align:center;">
  <div style="font-size:2rem;font-weight:800;color:#a78bfa;">{density}%</div>
  <div style="font-size:0.68rem;color:#2a3a50;text-transform:uppercase;">Graph Density</div>
</div>""", unsafe_allow_html=True)

            st.divider()

            # Topic explorer
            all_topics = kg.all_topics()
            sel_topic  = st.selectbox("Select topic to inspect", all_topics, key="kg_topic_debug")

            if sel_topic:
                kg_c1, kg_c2 = st.columns(2)

                with kg_c1:
                    st.markdown("**📥 Prerequisites (must learn before)**")
                    prereqs = kg.get_prerequisites(sel_topic)
                    if prereqs:
                        for p in prereqs:
                            diff = kg.get_difficulty(p)
                            st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            background:#0d1524;border:1px solid #1a2540;border-radius:8px;
            padding:8px 12px;margin-bottom:5px;">
  <span style="font-size:0.8rem;color:#d4dbe8;">← {p}</span>
  <span style="font-size:0.68rem;color:#4a6080;">Level {diff}/5</span>
</div>""", unsafe_allow_html=True)
                    else:
                        st.markdown("""
<div style="background:#081810;border:1px solid #065f35;border-radius:8px;padding:10px 12px;
            font-size:0.78rem;color:#34d399;">✓ Foundational topic — no prerequisites</div>""",
                            unsafe_allow_html=True)

                with kg_c2:
                    st.markdown("**📤 Unlocks (topics this enables)**")
                    import networkx as nx
                    nid  = kg._normalize(sel_topic)
                    successors = list(kg.graph.successors(nid))
                    if successors:
                        for s in successors:
                            label = kg.graph.nodes[s].get("label", s)
                            diff  = kg.graph.nodes[s].get("difficulty", 2)
                            st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            background:#0d1524;border:1px solid #1a2540;border-radius:8px;
            padding:8px 12px;margin-bottom:5px;">
  <span style="font-size:0.8rem;color:#d4dbe8;">{label} →</span>
  <span style="font-size:0.68rem;color:#4a6080;">Level {diff}/5</span>
</div>""", unsafe_allow_html=True)
                    else:
                        st.markdown("""
<div style="background:#1c1005;border:1px solid #92400e;border-radius:8px;padding:10px 12px;
            font-size:0.78rem;color:#fbbf24;">⚡ Terminal topic — no further topics depend on this</div>""",
                            unsafe_allow_html=True)

                st.divider()

                # Full chain visualization
                st.markdown("**🔗 Full Learning Chain to this topic**")
                from kg.kg_widget import render_prereq_chain
                render_prereq_chain(kg, sel_topic, [])

                st.divider()

                # Next topics
                st.markdown("**🔓 Topics unlocked if this is mastered**")
                next_t = kg.get_next_topics([sel_topic])[:8]
                if next_t:
                    ncols = st.columns(min(4, len(next_t)))
                    for col, nt in zip(ncols, next_t):
                        diff = kg.get_difficulty(nt)
                        diff_colors = ["","#34d399","#60a5fa","#f59e0b","#ef4444","#a78bfa"]
                        with col:
                            st.markdown(f"""
<div style="background:#0d1524;border:1px solid {diff_colors[diff]}44;border-radius:10px;
            padding:10px;text-align:center;">
  <div style="font-size:0.78rem;color:#d4dbe8;font-weight:600;">{nt}</div>
  <div style="font-size:0.65rem;color:{diff_colors[diff]};margin-top:3px;">Level {diff}/5</div>
</div>""", unsafe_allow_html=True)

            st.divider()

            # Full edge list
            with st.expander("📋 All prerequisite edges (raw)", expanded=False):
                edges = [(kg.graph.nodes[u].get("label",u),
                          kg.graph.nodes[v].get("label",v),
                          round(d.get("confidence",0.8),2))
                         for u,v,d in kg.graph.edges(data=True)]
                edges.sort(key=lambda x: x[2], reverse=True)
                for prereq, topic, conf in edges:
                    bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
                    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:5px 0;
            border-bottom:1px solid #0d1a28;font-size:0.75rem;">
  <span style="color:#60a5fa;width:160px;flex-shrink:0;">{prereq}</span>
  <span style="color:#3a5070;">→</span>
  <span style="color:#d4dbe8;flex:1;">{topic}</span>
  <span style="color:#34d399;font-family:monospace;font-size:0.65rem;">{bar} {conf}</span>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Session State Viewer
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("#### Live view of st.session_state — see what's stored right now")

    # Filter to relevant keys
    relevant_keys = [k for k in st.session_state.keys()
                     if any(x in k for x in ["xai","emotion","kg","tracker","_last","selected","study","quiz"])]
    all_keys      = list(st.session_state.keys())

    show_all = st.toggle("Show all session state keys", value=False)
    keys_to_show = all_keys if show_all else relevant_keys

    if st.button("🔄 Refresh", key="ss_refresh"):
        st.rerun()

    st.caption(f"Showing {len(keys_to_show)} of {len(all_keys)} keys")

    for key in sorted(keys_to_show):
        val = st.session_state[key]
        # Serialize for display
        try:
            if hasattr(val, 'to_dict'):
                display = json.dumps(val.to_dict(), indent=2)
            elif hasattr(val, '__dict__'):
                display = json.dumps({k:str(v) for k,v in val.__dict__.items()
                                       if not k.startswith('_')}, indent=2)
            else:
                display = json.dumps(val, indent=2, default=str)
        except Exception:
            display = str(val)[:500]

        type_color = "#3b82f6" if "xai" in key else "#34d399" if "emotion" in key else "#f59e0b" if "kg" in key else "#6b7280"

        with st.expander(f"`{key}`  —  {type(val).__name__}", expanded=False):
            st.code(display, language="json")