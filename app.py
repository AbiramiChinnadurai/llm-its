"""
app.py  —  Main entry point
Run with: streamlit run app.py
"""

import streamlit as st
from database.db import init_db, create_profile, get_all_profiles, get_profile

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(
    page_title="LLM Intelligent Tutoring System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Session state defaults ────────────────────────────────────────────────────
if "uid"             not in st.session_state: st.session_state.uid             = None
if "profile"         not in st.session_state: st.session_state.profile         = None
if "current_subject" not in st.session_state: st.session_state.current_subject = None
if "chat_history"    not in st.session_state: st.session_state.chat_history    = []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=60)
    st.title("LLM-ITS")
    st.caption("Intelligent Tutoring System")
    st.divider()

    if st.session_state.uid:
        p = st.session_state.profile
        st.success(f"👤 {p['name']}")
        st.caption(f"📚 {p['education_level']}")
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["uid", "profile", "current_subject", "chat_history"]:
                st.session_state[key] = None if key != "chat_history" else []
            st.rerun()
        st.divider()
        st.page_link("pages/1_Study.py",         label="📖 Study",          icon="📖")
        st.page_link("pages/2_Quiz.py",           label="🧠 Quiz",           icon="🧠")
        st.page_link("pages/3_LearningPlan.py",   label="🗓️ Learning Plan",  icon="🗓️")
        st.page_link("pages/4_Dashboard.py",      label="📊 Dashboard",      icon="📊")
        st.page_link("pages/5_UploadSyllabus.py", label="📄 Upload Syllabus",icon="📄")

# ── Main page ─────────────────────────────────────────────────────────────────
if not st.session_state.uid:
    st.title("🎓 Welcome to the LLM Intelligent Tutoring System")
    st.markdown("""
    An AI-powered tutor that:
    - 📚 Learns from **your uploaded syllabus** (no hallucination)
    - 🧠 Tracks your **quiz performance** across sessions
    - 🔄 Adapts **how it explains** concepts when you struggle *(AEL)*
    - 🗓️ Generates a **personalized study plan** based on your progress
    """)
    st.divider()

    tab1, tab2 = st.tabs(["🆕 Register", "🔑 Login"])

    # ── REGISTER ──────────────────────────────────────────────────────────────
    with tab1:
        st.subheader("Create Your Profile")
        col1, col2 = st.columns(2)
        with col1:
            name      = st.text_input("Full Name *")
            age       = st.number_input("Age", min_value=10, max_value=60, value=20)
            edu_level = st.selectbox("Education Level", [
                "Secondary School", "Undergraduate", "Postgraduate", "Professional"
            ])
        with col2:
            subjects_input = st.text_input("Subjects (comma separated) *",
                                           placeholder="e.g. Data Structures, Economics")
            daily_hours    = st.slider("Daily Study Hours", 0.5, 8.0, 2.0, 0.5)
            deadline       = st.date_input("Target Completion Date")

        goals = st.text_area("Learning Goals", placeholder="e.g. Prepare for semester exams, understand core concepts...")

        if st.button("✅ Create Profile", type="primary", use_container_width=True):
            if not name or not subjects_input:
                st.error("Please fill in Name and Subjects.")
            else:
                subjects = [s.strip() for s in subjects_input.split(",") if s.strip()]
                uid = create_profile(
                    name, age, edu_level, subjects,
                    daily_hours, str(deadline), goals
                )
                st.session_state.uid     = uid
                st.session_state.profile = get_profile(uid)
                st.session_state.profile["subjects_list"] = subjects
                st.success(f"Profile created! Welcome, {name} 🎉")
                st.rerun()

    # ── LOGIN ──────────────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Select Your Profile")
        profiles = get_all_profiles()
        if not profiles:
            st.info("No profiles yet. Please register first.")
        else:
            options = {f"{p['name']} (ID: {p['uid']})": p["uid"] for p in profiles}
            choice  = st.selectbox("Select Profile", list(options.keys()))
            if st.button("🔑 Login", type="primary", use_container_width=True):
                uid = options[choice]
                profile = get_profile(uid)
                st.session_state.uid     = uid
                st.session_state.profile = profile
                st.session_state.profile["subjects_list"] = profile["subject_list"].split(",")
                st.rerun()
else:
    # Logged in — show dashboard summary
    p = st.session_state.profile
    st.title(f"Welcome back, {p['name']}! 👋")
    st.markdown("Use the **sidebar** to navigate to Study, Quiz, Learning Plan, or Dashboard.")

    col1, col2, col3 = st.columns(3)
    from database.db import get_subject_summary, get_quiz_history
    summaries = get_subject_summary(st.session_state.uid)
    history   = get_quiz_history(st.session_state.uid)

    col1.metric("📚 Subjects",      len(p["subject_list"].split(",")))
    col2.metric("🧠 Quiz Attempts", len(history))
    col3.metric("🏆 Strong Subjects",
                len([s for s in summaries if s["strength_label"] == "Strong"]))

    if summaries:
        st.divider()
        st.subheader("📊 Subject Mastery Overview")
        cols = st.columns(len(summaries))
        color_map = {"Strong": "🟢", "Moderate": "🟡", "Weak": "🔴"}
        for col, s in zip(cols, summaries):
            icon = color_map.get(s["strength_label"], "⚪")
            col.metric(
                f"{icon} {s['subject']}",
                f"{s['avg_accuracy']:.1f}%",
                s["strength_label"]
            )
