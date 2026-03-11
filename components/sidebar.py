# components/sidebar.py
import streamlit as st

def render_sidebar():
    if not st.session_state.get("uid"):
        return

    p = st.session_state.profile
    subjects_list = p.get("subjects_list") or p.get("subject_list", "").split(",")

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=60)
        st.title("LLM-ITS")
        st.caption("Intelligent Tutoring System")
        st.divider()

        st.success(f"👤 {p['name']}")
        st.caption(f"📚 {p['education_level']}")
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["uid", "profile", "current_subject", "chat_history"]:
                st.session_state[key] = None if key != "chat_history" else []
            st.switch_page("app.py")

        st.divider()

        # ── Subjects (always visible) ─────────────────────────────────────
        st.markdown("**📚 My Subjects**")
        for subj in subjects_list:
            subj = subj.strip()
            is_active = st.session_state.get("study_subject") == subj
            if st.button(
                f"{'▶ ' if is_active else ''}{subj}",
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
        st.markdown("**🗂️ Navigation**")
        st.page_link("pages/1_Learn.py",          label="📖 Learn",          icon="📖")
        st.page_link("pages/4_Dashboard.py",      label="📊 Dashboard",      icon="📊")
        st.page_link("pages/5_UploadSyllabus.py", label="📄 Upload Syllabus",icon="📄")
        st.page_link("pages/6_Notes.py",          label="📝 Notes",          icon="📝")
        st.page_link("pages/7_XAI_Debug.py",      label="🔍 XAI Debug",      icon="🔍")
        st.page_link("pages/8_subjects.py",       label="📚 Subjects",       icon="📚")