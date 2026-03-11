"""
pages/5_UploadSyllabus.py
Upload PDF → auto-extract topics from headings → save to DB (no manual editing).
"""

import streamlit as st
import os
import tempfile
from rag.rag_pipeline import build_faiss_index, index_exists, extract_topics_from_pdf
from database.db import save_topics, get_topics, topics_exist
from kg.kg_engine import build_knowledge_graph, KnowledgeGraph

st.set_page_config(page_title="Upload Syllabus | LLM-ITS", page_icon="📄", layout="wide")

if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=Instrument+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'Instrument Sans', sans-serif; }
.stApp { background: #080c14; color: #d4dbe8; }

.hud-header {
    background: linear-gradient(160deg, #0d1524 0%, #080c14 60%);
    border: 1px solid #1a2540; border-radius: 20px;
    padding: 32px 40px; margin-bottom: 32px;
    position: relative; overflow: hidden;
}
.hud-header::after {
    content: 'UPLOAD'; position: absolute; right: 32px; top: 50%;
    transform: translateY(-50%); font-family: 'Syne', sans-serif;
    font-size: 5rem; font-weight: 800; color: rgba(255,255,255,0.025);
    letter-spacing: 0.15em; pointer-events: none; user-select: none;
}
.hud-title { font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800; color:#f0f6ff; margin:0 0 4px 0; }
.hud-sub   { color:#4a6080; font-size:0.88rem; margin:0; font-weight:300; }

.hud-cell { background:#0d1524; border:1px solid #1a2540; border-radius:14px; padding:18px 20px; position:relative; overflow:hidden; }
.hud-cell::before { content:''; position:absolute; bottom:0; left:0; right:0; height:2px; }
.hud-cell.completed::before { background:linear-gradient(90deg,#10b981,#059669); }
.hud-cell.pending::before   { background:linear-gradient(90deg,#3b82f6,#1d4ed8); }
.hud-cell.missing::before   { background:linear-gradient(90deg,#ef4444,#dc2626); }

.hud-num { font-family:'Syne',sans-serif; font-size:1.8rem; font-weight:800; line-height:1; margin-bottom:4px; color:#f0f6ff; }
.hud-label { font-size:0.7rem; color:#4a6080; text-transform:uppercase; letter-spacing:0.1em; font-weight:600; }

.stButton > button {
    border-radius:10px !important; font-family:'Instrument Sans',sans-serif !important;
    font-size:0.84rem !important; font-weight:500 !important;
    transition:all 0.2s !important; border:1px solid #1a2540 !important;
    background:#0d1524 !important; color:#8090a8 !important;
}
.stButton > button:hover { background:#1a2540 !important; border-color:#3b82f6 !important; color:#d4dbe8 !important; transform: translateY(-2px) !important; }
button[kind="primary"] {
    background:linear-gradient(135deg,#2563eb,#1d4ed8) !important;
    border-color:#3b82f6 !important; color:#fff !important; font-weight:600 !important;
}
button[kind="primary"]:hover {
    background:linear-gradient(135deg,#3b82f6,#2563eb) !important;
    box-shadow:0 4px 20px rgba(37,99,235,0.35) !important;
}
hr { border-color:#1a2540 !important; }
[data-baseweb="select"] { background:#0d1524 !important; border-color:#1a2540 !important; border-radius:10px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hud-header">
    <h1 class="hud-title">📄 Upload Syllabus / Curriculum PDF</h1>
    <p class="hud-sub">Upload your subject PDFs. Topics are auto-detected from chapter/section headings.</p>
</div>
""", unsafe_allow_html=True)

# ── Subject status cards ──────────────────────────────────────────────────────
st.markdown('<div class="hud-label" style="font-size:1rem; margin-bottom:16px; color:#d4dbe8;">📚 Subject Status</div>', unsafe_allow_html=True)
cols = st.columns(len(subjects))
for col, subj in zip(cols, subjects):
    indexed    = index_exists(subj)
    has_topics = topics_exist(subj)
    topic_count = len(get_topics(subj))
    with col:
        if indexed and has_topics:
            st.markdown(f"""
            <div class="hud-cell completed">
                <div class="hud-num">{topic_count}</div>
                <div class="hud-label" style="color:#10b981;">✅ {subj} REAdY</div>
            </div>
            """, unsafe_allow_html=True)
        elif indexed:
            st.markdown(f"""
            <div class="hud-cell pending">
                <div class="hud-num">0</div>
                <div class="hud-label" style="color:#3b82f6;">⚠️ {subj} (NO TOPICS)</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="hud-cell missing">
                <div class="hud-num">--</div>
                <div class="hud-label" style="color:#ef4444;">❌ {subj} (NOT SET UP)</div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ── Upload form ───────────────────────────────────────────────────────────────
st.markdown('<div class="hud-label" style="font-size:1rem; margin-bottom:16px; color:#d4dbe8;">⬆️ Upload PDF</div>', unsafe_allow_html=True)
selected_subject = st.selectbox("Select Subject for this PDF", subjects)
uploaded_file    = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file:
    st.info(f"📄 **{uploaded_file.name}** — {round(uploaded_file.size/1024, 1)} KB")

    if st.button("🔨 Build Index + Extract Topics", type="primary", use_container_width=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        try:
            prog = st.progress(0, text="Step 1/3 — Reading PDF...")
            from rag.rag_pipeline import extract_text_from_pdf, chunk_text
            import faiss, numpy as np, pickle
            from sentence_transformers import SentenceTransformer

            prog.progress(20, text="Step 2/3 — Extracting topics from headings...")
            topics = extract_topics_from_pdf(tmp_path)
            save_topics(selected_subject, topics)

            prog.progress(50, text="Step 3/3 — Building FAISS index (this may take a minute)...")
            chunk_count = build_faiss_index(selected_subject, tmp_path)

            prog.progress(100, text="Done!")
            st.success(f"✅ Done! **{chunk_count} chunks** indexed | **{len(topics)} topics** extracted")

            if topics:
                st.subheader(f"📋 Topics found in {selected_subject}:")
                # Show in 3 columns
                tcols = st.columns(3)
                for i, t in enumerate(topics):
                    tcols[i % 3].markdown(f"• {t}")
        except Exception as e:
            st.error(f"❌ Error: {e}")
        finally:
            os.unlink(tmp_path)

# ── Build Knowledge Graph ────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="hud-label" style="font-size:1rem; margin-bottom:16px; color:#d4dbe8;">🕸️ Knowledge Graph</div>', unsafe_allow_html=True)

kg_cols = st.columns(len(subjects))
for kg_col, subj in zip(kg_cols, subjects):
    with kg_col:
        kg_exists = KnowledgeGraph.exists(subj)
        topics_for_kg = get_topics(subj)
        if kg_exists:
            cached_kg = KnowledgeGraph.load(subj)
            stats = cached_kg.stats() if cached_kg else {}
            st.markdown(f"""
<div style="background:#081810;border:1px solid #065f35;border-radius:12px;padding:14px;text-align:center;margin-bottom:8px;">
  <div style="font-size:1.4rem;font-weight:800;color:#34d399;">{stats.get('nodes',0)}</div>
  <div style="font-size:0.68rem;color:#2d5a40;text-transform:uppercase;letter-spacing:0.1em;">concepts</div>
  <div style="font-size:0.68rem;color:#2d5a40;margin-top:2px;">{stats.get('edges',0)} relations</div>
  <div style="font-size:0.7rem;color:#10b981;margin-top:6px;font-weight:600;">✓ KG Ready — {subj}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:12px;padding:14px;text-align:center;margin-bottom:8px;">
  <div style="font-size:1.4rem;">🕸️</div>
  <div style="font-size:0.7rem;color:#4a6080;margin-top:4px;">{subj}</div>
  <div style="font-size:0.68rem;color:#2a3a50;margin-top:2px;">KG not built yet</div>
</div>""", unsafe_allow_html=True)

        if topics_for_kg:
            btn_label = "🔄 Rebuild KG" if kg_exists else "🕸️ Build KG"
            if st.button(btn_label, key=f"build_kg_{subj}", use_container_width=True):
                with st.spinner(f"Building Knowledge Graph for {subj}... (30-60s)"):
                    try:
                        import os
                        try:
                            api_key = st.secrets["GROQ_API_KEY"]
                        except Exception:
                            try:
                                api_key = st.secrets["supabase"]["GROQ_API_KEY"]
                            except Exception:
                                api_key = os.environ.get("GROQ_API_KEY", "")
                        from groq import Groq
                        client = Groq(api_key=api_key)
                        kg = build_knowledge_graph(subj, topics_for_kg, client, force_rebuild=True)
                        stats = kg.stats()
                        st.success(f"✅ KG built! {stats['nodes']} concepts, {stats['edges']} prerequisite relations")
                        # Clear session state cache so it reloads
                        cache_key = f"kg_{subj.lower().strip()}"
                        if cache_key in st.session_state:
                            del st.session_state[cache_key]
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ KG build failed: {e}")
        else:
            st.caption("Upload PDF first to extract topics")

# ── Show existing topics ──────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="hud-label" style="font-size:1rem; margin-bottom:16px; color:#d4dbe8;">📋 Extracted Topics by Subject</div>', unsafe_allow_html=True)
for subj in subjects:
    topics = get_topics(subj)
    if topics:
        with st.expander(f"📚 {subj} — {len(topics)} topics", expanded=False):
            tcols = st.columns(3)
            for i, t in enumerate(topics):
                tcols[i % 3].markdown(f"• {t}")
            if st.button(f"🔄 Re-upload to refresh topics for {subj}",
                         key=f"reup_{subj}", use_container_width=True):
                st.info("Upload a new PDF above to re-extract topics.")
    else:
        st.warning(f"⚠️ **{subj}** — No topics yet. Upload PDF above.")
