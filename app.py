"""
app.py  —  Main entry point
Run with: streamlit run app.py
"""

import streamlit as st
from database.db import (init_db, create_profile, get_all_profiles, get_profile,
                          get_subject_summary, get_quiz_history,
                          get_xp, get_streak, get_level_title, get_xp_progress)

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
from components.sidebar import render_sidebar
render_sidebar()

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
    content: 'LLM-ITS'; position: absolute; right: 32px; top: 50%;
    transform: translateY(-50%); font-family: 'Syne', sans-serif;
    font-size: 5rem; font-weight: 800; color: rgba(255,255,255,0.025);
    letter-spacing: 0.15em; pointer-events: none; user-select: none;
}
.hud-title { font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800; color:#f0f6ff; margin:0 0 4px 0; }
.hud-sub   { color:#4a6080; font-size:0.88rem; margin:0; font-weight:300; }

.day-card {
    background: #0d1524; border: 1px solid #1a2540;
    border-radius: 14px; padding: 20px;
    transition: all 0.3s;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Hide Streamlit's default page nav */
[data-testid="stSidebarNav"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Main page ─────────────────────────────────────────────────────────────────
if not st.session_state.uid:
    st.markdown("""
    <div class="hud-header">
        <h1 class="hud-title">🎓 Intelligent Tutoring System</h1>
        <p class="hud-sub">An AI-powered tutor that learns from your uploaded syllabus (no hallucination), tracks your quiz performance across sessions, adapts how it explains concepts when you struggle, and generates a personalized study plan based on your progress.</p>
    </div>
    """, unsafe_allow_html=True)

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

        goals = st.text_area("Learning Goals", placeholder="e.g. Prepare for semester exams...")

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
                st.session_state.profile["subjects_list"] = profile.get("subject_list", "").split(",")
                st.rerun()

else:
    # ── Logged in dashboard ───────────────────────────────────────────────────
    p = st.session_state.profile
    uid = st.session_state.uid

    st.title(f"Welcome back, {p['name']}! 👋")
    st.markdown("Use the **sidebar** to navigate to Study, Quiz, Learning Plan, or Dashboard.")

    # ── Basic stats ───────────────────────────────────────────────────────────
    summaries = get_subject_summary(uid)
    history   = get_quiz_history(uid)

    col1, col2, col3 = st.columns(3)
    subject_list = p.get("subject_list") or ",".join(p.get("subjects_list", []))
    col1.metric("📚 Subjects",       len(p["subject_list"].split(",")))
    col2.metric("🧠 Quiz Attempts",  len(history))
    col3.metric("🏆 Strong Subjects", len([s for s in summaries if s["strength_label"] == "Strong"]))

    # ── 🎮 Gamification Dashboard ─────────────────────────────────────────────
    st.divider()
    st.subheader("🎮 Your Progress")

    xp_data     = get_xp(uid)
    streak_data = get_streak(uid)

    total_xp       = xp_data.get("total_xp", 0)
    level          = xp_data.get("level", 1)
    current_streak = streak_data.get("current_streak", 0)
    longest_streak = streak_data.get("longest_streak", 0)

    xp_in_level, xp_needed = get_xp_progress(total_xp, level)
    level_title  = get_level_title(level)
    progress_pct = xp_in_level / xp_needed if xp_needed > 0 else 0

    g1, g2, g3, g4 = st.columns(4)
    g1.metric("⭐ Total XP",       total_xp)
    g2.metric("🏅 Level",          f"{level} — {level_title}")
    streak_icon = "🔥" if current_streak >= 3 else "📅"
    g3.metric(f"{streak_icon} Streak", f"{current_streak} days")
    g4.metric("🏆 Best Streak",    f"{longest_streak} days")

    st.markdown(f"**Level Progress:** {xp_in_level} / {xp_needed} XP to next level")
    st.progress(progress_pct)

    if current_streak >= 7:
        st.success(f"🔥 {'🔥' * min(current_streak, 10)} Amazing! {current_streak} days in a row!")
    elif current_streak >= 3:
        st.info(f"🔥 {'🔥' * current_streak} {current_streak} day streak — keep it up!")
    elif current_streak > 0:
        st.info(f"📅 {current_streak} day streak — study today to keep it going!")
    else:
        st.warning("📅 Study today to start your streak!")

    with st.expander("📊 Level Milestones"):
        levels = {
            1: ("🌱 Seedling",  0),
            2: ("📖 Learner",   100),
            3: ("🔥 Scholar",   200),
            4: ("⚡ Expert",    300),
            5: ("🏆 Master",    400),
        }
        for lvl, (title, xp_req) in levels.items():
            if lvl < level:
                st.markdown(f"✅ Level {lvl}: {title} *(unlocked)*")
            elif lvl == level:
                st.markdown(f"⭐ **Level {lvl}: {title} ← YOU ARE HERE**")
            else:
                st.markdown(f"🔒 Level {lvl}: {title} *(need {xp_req} XP)*")

    # ── Subject mastery ───────────────────────────────────────────────────────
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
