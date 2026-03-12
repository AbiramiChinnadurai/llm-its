# components/sidebar.py
import streamlit as st

def render_sidebar():
    # Import inside function to prevent circular imports
    from utils.theme import render_theme_toggle, get_theme

    with st.sidebar:
        st.markdown("""
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        section[data-testid="stSidebar"] button {
            -webkit-user-select: none !important;
            user-select: none !important;
        }
        </style>
        """, unsafe_allow_html=True)

        t = get_theme()
        title_color = t["text_primary"]
        sub_color   = t["text_muted"]

        # ── Brand ─────────────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:4px 0 16px 0;">
            <img src="https://img.icons8.com/fluency/96/graduation-cap.png" width="36"/>
            <div>
                <div style="font-weight:800;font-size:1.1rem;color:{title_color};">LLM-ITS</div>
                <div style="font-size:0.7rem;color:{sub_color};">Intelligent Tutoring System</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Theme toggle ───────────────────────────────────────────────────────
        render_theme_toggle()

        # ── Not logged in ──────────────────────────────────────────────────────
        if not st.session_state.get("uid"):
            st.divider()
            st.markdown(
                f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;'
                f'text-transform:uppercase;color:{t["text_faint"]};margin-bottom:8px;">Navigation</div>',
                unsafe_allow_html=True
            )
            st.page_link("app.py", label="Home — Login / Register", icon="🏠")
            return

        p = st.session_state.profile
        if not p:
            st.session_state.uid = None
            st.rerun()
            return

        # ── Parse subjects ─────────────────────────────────────────────────────
        raw = p.get("subjects_list") or p.get("subject_list", "")
        if isinstance(raw, list):
            subjects_list = [s.strip() for s in raw if s.strip()]
        else:
            subjects_list = [s.strip() for s in str(raw).split(",") if s.strip()]

        # ── User pill ──────────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="background:{t['card_bg']};border:1px solid {t['border']};border-radius:10px;
                    padding:10px 14px;margin-bottom:12px;">
            <div style="font-size:0.78rem;font-weight:600;color:{t['text_secondary']};">👤 {p['name']}</div>
            <div style="font-size:0.7rem;color:{t['text_muted']};">{p['education_level']}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True, key="sidebar_logout"):
            for key in ["uid", "profile", "current_subject", "chat_history",
                        "study_subject", "selected_topic"]:
                st.session_state[key] = None if key != "chat_history" else []
            st.switch_page("app.py")

        st.divider()

        # ── Manage Subjects button — above navigation, prominent ──────────────
        st.markdown(
            f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;'
            f'text-transform:uppercase;color:{t["text_faint"]};margin-bottom:8px;">Subjects</div>',
            unsafe_allow_html=True
        )
        if st.button("⚙️  Manage Subjects", use_container_width=True,
                     key="sidebar_manage_subjects",
                     type="primary"):
            st.switch_page("pages/8_subjects.py")

        st.divider()

        # ── My Subjects ────────────────────────────────────────────────────────
        st.markdown(
            f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;'
            f'text-transform:uppercase;color:{t["text_faint"]};margin-bottom:8px;">My Subjects</div>',
            unsafe_allow_html=True
        )

        if subjects_list:
            for subj in subjects_list:
                is_active = st.session_state.get("study_subject") == subj
                label     = f"▶  {subj}" if is_active else subj
                if st.button(label, key=f"sidebar_subj_{subj}", use_container_width=True):
                    st.session_state["study_subject"]  = subj
                    st.session_state["selected_topic"] = None
                    st.session_state["chat_history"]   = []
                    st.switch_page("pages/1_Learn.py")
        else:
            st.caption("No subjects yet — click Manage Subjects above to add some.")

        st.divider()

        # ── Navigation ─────────────────────────────────────────────────────────
        st.markdown(
            f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;'
            f'text-transform:uppercase;color:{t["text_faint"]};margin-bottom:8px;">Navigation</div>',
            unsafe_allow_html=True
        )
        st.page_link("pages/4_Dashboard.py", label="📊  Dashboard")
        st.page_link("pages/6_Notes.py",     label="📝  Notes")
        st.page_link("pages/7_XAI_Debug.py", label="🔍  XAI Debug")