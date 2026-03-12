"""
pages/8_Subjects.py
─────────────────────────────────────────────────────────────────────────────
Subject Manager + Syllabus Upload — clean tabbed layout.
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import os
import tempfile
from database.db import get_topics, topics_exist, save_topics, get_connection
from components.sidebar import render_sidebar
from utils.theme import inject_theme, get_theme

st.set_page_config(page_title="Subjects | LLM-ITS", page_icon="📚", layout="wide")
render_sidebar()

if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid     = st.session_state.uid
profile = st.session_state.profile

inject_theme()

# ── No query params needed — actions handled via session state buttons ──────────

# ── Extra CSS ─────────────────────────────────────────────────────────────────
t = get_theme()
_is_dark = (t.get("name", "dark") == "dark")

# Pick button colors based on theme
btn_bg           = "#1a2540"  if _is_dark else "#eef2f7"
btn_border       = "#2a3f55"  if _is_dark else "#b0bdd0"
btn_color        = "#8aabcc"  if _is_dark else "#3a5070"
btn_hover_bg     = "#1e3a5f"  if _is_dark else "#d0e2f8"
btn_hover_border = "#3b82f6"
btn_hover_color  = "#90c4f9"  if _is_dark else "#1d4ed8"
del_hover_bg     = "#2d0a0a"  if _is_dark else "#fff0f0"
del_hover_border = "#ef4444"
del_hover_color  = "#f87171"  if _is_dark else "#dc2626"

st.markdown(f"""
<style>
[data-testid="stSidebarNav"] {{ display: none !important; }}

.subj-page-title {{
    font-family: 'Syne', sans-serif;
    font-size: 1.7rem; font-weight: 800;
    color: {t['text_primary']}; margin: 0 0 4px 0;
}}
.subj-page-sub {{
    font-size: 0.82rem; color: {t['text_muted']}; margin: 0 0 28px 0;
}}

/* Subject card row */
.subj-row {{
    display: flex; align-items: center; gap: 12px;
    background: {t['card_bg']};
    border: 1px solid {t['border']};
    border-radius: 14px; padding: 10px 14px;
    margin-bottom: 8px;
    transition: border-color 0.2s;
}}
.subj-row:hover {{ border-color: {t['accent_light']}; }}
.subj-index {{
    width: 26px; height: 26px; border-radius: 7px;
    background: {t['accent']}22; border: 1px solid {t['accent']}44;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.7rem; font-weight: 800; color: {t['accent_light']};
    flex-shrink: 0;
}}
.subj-name {{
    font-family: 'Syne', sans-serif; font-size: 0.88rem;
    font-weight: 700; color: {t['text_primary']}; flex: 1;
}}

/* ── Up / Delete action buttons — always visible ── */
div[data-testid="stButton"] button[title="Move up"],
div[data-testid="stButton"] button[title="Remove"] {{
    background-color: {btn_bg} !important;
    background: {btn_bg} !important;
    color: {btn_color} !important;
    border: 1px solid {btn_border} !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    font-weight: 800 !important;
    min-height: 36px !important;
    padding: 0 !important;
    box-shadow: none !important;
}}
div[data-testid="stButton"] button[title="Move up"]:hover {{
    background-color: {btn_hover_bg} !important;
    background: {btn_hover_bg} !important;
    border-color: {btn_hover_border} !important;
    color: {btn_hover_color} !important;
    transform: translateY(-1px) !important;
}}
div[data-testid="stButton"] button[title="Remove"]:hover {{
    background-color: {del_hover_bg} !important;
    background: {del_hover_bg} !important;
    border-color: {del_hover_border} !important;
    color: {del_hover_color} !important;
    transform: translateY(-1px) !important;
}}

/* Badges */
.badge-ready {{
    background: {t['success_bg']}; color: {t['success']};
    border: 1px solid {t['success']}44; border-radius: 999px;
    padding: 2px 10px; font-size: 0.65rem; font-weight: 600;
}}
.badge-pdf {{
    background: {t['accent']}18; color: {t['accent_light']};
    border: 1px solid {t['accent']}44; border-radius: 999px;
    padding: 2px 10px; font-size: 0.65rem; font-weight: 600;
}}
.badge-none {{
    background: {t['warning_bg']}; color: {t['warning']};
    border: 1px solid {t['warning']}44; border-radius: 999px;
    padding: 2px 10px; font-size: 0.65rem; font-weight: 600;
}}

/* Empty state */
.empty-box {{
    background: {t['card_bg2']};
    border: 1px dashed {t['border']};
    border-radius: 16px; padding: 40px 24px;
    text-align: center; color: {t['text_muted']};
}}
.empty-box .e-icon  {{ font-size: 2.4rem; margin-bottom: 10px; }}
.empty-box .e-title {{ font-family: 'Syne', sans-serif; font-weight: 700;
                       font-size: 1rem; color: {t['text_primary']}; margin-bottom: 6px; }}
.empty-box .e-sub   {{ font-size: 0.8rem; }}

/* Quick add done pill */
.quick-pill-done {{
    background: {t['success_bg']};
    border: 1px solid {t['success']}44;
    border-radius: 10px; padding: 8px 12px;
    font-size: 0.78rem; color: {t['success']};
    font-weight: 600; text-align: center;
    margin-bottom: 4px;
}}

/* Step guide */
.step-guide {{
    background: {t['card_bg']};
    border: 1px solid {t['border']};
    border-radius: 14px; padding: 18px 20px; margin-top: 8px;
}}
.step-item {{
    display: flex; align-items: flex-start;
    gap: 12px; margin-bottom: 12px;
}}
.step-item:last-child {{ margin-bottom: 0; }}
.step-num-badge {{
    width: 22px; height: 22px; border-radius: 50%;
    background: {t['accent']}; color: #fff;
    font-size: 0.68rem; font-weight: 800;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 1px;
}}
.step-text-s {{ font-size: 0.8rem; color: {t['text_secondary']}; line-height: 1.5; }}

/* KG stats */
.kg-stat-row {{
    display: flex; gap: 16px;
    background: {t['success_bg']};
    border: 1px solid {t['success']}44;
    border-radius: 12px; padding: 14px 18px;
    margin-bottom: 12px; align-items: center;
}}
.kg-stat-num {{
    font-family: 'Syne', sans-serif; font-size: 1.5rem;
    font-weight: 800; color: {t['success']};
}}
.kg-stat-lbl {{
    font-size: 0.65rem; text-transform: uppercase;
    letter-spacing: 0.08em; color: {t['text_muted']};
}}
.file-info {{
    background: {t['card_bg2']};
    border: 1px solid {t['border']};
    border-radius: 10px; padding: 10px 14px;
    font-size: 0.8rem; color: {t['text_muted']}; margin-bottom: 12px;
}}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_current_subjects():
    p   = st.session_state.profile
    raw = p.get("subjects_list") or p.get("subject_list", "")
    if isinstance(raw, list):
        return [s.strip() for s in raw if s.strip()]
    return [s.strip() for s in str(raw).split(",") if s.strip()]


def save_subjects_to_db(uid, subjects):
    try:
        conn = get_connection()
        c    = conn.cursor()
        c.execute(
            "UPDATE learner_profile SET subject_list = %s WHERE uid = %s",
            (", ".join(subjects), uid)
        )
        conn.commit(); conn.close()
        return True
    except Exception as e:
        st.error(f"DB save failed: {e}")
        return False


def refresh_session(subjects):
    st.session_state.profile["subjects_list"] = subjects
    st.session_state.profile["subject_list"]  = ", ".join(subjects)
    st.session_state.subjects_edit_list       = subjects
    for k in [k for k in list(st.session_state.keys()) if k.startswith(("kg_", "topics_"))]:
        del st.session_state[k]


def get_subject_status(subj):
    has_topics = bool(get_topics(subj))
    has_kg = has_index = False
    try:
        from kg.kg_engine import KnowledgeGraph
        has_kg = KnowledgeGraph.exists(subj)
    except Exception:
        pass
    try:
        from rag.rag_pipeline import index_exists
        has_index = index_exists(subj)
    except Exception:
        pass
    return has_topics, has_kg, has_index


# ── Init ──────────────────────────────────────────────────────────────────────
if "subjects_edit_list" not in st.session_state:
    st.session_state.subjects_edit_list = get_current_subjects()

current = st.session_state.subjects_edit_list

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<div>
    <p class="subj-page-title">📚 Subject Manager</p>
    <p class="subj-page-sub">Add subjects, upload syllabi, and build knowledge graphs — all in one place.</p>
</div>
""", unsafe_allow_html=True)

tab_subj, tab_upload, tab_kg = st.tabs([
    "📋  My Subjects",
    "⬆️  Upload Syllabus",
    "🕸️  Knowledge Graph",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — My Subjects
# ══════════════════════════════════════════════════════════════════════════════
with tab_subj:
    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        st.markdown("#### Your Subjects")

        if not current:
            st.markdown("""
            <div class="empty-box">
                <div class="e-icon">📭</div>
                <div class="e-title">No subjects yet</div>
                <div class="e-sub">Use Quick Add or type a subject name on the right.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for i, subj in enumerate(current):
                has_topics, has_kg, has_index = get_subject_status(subj)
                if has_topics and has_kg:
                    badge = '<span class="badge-ready">✓ PDF + KG</span>'
                elif has_index or has_topics:
                    badge = '<span class="badge-pdf">✓ PDF indexed</span>'
                else:
                    badge = '<span class="badge-none">⚠ No PDF</span>'

                # Subject card + inline action buttons
                c_name, c_up, c_del = st.columns([6, 0.7, 0.7])
                with c_name:
                    st.markdown(f"""
                    <div class="subj-row">
                        <div class="subj-index">{i+1}</div>
                        <div class="subj-name">{subj}</div>
                        {badge}
                    </div>
                    """, unsafe_allow_html=True)
                with c_up:
                    if i > 0:
                        if st.button("▲", key=f"up_{i}", use_container_width=True, help="Move up"):
                            lst = st.session_state.subjects_edit_list
                            lst[i], lst[i-1] = lst[i-1], lst[i]
                            st.rerun()
                with c_del:
                    if st.button("✕", key=f"del_{i}", use_container_width=True, help="Remove"):
                        st.session_state[f"confirm_del_{i}"] = True
                        st.rerun()

                # Inline confirm delete
                if st.session_state.get(f"confirm_del_{i}"):
                    st.warning(f"Remove **{subj}**? Your uploaded PDFs won't be deleted.")
                    y, n = st.columns(2)
                    with y:
                        if st.button("✓ Remove", key=f"yes_{i}",
                                     type="primary", use_container_width=True):
                            st.session_state.subjects_edit_list = [s for s in current if s != subj]
                            st.session_state.pop(f"confirm_del_{i}", None)
                            st.rerun()
                    with n:
                        if st.button("✗ Cancel", key=f"no_{i}", use_container_width=True):
                            st.session_state.pop(f"confirm_del_{i}", None)
                            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        s_col, r_col = st.columns(2)
        with s_col:
            if st.button("💾 Save Changes", type="primary", use_container_width=True,
                         disabled=len(current) == 0):
                if save_subjects_to_db(uid, current):
                    refresh_session(current)
                    st.success(f"✅ {len(current)} subject(s) saved!")
                    st.rerun()
        with r_col:
            if st.button("↺ Reset", use_container_width=True):
                st.session_state.subjects_edit_list = get_current_subjects()
                st.rerun()

    with right:
        st.markdown("#### Add a Subject")
        new_subject = st.text_input(
            "Subject name",
            placeholder="e.g. Machine Learning, Thermodynamics...",
            key="new_subject_input",
            label_visibility="collapsed"
        )
        if st.button("➕ Add Subject", type="primary", use_container_width=True,
                     disabled=not new_subject.strip()):
            cleaned = new_subject.strip().title()
            if cleaned in st.session_state.subjects_edit_list:
                st.warning(f"**{cleaned}** already added.")
            elif len(st.session_state.subjects_edit_list) >= 8:
                st.warning("Maximum 8 subjects allowed.")
            else:
                st.session_state.subjects_edit_list.append(cleaned)
                st.rerun()

        st.markdown("---")
        st.markdown("#### ⚡ Quick Add")

        QUICK = [
            ("💻", "Data Structures"),   ("🧮", "Algorithms"),
            ("🤖", "Machine Learning"),  ("🌐", "Computer Networks"),
            ("🗄️", "Database Systems"),  ("⚙️", "Operating Systems"),
            ("🔢", "Linear Algebra"),    ("📊", "Statistics"),
            ("🐍", "Python Programming"),("☕", "Java Programming"),
            ("🌍", "Web Development"),   ("🔐", "Cyber Security"),
            ("📱", "Mobile Dev"),        ("☁️", "Cloud Computing"),
            ("🧠", "Deep Learning"),     ("📡", "Computer Architecture"),
        ]

        q1, q2 = st.columns(2)
        for idx, (icon, subj) in enumerate(QUICK):
            already = subj in st.session_state.subjects_edit_list
            col     = q1 if idx % 2 == 0 else q2
            with col:
                if already:
                    st.markdown(f'<div class="quick-pill-done">✓ {icon} {subj}</div>',
                                unsafe_allow_html=True)
                else:
                    if st.button(f"{icon} {subj}", key=f"quick_{subj}",
                                 use_container_width=True):
                        if len(st.session_state.subjects_edit_list) >= 8:
                            st.warning("Maximum 8 subjects.")
                        else:
                            st.session_state.subjects_edit_list.append(subj)
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Upload Syllabus
# ══════════════════════════════════════════════════════════════════════════════
with tab_upload:
    if not current:
        st.markdown("""
        <div class="empty-box" style="margin-top:16px;">
            <div class="e-icon">📂</div>
            <div class="e-title">No subjects saved yet</div>
            <div class="e-sub">Go to <strong>My Subjects</strong> tab, add your subjects, and save them first.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        ul, ur = st.columns([1, 1], gap="large")
        with ul:
            st.markdown("#### Select Subject & Upload")
            selected_subject = st.selectbox(
                "Subject", current, key="upload_subj_sel",
                label_visibility="collapsed"
            )
            has_topics, has_kg, has_index = get_subject_status(selected_subject)
            if has_index or has_topics:
                st.success(f"✅ **{selected_subject}** already has a PDF indexed. Re-upload to replace it.")
            else:
                st.info(f"📄 No PDF uploaded yet for **{selected_subject}**.")

            uploaded_file = st.file_uploader("Choose a PDF syllabus", type=["pdf"],
                                             key="syllabus_uploader")
            if uploaded_file:
                st.markdown(f"""
                <div class="file-info">
                    📄 <strong style="color:{t['text_primary']};">{uploaded_file.name}</strong>
                    &nbsp;·&nbsp; {round(uploaded_file.size/1024, 1)} KB
                </div>
                """, unsafe_allow_html=True)
                if st.button("🔨 Build Index + Extract Topics",
                             type="primary", use_container_width=True):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name
                    try:
                        from rag.rag_pipeline import build_faiss_index, extract_topics_from_pdf
                        prog = st.progress(0, text="Reading PDF...")
                        prog.progress(25, text="Extracting topics...")
                        topics = extract_topics_from_pdf(tmp_path)
                        save_topics(selected_subject, topics)
                        prog.progress(55, text="Building FAISS index...")
                        chunk_count = build_faiss_index(selected_subject, tmp_path)
                        prog.progress(100, text="Done!")
                        st.success(f"✅ **{chunk_count} chunks** indexed · **{len(topics)} topics** extracted")
                        if topics:
                            with st.expander(f"📋 {len(topics)} topics found", expanded=True):
                                tcols = st.columns(3)
                                for idx2, t2 in enumerate(topics):
                                    tcols[idx2 % 3].markdown(f"• {t2}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                    finally:
                        try: os.unlink(tmp_path)
                        except: pass

        with ur:
            st.markdown("#### How it works")
            st.markdown(f"""
            <div class="step-guide">
                <div class="step-item"><div class="step-num-badge">1</div>
                    <div class="step-text-s">Select a subject from the dropdown</div></div>
                <div class="step-item"><div class="step-num-badge">2</div>
                    <div class="step-text-s">Upload your syllabus or textbook as a <strong>PDF</strong></div></div>
                <div class="step-item"><div class="step-num-badge">3</div>
                    <div class="step-text-s">Click <strong>Build Index</strong> — topics are extracted automatically</div></div>
                <div class="step-item"><div class="step-num-badge">4</div>
                    <div class="step-text-s">Your AI tutor answers questions <strong>grounded in your syllabus</strong></div></div>
                <div class="step-item"><div class="step-num-badge">5</div>
                    <div class="step-text-s">Re-upload any time to update the index</div></div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Knowledge Graph
# ══════════════════════════════════════════════════════════════════════════════
with tab_kg:
    if not current:
        st.markdown("""
        <div class="empty-box" style="margin-top:16px;">
            <div class="e-icon">🕸️</div>
            <div class="e-title">No subjects yet</div>
            <div class="e-sub">Add and upload subjects first before building a Knowledge Graph.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        kg_l, kg_r = st.columns([1, 1], gap="large")
        with kg_l:
            st.markdown("#### Build Knowledge Graph")
            kg_subject    = st.selectbox("Subject", current, key="kg_subj_sel",
                                         label_visibility="collapsed")
            topics_for_kg = get_topics(kg_subject)
            kg_exists = False; cached_kg = None
            try:
                from kg.kg_engine import KnowledgeGraph
                kg_exists = KnowledgeGraph.exists(kg_subject)
                if kg_exists:
                    cached_kg = KnowledgeGraph.load(kg_subject)
            except Exception:
                pass

            if kg_exists and cached_kg:
                stats = cached_kg.stats() if cached_kg else {}
                st.markdown(f"""
                <div class="kg-stat-row">
                    <div><div class="kg-stat-num">{stats.get('nodes',0)}</div>
                         <div class="kg-stat-lbl">Concepts</div></div>
                    <div><div class="kg-stat-num">{stats.get('edges',0)}</div>
                         <div class="kg-stat-lbl">Relations</div></div>
                    <div style="font-size:0.8rem;color:{t['success']};font-weight:600;margin-left:8px;">
                        ✓ KG ready for <strong>{kg_subject}</strong></div>
                </div>
                """, unsafe_allow_html=True)
            elif topics_for_kg:
                st.info(f"📋 {len(topics_for_kg)} topics found — ready to build.")
            else:
                st.warning("⚠ Upload a PDF for this subject first.")

            if topics_for_kg:
                btn_lbl = "🔄 Rebuild KG" if kg_exists else "🕸️ Build Knowledge Graph"
                if st.button(btn_lbl, type="primary", use_container_width=True):
                    with st.spinner(f"Building KG for {kg_subject}… (30–60s)"):
                        try:
                            from kg.kg_engine import build_knowledge_graph, KnowledgeGraph
                            from groq import Groq
                            try:    api_key = st.secrets["GROQ_API_KEY"]
                            except:
                                try: api_key = st.secrets["supabase"]["GROQ_API_KEY"]
                                except: api_key = os.environ.get("GROQ_API_KEY", "")
                            client = Groq(api_key=api_key)
                            kg     = build_knowledge_graph(kg_subject, topics_for_kg, client, force_rebuild=True)
                            stats  = kg.stats()
                            st.success(f"✅ {stats['nodes']} concepts · {stats['edges']} relations")
                            ck = f"kg_{kg_subject.lower().strip()}"
                            if ck in st.session_state: del st.session_state[ck]
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ KG build failed: {e}")

        with kg_r:
            st.markdown("#### What is a Knowledge Graph?")
            st.markdown(f"""
            <div class="step-guide">
                <div class="step-item"><div class="step-num-badge">🕸</div>
                    <div class="step-text-s">Maps how topics in your syllabus <strong>relate to each other</strong> — prerequisites, dependencies, concepts.</div></div>
                <div class="step-item"><div class="step-num-badge">🎯</div>
                    <div class="step-text-s">Helps the AI <strong>detect prerequisite gaps</strong> when you struggle with a topic.</div></div>
                <div class="step-item"><div class="step-num-badge">✅</div>
                    <div class="step-text-s"><strong>Prevents hallucinations</strong> by keeping answers within your syllabus structure.</div></div>
                <div class="step-item"><div class="step-num-badge">⚡</div>
                    <div class="step-text-s">Takes <strong>30–60 seconds</strong> and only needs to be built once per subject.</div></div>
            </div>
            """, unsafe_allow_html=True)