# components/sidebar.py
import streamlit as st

def render_sidebar():
    if not st.session_state.get("uid"):
        return

    p = st.session_state.profile
    subjects_list = p.get("subjects_list") or p.get("subject_list", "").split(",")

    with st.sidebar:
        # ── Brand ─────────────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;padding:4px 0 16px 0;">
            <img src="https://img.icons8.com/fluency/96/graduation-cap.png" width="36"/>
            <div>
                <div style="font-weight:800;font-size:1.1rem;color:#f0f6ff;">LLM-ITS</div>
                <div style="font-size:0.7rem;color:#4a6080;">Intelligent Tutoring System</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        </style>
        """, unsafe_allow_html=True)

        # ── User pill ─────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="background:#0d1524;border:1px solid #1a2540;border-radius:10px;
                    padding:10px 14px;margin-bottom:12px;">
            <div style="font-size:0.78rem;font-weight:600;color:#d4dbe8;">👤 {p['name']}</div>
            <div style="font-size:0.7rem;color:#4a6080;">{p['education_level']}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True):
            for key in ["uid", "profile", "current_subject", "chat_history"]:
                st.session_state[key] = None if key != "chat_history" else []
            st.switch_page("app.py")

        st.divider()

        # ── My Subjects ───────────────────────────────────────────────────
        st.markdown('<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#4a6080;margin-bottom:8px;">My Subjects</div>', unsafe_allow_html=True)

        for subj in subjects_list:
            subj = subj.strip()
            is_active = st.session_state.get("study_subject") == subj
            if st.button(
                f"{'▶  ' if is_active else '      '}{subj}",
                key=f"sidebar_subj_{subj}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state["study_subject"]  = subj
                st.session_state["selected_topic"] = None
                st.session_state["chat_history"]   = []
                st.switch_page("pages/1_Learn.py")

        st.divider()

        # ── Navigation ────────────────────────────────────────────────────
        st.markdown('<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#4a6080;margin-bottom:8px;">Navigation</div>', unsafe_allow_html=True)

        st.page_link("pages/1_Learn.py",          label="📖  Learn")
        st.page_link("pages/4_Dashboard.py",      label="📊  Dashboard")
        st.page_link("pages/5_UploadSyllabus.py", label="📄  Upload Syllabus")
        st.page_link("pages/6_Notes.py",          label="📝  Notes")
        st.page_link("pages/7_XAI_Debug.py",      label="🔍  XAI Debug")
        st.page_link("pages/8_subjects.py",       label="⚙️  Manage Subjects")