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

st.title("📊 Learning Analytics Dashboard")
st.caption("Track your progress, mastery levels, and how the Adaptive Explanation Loop is helping you.")

summaries = get_subject_summary(uid)
history   = get_quiz_history(uid)

if not history:
    st.info("📝 No quiz data yet. Complete some quizzes to see your analytics.")
    st.stop()

df = pd.DataFrame(history)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["session_num"] = df.groupby("subject").cumcount() + 1

# ── Row 1: Key Metrics ────────────────────────────────────────────────────────
st.subheader("🏆 Overall Performance")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Attempts",   len(df))
col2.metric("Overall Accuracy", f"{df['accuracy_pct'].mean():.1f}%")
col3.metric("Subjects Studied", df["subject"].nunique())
col4.metric("Strong Subjects",  len([s for s in summaries if s["strength_label"] == "Strong"]))

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
        fig.update_layout(showlegend=True, height=350)
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
    fig2.update_layout(height=350)
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
