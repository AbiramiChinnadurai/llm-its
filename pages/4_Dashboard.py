"""
pages/4_Dashboard.py
Analytics dashboard — mastery trends, accuracy history, AEL distribution.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.db import get_subject_summary, get_quiz_history, get_error_topics

st.set_page_config(page_title="Dashboard | LLM-ITS", page_icon="📊", layout="wide")

if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid      = st.session_state.uid
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
    content: 'ANALYTICS'; position: absolute; right: 32px; top: 50%;
    transform: translateY(-50%); font-family: 'Syne', sans-serif;
    font-size: 5rem; font-weight: 800; color: rgba(255,255,255,0.025);
    letter-spacing: 0.15em; pointer-events: none; user-select: none;
}
.hud-title { font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800; color:#f0f6ff; margin:0 0 4px 0; }
.hud-sub   { color:#4a6080; font-size:0.88rem; margin:0; font-weight:300; }

.hud-cell { background:#0d1524; border:1px solid #1a2540; border-radius:14px; padding:18px 20px; position:relative; overflow:hidden; }
.hud-cell::before { content:''; position:absolute; bottom:0; left:0; right:0; height:2px; background:linear-gradient(90deg,#3b82f6,#1d4ed8); }
.hud-num { font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800; line-height:1; margin-bottom:4px; color:#f0f6ff; }
.hud-label { font-size:0.7rem; color:#4a6080; text-transform:uppercase; letter-spacing:0.1em; font-weight:600; }

hr { border-color:#1a2540 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hud-header">
    <h1 class="hud-title">📊 Learning Analytics Dashboard</h1>
    <p class="hud-sub">Track your progress, mastery levels, and how the Adaptive Explanation Loop is helping you.</p>
</div>
""", unsafe_allow_html=True)

summaries = get_subject_summary(uid)
history   = get_quiz_history(uid)

if not history:
    st.info("📝 No quiz data yet. Complete some quizzes to see your analytics.")
    st.stop()

df = pd.DataFrame(history)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["session_num"] = df.groupby("subject").cumcount() + 1

# ── Row 1: Key Metrics ────────────────────────────────────────────────────────
st.markdown('<div class="hud-label" style="font-size:1rem; margin-bottom:16px; color:#d4dbe8;">🏆 Overall Performance</div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

metrics = [
    ("Total Attempts", len(df)),
    ("Overall Accuracy", f"{df['accuracy_pct'].mean():.1f}%"),
    ("Subjects Studied", df["subject"].nunique()),
    ("Strong Subjects", len([s for s in summaries if s["strength_label"] == "Strong"]))
]

for col, (label, val) in zip([col1, col2, col3, col4], metrics):
    with col:
        st.markdown(f"""
        <div class="hud-cell">
            <div class="hud-num">{val}</div>
            <div class="hud-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Row 2: Mastery bar chart ──────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("📚 Subject Mastery")
    if summaries:
        df_sum = pd.DataFrame(summaries)
        color_map = {"Strong": "#2ecc71", "Moderate": "#f39c12", "Weak": "#e74c3c"}
        df_sum["color"] = df_sum["strength_label"].map(color_map)
        fig = px.bar(
            df_sum, x="subject", y="avg_accuracy",
            color="strength_label",
            color_discrete_map=color_map,
            text="avg_accuracy",
            title="Average Accuracy per Subject",
            labels={"avg_accuracy": "Accuracy (%)", "subject": "Subject"},
            range_y=[0, 100]
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.add_hline(y=75, line_dash="dash", line_color="#2ecc71", annotation_text="Strong (75%)")
        fig.add_hline(y=50, line_dash="dash", line_color="#f39c12", annotation_text="Moderate (50%)")
        fig.update_layout(
            showlegend=True, height=350,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#d4dbe8', family='Instrument Sans')
        )
        st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("📈 Accuracy Over Time")
    subject_filter = st.selectbox("Filter by subject", ["All"] + subjects, key="dash_subj")
    df_plot = df if subject_filter == "All" else df[df["subject"] == subject_filter]

    fig2 = px.line(
        df_plot.sort_values("timestamp"),
        x="timestamp", y="accuracy_pct",
        color="subject",
        markers=True,
        title="Quiz Accuracy Trend",
        labels={"accuracy_pct": "Accuracy (%)", "timestamp": "Date"}
    )
    fig2.add_hline(y=75, line_dash="dash", line_color="#2ecc71")
    fig2.add_hline(y=50, line_dash="dash", line_color="#f39c12")
    fig2.update_layout(
        height=350,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#d4dbe8', family='Instrument Sans')
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Row 3: AEL Distribution + Weak Topics ────────────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("🔄 AEL Modality Distribution")
    modality_labels = {
        0: "Standard Prose",
        1: "Step-by-Step",
        2: "Analogical",
        3: "Worked Example",
        4: "Simplified"
    }
    df["modality_label"] = df["ael_modality_used"].map(modality_labels)
    modality_counts = df["modality_label"].value_counts().reset_index()
    modality_counts.columns = ["Modality", "Count"]

    fig3 = px.pie(
        modality_counts, names="Modality", values="Count",
        title="Explanation Modality Usage",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig3.update_layout(height=320)
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    st.subheader("⚠️ Weak Topics by Subject")
    for subject in subjects:
        weak = get_error_topics(uid, subject)
        if weak:
            st.markdown(f"**{subject}:**")
            for t in weak:
                st.caption(f"  🔴 {t}")
        else:
            st.markdown(f"**{subject}:** ✅ No weak topics identified")

st.divider()

# ── Row 4: Detailed history table ────────────────────────────────────────────
with st.expander("📋 Full Quiz History", expanded=False):
    df_display = df[["timestamp", "subject", "topic", "score",
                     "total_questions", "accuracy_pct",
                     "ael_modality_used", "response_latency_s"]].copy()
    df_display.columns = ["Time", "Subject", "Topic", "Score",
                           "Total", "Accuracy %", "AEL Modality", "Latency (s)"]
    df_display["Time"] = df_display["Time"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(df_display, use_container_width=True)
