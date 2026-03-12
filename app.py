"""
app.py  —  Main entry point
Run with: streamlit run app.py
"""

import streamlit as st
from database.db import (init_db, create_profile, get_all_profiles, get_profile,
                          get_profile_by_email,
                          get_subject_summary, get_quiz_history,
                          get_xp, get_streak, get_level_title, get_xp_progress)
from utils.theme import inject_theme, render_theme_toggle

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
if "theme"           not in st.session_state: st.session_state.theme           = "dark"

# ── Sidebar ───────────────────────────────────────────────────────────────────
from components.sidebar import render_sidebar
render_sidebar()

# ── Theme CSS (dark + light) ───────────────────────────────────────────────────
inject_theme()

st.markdown("""
<style>
/* Hide Streamlit's default page nav */
[data-testid="stSidebarNav"] { display: none !important; }

/* ══════════════════════════════════════════════════════════════════
   LANDING PAGE — Hero & Auth
══════════════════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=Instrument+Sans:wght@300;400;500;600&display=swap');

/* ── Hero banner ── */
.hero-wrap {
    position: relative;
    overflow: hidden;
    border-radius: 24px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    padding: 56px 52px 48px;
    margin-bottom: 32px;
}
.hero-wrap::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(ellipse 60% 60% at 80% 20%, var(--accent)18, transparent 70%),
        radial-gradient(ellipse 40% 40% at 10% 80%, var(--orange)12, transparent 60%);
    pointer-events: none;
}
.hero-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--accent)1a;
    border: 1px solid var(--accent)44;
    border-radius: 999px;
    padding: 5px 16px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent-l);
    margin-bottom: 22px;
}
.hero-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--accent-l);
    animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.7); }
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2rem, 4vw, 3.2rem);
    font-weight: 800;
    color: var(--text-h);
    line-height: 1.1;
    margin: 0 0 18px 0;
    letter-spacing: -0.02em;
}
.hero-title .accent-word {
    background: linear-gradient(135deg, var(--accent-l), var(--orange));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-sub {
    font-size: 1rem;
    color: var(--text-m);
    line-height: 1.75;
    max-width: 620px;
    margin-bottom: 36px;
}
.hero-features {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}
.hero-feature-pill {
    display: flex;
    align-items: center;
    gap: 7px;
    background: var(--card-bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 7px 14px;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text);
    transition: border-color 0.2s, transform 0.2s;
}
.hero-feature-pill:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
}
.hero-feature-pill .pill-icon {
    font-size: 1rem;
}

/* ── Auth panel ── */
.auth-panel {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 0;
    overflow: hidden;
    margin-bottom: 24px;
}
.auth-panel-header {
    padding: 22px 28px 18px;
    border-bottom: 1px solid var(--border);
    background: var(--card-bg2);
}
.auth-panel-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-h);
    margin: 0 0 4px 0;
}
.auth-panel-sub {
    font-size: 0.78rem;
    color: var(--text-m);
    margin: 0;
}
.auth-panel-body {
    padding: 24px 28px;
}

/* ── Stats strip (logged-in) ── */
.stats-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 14px;
    margin-bottom: 28px;
}
.stat-tile {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 16px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s, transform 0.2s;
}
.stat-tile:hover {
    border-color: var(--accent);
    transform: translateY(-3px);
}
.stat-tile::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}
.stat-tile.blue::before  { background: var(--accent); }
.stat-tile.green::before { background: var(--success); }
.stat-tile.orange::before{ background: var(--orange); }
.stat-tile.purple::before{ background: #8b5cf6; }
.stat-icon { font-size: 1.5rem; margin-bottom: 6px; }
.stat-num {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: var(--text-h);
    line-height: 1;
    margin-bottom: 4px;
}
.stat-lbl {
    font-size: 0.68rem;
    color: var(--text-m);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
}

/* ── XP progress card ── */
.xp-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 22px 26px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.xp-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse 50% 80% at 100% 50%, var(--accent)10, transparent 70%);
    pointer-events: none;
}
.xp-card-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    flex-wrap: wrap;
    gap: 10px;
}
.xp-level-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--accent)20;
    border: 1px solid var(--accent)50;
    border-radius: 999px;
    padding: 6px 16px;
    font-family: 'Syne', sans-serif;
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--accent-l);
}
.xp-total {
    font-family: 'Syne', sans-serif;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--orange);
}
.xp-bar-track {
    height: 10px;
    background: var(--card-bg2);
    border: 1px solid var(--border);
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 8px;
}
.xp-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--success), var(--accent), #8b5cf6);
    transition: width 0.8s cubic-bezier(.22,.61,.36,1);
}
.xp-bar-caption {
    display: flex;
    justify-content: space-between;
    font-size: 0.71rem;
    color: var(--text-f);
}

/* ── Streak banner ── */
.streak-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    border-radius: 14px;
    padding: 14px 20px;
    margin-bottom: 24px;
    border: 1px solid;
}
.streak-banner.fire {
    background: var(--warning-bg);
    border-color: var(--orange)66;
}
.streak-banner.mild {
    background: var(--card-bg);
    border-color: var(--border);
}
.streak-banner.cold {
    background: var(--card-bg2);
    border-color: var(--border);
}
.streak-emoji { font-size: 1.8rem; }
.streak-text  { flex: 1; }
.streak-main  { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 0.95rem; color: var(--text-h); }
.streak-sub   { font-size: 0.75rem; color: var(--text-m); margin-top: 2px; }

/* ── Mastery chips ── */
.mastery-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 6px;
}
.mastery-chip-new {
    flex: 1;
    min-width: 110px;
    border-radius: 14px;
    padding: 14px 16px;
    border: 1px solid;
    text-align: center;
    transition: transform 0.2s;
}
.mastery-chip-new:hover { transform: translateY(-3px); }
.mastery-chip-new.strong   { background: var(--success-bg); border-color: var(--success)66; }
.mastery-chip-new.moderate { background: var(--warning-bg); border-color: var(--warning)66; }
.mastery-chip-new.weak     { background: var(--error-bg);   border-color: var(--error)66;   }
.mc-pct {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 4px;
}
.mastery-chip-new.strong   .mc-pct { color: var(--success); }
.mastery-chip-new.moderate .mc-pct { color: var(--warning); }
.mastery-chip-new.weak     .mc-pct { color: var(--error);   }
.mc-subj {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.mc-badge {
    display: inline-block;
    font-size: 0.6rem;
    border-radius: 999px;
    padding: 2px 8px;
    margin-top: 5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.mastery-chip-new.strong   .mc-badge { background: var(--success)22; color: var(--success); }
.mastery-chip-new.moderate .mc-badge { background: var(--warning)22; color: var(--warning); }
.mastery-chip-new.weak     .mc-badge { background: var(--error)22;   color: var(--error);   }

/* ── Level milestones ── */
.milestone-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    padding: 6px 0;
}
.ms-step {
    flex: 1;
    min-width: 80px;
    border-radius: 12px;
    padding: 10px 12px;
    border: 1px solid var(--border);
    text-align: center;
    background: var(--card-bg2);
    font-size: 0.7rem;
    color: var(--text-m);
    transition: all 0.2s;
}
.ms-step.done    { border-color: var(--success)66; background: var(--success-bg); color: var(--success); }
.ms-step.current { border-color: var(--accent); background: var(--accent)18; color: var(--accent-l); font-weight: 700; }
.ms-step.locked  { opacity: 0.45; }
.ms-icon { font-size: 1.2rem; display: block; margin-bottom: 4px; }
.ms-name { font-weight: 600; display: block; }
.ms-xp   { font-size: 0.62rem; opacity: 0.7; }

/* ── Welcome header ── */
.welcome-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 24px;
}
.welcome-name {
    font-family: 'Syne', sans-serif;
    font-size: clamp(1.4rem, 3vw, 2rem);
    font-weight: 800;
    color: var(--text-h);
    margin: 0;
}
.welcome-sub {
    font-size: 0.82rem;
    color: var(--text-m);
    margin: 4px 0 0 0;
}
.section-heading {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-f);
    margin: 0 0 12px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-heading::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── HUD header override ── */
.hud-header {
    display: none; /* replaced by new hero */
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ── Main page ─────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state.uid:
    # ── HERO ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-eyebrow">
            <span class="hero-dot"></span>
            AI-Powered · Adaptive · Personalized
        </div>
        <h1 class="hero-title">
            Your <span class="accent-word">Intelligent</span><br>
            Tutoring System
        </h1>
        <p class="hero-sub">
            An AI tutor grounded in your syllabus — zero hallucinations.
            It tracks quiz performance across sessions, adapts explanations
            when you struggle, and builds a personalized study plan around your goals.
        </p>
        <div class="hero-features">
            <div class="hero-feature-pill"><span class="pill-icon">📄</span> Syllabus-grounded RAG</div>
            <div class="hero-feature-pill"><span class="pill-icon">🧠</span> Socratic tutoring</div>
            <div class="hero-feature-pill"><span class="pill-icon">📊</span> Adaptive quizzes</div>
            <div class="hero-feature-pill"><span class="pill-icon">🗺️</span> Personalized roadmap</div>
            <div class="hero-feature-pill"><span class="pill-icon">🔍</span> XAI explanations</div>
            <div class="hero-feature-pill"><span class="pill-icon">🎮</span> XP &amp; streaks</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── REGISTER / LOGIN TABS ─────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["🆕  Register", "🔑  Login"])

    # ── REGISTER ──────────────────────────────────────────────────────────────
    with tab1:
        st.markdown("""
        <div class="auth-panel-header" style="background:var(--card-bg2);border-radius:14px 14px 0 0;
             padding:18px 0 14px 0;margin-bottom:18px;">
            <p class="auth-panel-title" style="font-family:'Syne',sans-serif;font-size:1.05rem;
               font-weight:700;color:var(--text-h);margin:0 0 4px 0;text-align:center;">
               ✨ Create Your Profile
            </p>
            <p class="auth-panel-sub" style="font-size:0.78rem;color:var(--text-m);text-align:center;margin:0;">
               Set up once — your tutor remembers everything
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            name      = st.text_input("Full Name *", placeholder="e.g. Arjun Mehta")
            age       = st.number_input("Age", min_value=10, max_value=60, value=20)
        with col2:
            edu_level = st.selectbox("Education Level", [
                "Secondary School", "Undergraduate", "Postgraduate", "Professional"
            ])
            email     = st.text_input("Email ID *", placeholder="e.g. arjun@email.com")

        password  = st.text_input("Password *", type="password", placeholder="Create a password")

        if st.button("✅ Create Profile", type="primary", use_container_width=True):
            if not name or not email or not password:
                st.error("Please fill in Name, Email and Password.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                uid = create_profile(
                    name, age, edu_level,
                    subject_list=[],
                    daily_hours=2.0,
                    deadline="",
                    learning_goals="",
                    email=email,
                    password=password
                )
                st.session_state.uid     = uid
                st.session_state.profile = get_profile(uid)
                st.session_state.profile["subjects_list"] = []
                st.success(f"Profile created! Welcome, {name} 🎉")
                st.rerun()

    # ── LOGIN ──────────────────────────────────────────────────────────────────
    with tab2:
        st.markdown("""
        <div style="background:var(--card-bg2);border-radius:14px 14px 0 0;
             padding:18px 0 14px 0;margin-bottom:18px;">
            <p style="font-family:'Syne',sans-serif;font-size:1.05rem;
               font-weight:700;color:var(--text-h);margin:0 0 4px 0;text-align:center;">
               🔑 Welcome Back
            </p>
            <p style="font-size:0.78rem;color:var(--text-m);text-align:center;margin:0;">
               Pick up exactly where you left off
            </p>
        </div>
        """, unsafe_allow_html=True)

        login_email = st.text_input("Email ID", placeholder="e.g. arjun@email.com",
                                    key="login_email")
        login_pass  = st.text_input("Password", type="password",
                                    placeholder="Enter your password", key="login_pass")

        if st.button("🔑 Login", type="primary", use_container_width=True):
            if not login_email.strip() or not login_pass.strip():
                st.error("Please enter both email and password.")
            else:
                try:
                    _profile = get_profile_by_email(login_email.strip(), login_pass)
                    if _profile is None:
                        st.error("Invalid email or password.")
                    else:
                        st.session_state.uid     = _profile["uid"]
                        st.session_state.profile = _profile
                        st.session_state.profile["subjects_list"] = _profile.get("subject_list", "").split(",")
                        st.rerun()
                except Exception as _e:
                    st.error(f"Login error: {_e}")

else:
    # ══════════════════════════════════════════════════════════════════
    # ── Logged-in Dashboard ─────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════
    p   = st.session_state.profile
    uid = st.session_state.uid

    # ── Welcome header ────────────────────────────────────────────────
    st.markdown(f"""
    <div class="welcome-row">
        <div>
            <p class="welcome-name">Welcome back, {p['name']}! 👋</p>
            <p class="welcome-sub">Use the sidebar to navigate — Study, Quiz, Plan, Dashboard &amp; more.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Fetch all dashboard data in one cached batch ─────────────────
    @st.cache_data(ttl=30, show_spinner=False)
    def _load_dashboard(uid):
        from database.db import get_connection as _gc
        conn = _gc()
        c = conn.cursor()
        # subject summary
        c.execute("SELECT * FROM subject_summary WHERE uid=%s ORDER BY subject", (uid,))
        summaries = [dict(r) for r in c.fetchall()]
        # quiz count
        c.execute("SELECT COUNT(*) as cnt FROM quiz_attempts WHERE uid=%s", (uid,))
        quiz_count = c.fetchone()["cnt"]
        # xp
        c.execute("SELECT * FROM learner_xp WHERE uid=%s", (uid,))
        xp_row = c.fetchone()
        xp_data = dict(xp_row) if xp_row else {"total_xp": 0, "level": 1}
        # streak
        c.execute("SELECT * FROM learner_streaks WHERE uid=%s", (uid,))
        streak_row = c.fetchone()
        streak_data = dict(streak_row) if streak_row else {"current_streak": 0, "longest_streak": 0}
        conn.close()
        return summaries, quiz_count, xp_data, streak_data

    summaries, quiz_count, xp_data, streak_data = _load_dashboard(uid)
    history = type("H", (), {"__len__": lambda s: quiz_count})()  # lightweight proxy

    total_xp       = xp_data.get("total_xp", 0)
    level          = xp_data.get("level", 1)
    current_streak = streak_data.get("current_streak", 0)
    longest_streak = streak_data.get("longest_streak", 0)
    xp_in_level, xp_needed = get_xp_progress(total_xp, level)
    level_title  = get_level_title(level)
    progress_pct = xp_in_level / xp_needed if xp_needed > 0 else 0

    subject_list_raw = p.get("subject_list") or ",".join(p.get("subjects_list", []))
    num_subjects     = len(subject_list_raw.split(","))
    num_strong       = len([s for s in summaries if s["strength_label"] == "Strong"])

    # ── Stats strip ───────────────────────────────────────────────────
    st.markdown('<p class="section-heading">Overview</p>', unsafe_allow_html=True)

    streak_icon = "🔥" if current_streak >= 3 else "📅"
    st.markdown(f"""
    <div class="stats-strip">
        <div class="stat-tile blue">
            <div class="stat-icon">📚</div>
            <div class="stat-num">{num_subjects}</div>
            <div class="stat-lbl">Subjects</div>
        </div>
        <div class="stat-tile green">
            <div class="stat-icon">🧠</div>
            <div class="stat-num">{len(history)}</div>
            <div class="stat-lbl">Quiz Attempts</div>
        </div>
        <div class="stat-tile purple">
            <div class="stat-icon">🏆</div>
            <div class="stat-num">{num_strong}</div>
            <div class="stat-lbl">Strong Subjects</div>
        </div>
        <div class="stat-tile orange">
            <div class="stat-icon">{streak_icon}</div>
            <div class="stat-num">{current_streak}</div>
            <div class="stat-lbl">Day Streak</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── XP / Level progress card ──────────────────────────────────────
    st.markdown('<p class="section-heading">🎮 Your Progress</p>', unsafe_allow_html=True)

    pct_display = int(progress_pct * 100)
    st.markdown(f"""
    <div class="xp-card">
        <div class="xp-card-row">
            <span class="xp-level-badge">🏅 Level {level} — {level_title}</span>
            <span class="xp-total">⭐ {total_xp} total XP</span>
        </div>
        <div class="xp-bar-track">
            <div class="xp-bar-fill" style="width:{pct_display}%;"></div>
        </div>
        <div class="xp-bar-caption">
            <span>{xp_in_level} XP in this level</span>
            <span>{xp_needed} XP to next level &nbsp;·&nbsp; {pct_display}% complete</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Streak banner ─────────────────────────────────────────────────
    if current_streak >= 7:
        flames = "🔥" * min(current_streak, 8)
        st.markdown(f"""
        <div class="streak-banner fire">
            <div class="streak-emoji">🔥</div>
            <div class="streak-text">
                <div class="streak-main">{flames} {current_streak}-day streak — incredible!</div>
                <div class="streak-sub">Best streak: {longest_streak} days · Keep the momentum going!</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif current_streak >= 3:
        flames = "🔥" * current_streak
        st.markdown(f"""
        <div class="streak-banner fire">
            <div class="streak-emoji">🔥</div>
            <div class="streak-text">
                <div class="streak-main">{flames} {current_streak}-day streak — keep it up!</div>
                <div class="streak-sub">Best streak: {longest_streak} days · Study today to extend it!</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif current_streak > 0:
        st.markdown(f"""
        <div class="streak-banner mild">
            <div class="streak-emoji">📅</div>
            <div class="streak-text">
                <div class="streak-main">{current_streak}-day streak — good start!</div>
                <div class="streak-sub">Best streak: {longest_streak} days · Keep studying to build momentum.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="streak-banner cold">
            <div class="streak-emoji">📅</div>
            <div class="streak-text">
                <div class="streak-main">No active streak yet</div>
                <div class="streak-sub">Study today to start your streak! Best ever: {longest_streak} days.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Level milestones ──────────────────────────────────────────────
    with st.expander("📊 Level Milestones", expanded=False):
        levels_info = {
            1: ("🌱", "Beginner",  0),
            2: ("📖", "Learner",   100),
            3: ("🔥", "Scholar",   200),
            4: ("⚡", "Expert",    300),
            5: ("🏆", "Master",    400),
        }
        steps_html = ""
        for lvl, (icon, title, xp_req) in levels_info.items():
            if lvl < level:
                cls = "done"
                tag = "✅ Unlocked"
            elif lvl == level:
                cls = "current"
                tag = "← You are here"
            else:
                cls = "locked"
                tag = f"{xp_req} XP needed"
            steps_html += f"""
            <div class="ms-step {cls}">
                <span class="ms-icon">{icon}</span>
                <span class="ms-name">Lv {lvl} · {title}</span>
                <span class="ms-xp">{tag}</span>
            </div>"""
        st.markdown(f'<div class="milestone-row">{steps_html}</div>', unsafe_allow_html=True)

    # ── Subject mastery ───────────────────────────────────────────────
    if summaries:
        st.markdown('<p class="section-heading" style="margin-top:8px;">📊 Subject Mastery</p>', unsafe_allow_html=True)
        color_map = {"Strong": "strong", "Moderate": "moderate", "Weak": "weak"}
        icon_map  = {"Strong": "🟢", "Moderate": "🟡", "Weak": "🔴"}
        chips_html = ""
        for s in summaries:
            cls  = color_map.get(s["strength_label"], "moderate")
            icon = icon_map.get(s["strength_label"], "⚪")
            chips_html += f"""
            <div class="mastery-chip-new {cls}">
                <div class="mc-pct">{s['avg_accuracy']:.1f}%</div>
                <div class="mc-subj">{icon} {s['subject']}</div>
                <span class="mc-badge">{s['strength_label']}</span>
            </div>"""
        st.markdown(f'<div class="mastery-row">{chips_html}</div>', unsafe_allow_html=True)