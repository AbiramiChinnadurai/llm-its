"""
pages/8_Subjects.py
─────────────────────────────────────────────────────────────────────────────
Subject Manager + Syllabus Upload — all in one clean page.
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import os
import tempfile
from database.db import get_topics, topics_exist, save_topics, get_connection
from components.sidebar import render_sidebar
from utils.theme import inject_theme, render_theme_toggle, get_theme

st.set_page_config(page_title="Subjects | LLM-ITS", page_icon="📚", layout="wide")

render_sidebar()

# ── Theme toggle in sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    render_theme_toggle()

# ── Auth ──────────────────────────────────────────────────────────────────────
if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid     = st.session_state.uid
profile = st.session_state.profile

# ── CSS ───────────────────────────────────────────────────────────────────────
inject_theme()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(160deg,#0d1524 0%,#080c14 60%);
            border:1px solid #1a2540; border-radius:20px;
            padding:28px 36px; margin-bottom:28px; position:relative; overflow:hidden;">
  <div style="position:absolute;right:32px;top:50%;transform:translateY(-50%);
              font-family:'Syne',sans-serif;font-size:5rem;font-weight:800;
              color:rgba(255,255,255,0.022);letter-spacing:0.15em;
              pointer-events:none;user-select:none;">SUBJECTS</div>
  <div style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#f0f6ff;margin-bottom:4px;">
    📚 Subject Manager
  </div>
  <div style="color:#4a6080;font-size:0.88rem;">
    Manage your subjects and upload syllabi — everything in one place.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_current_subjects():
    p   = st.session_state.profile
    raw = p.get("subjects_list") or p.get("subject_list", "")
    if isinstance(raw, list):
        return [s.strip() for s in raw if s.strip()]
    return [s.strip() for s in str(raw).split(",") if s.strip()]


def save_subjects_to_db(uid, subjects):
    """Save subject list using existing get_connection() from db.py."""
    try:
        conn = get_connection()
        c    = conn.cursor()
        c.execute(
            "UPDATE learner_profile SET subject_list = %s WHERE uid = %s",
            (", ".join(subjects), uid)
        )
        conn.commit()
        conn.close()
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
    """Safely get PDF/KG status with lazy imports so missing modules don't crash the page."""
    has_topics = bool(get_topics(subj))
    has_kg     = False
    has_index  = False
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

# ══════════════════════════════════════════════════════════════════════════════
col_left, col_right = st.columns([1, 1], gap="large")

# ══ LEFT ══════════════════════════════════════════════════════════════════════
with col_left:

    # ── Subject list ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-title" style="color:#3b82f6;">📋 My Subjects</div>', unsafe_allow_html=True)

    if not current:
        st.markdown("""
        <div style="background:#1c0808;border:1px solid #7f1d1d;border-radius:12px;
                    padding:20px;text-align:center;color:#f87171;font-size:0.85rem;">
            ⚠️ No subjects yet. Add one using the panel on the right.
        </div>
        """, unsafe_allow_html=True)
    else:
        for i, subj in enumerate(current):
            has_topics, has_kg, has_index = get_subject_status(subj)

            if has_topics and has_kg:
                badge = '<span class="badge badge-green">✓ PDF + KG</span>'
            elif has_index or has_topics:
                badge = '<span class="badge badge-blue">✓ PDF indexed</span>'
            else:
                badge = '<span class="badge badge-yellow">⚠ No PDF yet</span>'

            c_num, c_name, c_up, c_del = st.columns([0.3, 3.2, 0.5, 0.5])

            with c_num:
                st.markdown(f"""
                <div style="width:30px;height:30px;border-radius:8px;background:#0d1a2e;
                            border:1px solid #1d4ed8;display:flex;align-items:center;
                            justify-content:center;font-size:0.75rem;font-weight:800;
                            color:#60a5fa;margin-top:6px;">{i+1}</div>
                """, unsafe_allow_html=True)

            with c_name:
                st.markdown(f"""
                <div class="subj-card">
                    <span class="subj-card-name">{subj}</span>{badge}
                </div>
                """, unsafe_allow_html=True)

            with c_up:
                if i > 0:
                    if st.button("↑", key=f"up_{i}", use_container_width=True):
                        lst = st.session_state.subjects_edit_list
                        lst[i], lst[i-1] = lst[i-1], lst[i]
                        st.rerun()

            with c_del:
                if st.button("🗑", key=f"del_{i}", use_container_width=True):
                    st.session_state[f"confirm_del_{i}"] = True
                    st.rerun()

            if st.session_state.get(f"confirm_del_{i}"):
                st.markdown(f"""
                <div style="background:#1c0808;border:1px solid #7f1d1d;border-radius:10px;
                            padding:10px 14px;margin:4px 0 8px 0;">
                    <span style="font-size:0.8rem;color:#f87171;">
                        Remove <strong>{subj}</strong>? This won't delete your uploaded PDFs.
                    </span>
                </div>
                """, unsafe_allow_html=True)
                y, n = st.columns(2)
                with y:
                    if st.button("✓ Remove", key=f"yes_{i}", type="primary", use_container_width=True):
                        st.session_state.subjects_edit_list = [s for s in current if s != subj]
                        st.session_state.pop(f"confirm_del_{i}", None)
                        st.rerun()
                with n:
                    if st.button("✗ Cancel", key=f"no_{i}", use_container_width=True):
                        st.session_state.pop(f"confirm_del_{i}", None)
                        st.rerun()

    # ── Save / Reset ──────────────────────────────────────────────────────────
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

    st.divider()

    # ── Upload Syllabus ───────────────────────────────────────────────────────
    st.markdown('<div class="section-title" style="color:#10b981;">⬆️ Upload Syllabus PDF</div>', unsafe_allow_html=True)

    if not current:
        st.caption("Save subjects first, then upload a PDF for each.")
    else:
        selected_subject = st.selectbox("Select subject to upload for", current, key="upload_subj_sel")
        uploaded_file    = st.file_uploader("Choose PDF", type=["pdf"], key="syllabus_uploader")

        if uploaded_file:
            st.markdown(f"""
            <div style="background:#0d1524;border:1px solid #1a2540;border-radius:10px;
                        padding:10px 14px;margin-bottom:12px;font-size:0.8rem;color:#8090a8;">
                📄 <strong style="color:#d4dbe8;">{uploaded_file.name}</strong>
                &nbsp;·&nbsp; {round(uploaded_file.size/1024, 1)} KB
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔨 Build Index + Extract Topics", type="primary", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name
                try:
                    from rag.rag_pipeline import build_faiss_index, extract_topics_from_pdf

                    prog = st.progress(0,  text="Reading PDF...")
                    prog.progress(25, text="Extracting topics from headings...")
                    topics      = extract_topics_from_pdf(tmp_path)
                    save_topics(selected_subject, topics)

                    prog.progress(55, text="Building FAISS index...")
                    chunk_count = build_faiss_index(selected_subject, tmp_path)

                    prog.progress(100, text="Done!")
                    st.success(f"✅ **{chunk_count} chunks** indexed · **{len(topics)} topics** extracted")

                    if topics:
                        with st.expander(f"📋 {len(topics)} topics found", expanded=True):
                            tcols = st.columns(3)
                            for idx, t in enumerate(topics):
                                tcols[idx % 3].markdown(f"• {t}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

    st.divider()

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    st.markdown('<div class="section-title" style="color:#8b5cf6;">🕸️ Knowledge Graph</div>', unsafe_allow_html=True)

    if not current:
        st.caption("Add and upload subjects first.")
    else:
        kg_subject    = st.selectbox("Select subject", current, key="kg_subj_sel")
        topics_for_kg = get_topics(kg_subject)

        kg_exists = False
        cached_kg = None
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
            <div style="background:#081810;border:1px solid #065f35;border-radius:12px;
                        padding:14px;display:flex;gap:24px;align-items:center;margin-bottom:10px;">
                <div style="text-align:center;">
                    <div style="font-size:1.6rem;font-weight:800;color:#34d399;">{stats.get('nodes',0)}</div>
                    <div style="font-size:0.65rem;color:#2d5a40;text-transform:uppercase;">concepts</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:1.6rem;font-weight:800;color:#10b981;">{stats.get('edges',0)}</div>
                    <div style="font-size:0.65rem;color:#2d5a40;text-transform:uppercase;">relations</div>
                </div>
                <div style="font-size:0.78rem;color:#34d399;font-weight:600;">✓ KG ready for {kg_subject}</div>
            </div>
            """, unsafe_allow_html=True)

        if topics_for_kg:
            btn_lbl = "🔄 Rebuild KG" if kg_exists else "🕸️ Build Knowledge Graph"
            if st.button(btn_lbl, type="primary", use_container_width=True):
                with st.spinner(f"Building Knowledge Graph for {kg_subject}... (30–60s)"):
                    try:
                        from kg.kg_engine import build_knowledge_graph, KnowledgeGraph
                        from groq import Groq

                        try:
                            api_key = st.secrets["GROQ_API_KEY"]
                        except Exception:
                            try:
                                api_key = st.secrets["supabase"]["GROQ_API_KEY"]
                            except Exception:
                                api_key = os.environ.get("GROQ_API_KEY", "")

                        client = Groq(api_key=api_key)
                        kg     = build_knowledge_graph(kg_subject, topics_for_kg, client, force_rebuild=True)
                        stats  = kg.stats()
                        st.success(f"✅ KG built! {stats['nodes']} concepts, {stats['edges']} relations")
                        cache_key = f"kg_{kg_subject.lower().strip()}"
                        if cache_key in st.session_state:
                            del st.session_state[cache_key]
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ KG build failed: {e}")
        else:
            st.info("Upload a PDF for this subject first to extract topics.")


# ══ RIGHT ══════════════════════════════════════════════════════════════════════
with col_right:

    st.markdown('<div class="section-title" style="color:#10b981;">➕ Add Subject</div>', unsafe_allow_html=True)

    new_subject = st.text_input(
        "Subject name",
        placeholder="e.g. Machine Learning, Operating Systems...",
        key="new_subject_input",
        label_visibility="collapsed"
    )
    if st.button("➕ Add Subject", type="primary", use_container_width=True,
                 disabled=not new_subject.strip()):
        cleaned = new_subject.strip().title()
        if cleaned in st.session_state.subjects_edit_list:
            st.warning(f"**{cleaned}** already added.")
        elif len(st.session_state.subjects_edit_list) >= 8:
            st.warning("Maximum 8 subjects.")
        else:
            st.session_state.subjects_edit_list.append(cleaned)
            st.rerun()

    st.divider()

    st.markdown('<div class="section-title" style="color:#4a6080;">⚡ Quick Add</div>', unsafe_allow_html=True)

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
                st.markdown(f"""
                <div style="background:#081810;border:1px solid #065f35;border-radius:8px;
                            padding:7px 10px;margin-bottom:4px;font-size:0.75rem;color:#34d399;">
                    ✓ {icon} {subj}
                </div>
                """, unsafe_allow_html=True)
            else:
                if st.button(f"{icon} {subj}", key=f"quick_{subj}", use_container_width=True):
                    if len(st.session_state.subjects_edit_list) >= 8:
                        st.warning("Maximum 8 subjects.")
                    else:
                        st.session_state.subjects_edit_list.append(subj)
                        st.rerun()

    st.divider()

    st.markdown("""
    <div style="background:#0d1524;border:1px solid #1a2540;border-radius:14px;padding:18px 20px;">
        <div style="font-size:0.7rem;font-weight:700;color:#3b82f6;
                    text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px;">
            ℹ️ Setup Guide
        </div>
        <div class="step-row">
            <div class="step-num">1</div>
            <div class="step-text">Add your subjects using Quick Add or the text field</div>
        </div>
        <div class="step-row">
            <div class="step-num">2</div>
            <div class="step-text">Click <strong style="color:#d4dbe8;">Save Changes</strong> to persist them</div>
        </div>
        <div class="step-row">
            <div class="step-num">3</div>
            <div class="step-text">Upload a syllabus PDF for each subject</div>
        </div>
        <div class="step-row">
            <div class="step-num">4</div>
            <div class="step-text">Build the Knowledge Graph for smarter answers</div>
        </div>
        <div class="step-row">
            <div class="step-num">5</div>
            <div class="step-text">Click your subject in the sidebar to start studying!</div>
        </div>
    </div>
    """, unsafe_allow_html=True)