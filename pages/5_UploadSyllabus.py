"""
pages/5_UploadSyllabus.py
Upload PDF → auto-extract topics from headings → save to DB (no manual editing).
"""

import streamlit as st
import os
import tempfile
from rag.rag_pipeline import build_faiss_index, index_exists, extract_topics_from_pdf
from database.db import save_topics, get_topics, topics_exist

st.set_page_config(page_title="Upload Syllabus | LLM-ITS", page_icon="📄", layout="wide")

if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

st.title("📄 Upload Syllabus / Curriculum PDF")
st.caption("Upload your subject PDFs. Topics are auto-detected from chapter/section headings.")
st.divider()

# ── Subject status cards ──────────────────────────────────────────────────────
st.subheader("📚 Subject Status")
cols = st.columns(len(subjects))
for col, subj in zip(cols, subjects):
    indexed    = index_exists(subj)
    has_topics = topics_exist(subj)
    topic_count = len(get_topics(subj))
    if indexed and has_topics:
        col.success(f"✅ {subj}\n{topic_count} topics ready")
    elif indexed:
        col.warning(f"⚠️ {subj}\nIndexed — no topics")
    else:
        col.error(f"❌ {subj}\nNot set up yet")

st.divider()

# ── Upload form ───────────────────────────────────────────────────────────────
st.subheader("⬆️ Upload PDF")
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

# ── Show existing topics ──────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Extracted Topics by Subject")
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
