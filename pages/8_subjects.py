"""
pages/8_Subjects.py
─────────────────────────────────────────────────────────────────────────────
Subject Manager — add, remove, and reorder subjects from inside the app.
Updates Supabase profile + st.session_state.profile instantly.
No need to re-register.
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
from database.db import get_profile

st.set_page_config(page_title="Subjects | LLM-ITS", page_icon="📚", layout="wide")

# ── Auth ──────────────────────────────────────────────────────────────────────
if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid     = st.session_state.uid
profile = st.session_state.profile

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=Instrument+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'Instrument Sans', sans-serif; }
.stApp { background: #080c14; color: #d4dbe8; }
hr { border-color: #1a2540 !important; }
[data-baseweb="input"] { background: #0d1524 !important; border-color: #1a2540 !important; border-radius: 10px !important; }
.stButton > button {
    border-radius: 10px !important; border: 1px solid #1a2540 !important;
    background: #0d1524 !important; color: #8090a8 !important;
    font-family: 'Instrument Sans', sans-serif !important;
    transition: all 0.18s !important;
}
.stButton > button:hover { background: #1a2540 !important; border-color: #3b82f6 !important; color: #f0f4ff !important; }
button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    border-color: #3b82f6 !important; color: #fff !important; font-weight: 600 !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    box-shadow: 0 4px 20px rgba(37,99,235,0.35) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(160deg,#0d1524 0%,#080c14 60%);
            border:1px solid #1a2540;border-radius:20px;
            padding:28px 36px;margin-bottom:28px;position:relative;overflow:hidden;">
  <div style="position:absolute;right:32px;top:50%;transform:translateY(-50%);
              font-family:'Syne',sans-serif;font-size:5rem;font-weight:800;
              color:rgba(255,255,255,0.022);letter-spacing:0.15em;
              pointer-events:none;user-select:none;">SUBJECTS</div>
  <div style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;
              color:#f0f6ff;margin-bottom:4px;">📚 Subject Manager</div>
  <div style="color:#4a6080;font-size:0.88rem;">
    Add or remove subjects without re-registering. Changes apply instantly across all pages.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Load current subjects ─────────────────────────────────────────────────────
def get_current_subjects():
    """Get subjects from session state profile (source of truth)."""
    p = st.session_state.profile
    raw = p.get("subjects_list") or p.get("subject_list", "")
    if isinstance(raw, list):
        return [s.strip() for s in raw if s.strip()]
    return [s.strip() for s in str(raw).split(",") if s.strip()]

def save_subjects_to_db(uid: str, subjects: list) -> bool:
    """
    Update subjects in Supabase profile table.
    Tries both subjects_list (array) and subject_list (comma string) columns.
    """
    try:
        import os
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
        except Exception:
            url = st.secrets.get("SUPABASE_URL", "")
            key = st.secrets.get("SUPABASE_KEY", "")

        from supabase import create_client
        client = create_client(url, key)

        subjects_str = ", ".join(subjects)

        # Try updating both columns (handle either schema)
        try:
            client.table("profiles").update({
                "subjects_list": subjects,
                "subject_list":  subjects_str,
            }).eq("uid", uid).execute()
        except Exception:
            try:
                client.table("profiles").update({
                    "subjects_list": subjects,
                }).eq("uid", uid).execute()
            except Exception:
                client.table("profiles").update({
                    "subject_list": subjects_str,
                }).eq("uid", uid).execute()

        return True
    except Exception as e:
        st.error(f"DB save failed: {e}")
        return False

def refresh_session_profile(subjects: list):
    """Update st.session_state.profile so all pages see new subjects immediately."""
    st.session_state.profile["subjects_list"] = subjects
    st.session_state.profile["subject_list"]  = ", ".join(subjects)
    # Clear any cached KG/topic state for removed subjects
    keys_to_clear = [k for k in st.session_state.keys()
                     if k.startswith("kg_") or k.startswith("topics_")]
    for k in keys_to_clear:
        del st.session_state[k]

# ── Initialize edit state ─────────────────────────────────────────────────────
if "subjects_edit_list" not in st.session_state:
    st.session_state.subjects_edit_list = get_current_subjects()

current = st.session_state.subjects_edit_list

# ── Layout ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1.4, 1])

# ══ LEFT: Current subjects list ═══════════════════════════════════════════════
with col_left:
    st.markdown("""
<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;
            letter-spacing:0.15em;color:#3b82f6;margin-bottom:14px;">
  📋 Current Subjects
</div>
""", unsafe_allow_html=True)

    if not current:
        st.markdown("""
<div style="background:#1c0808;border:1px solid #7f1d1d;border-radius:12px;
            padding:16px;text-align:center;color:#f87171;font-size:0.85rem;">
  ⚠️ No subjects added yet. Add your first subject on the right.
</div>
""", unsafe_allow_html=True)
    else:
        for i, subj in enumerate(current):
            # Check if this subject has a KG and topics
            from kg.kg_engine import KnowledgeGraph
            from database.db import get_topics, topics_exist
            has_topics = topics_exist(subj) if hasattr(__import__('database.db', fromlist=['topics_exist']), 'topics_exist') else bool(get_topics(subj))
            has_kg     = KnowledgeGraph.exists(subj)

            # Status indicators
            status_html = ""
            if has_topics and has_kg:
                status_html = '<span style="font-size:0.65rem;color:#34d399;background:#081810;border:1px solid #065f35;border-radius:20px;padding:2px 8px;margin-left:6px;">✓ PDF + KG</span>'
            elif has_topics:
                status_html = '<span style="font-size:0.65rem;color:#60a5fa;background:#0d1a2e;border:1px solid #1d4ed8;border-radius:20px;padding:2px 8px;margin-left:6px;">✓ PDF indexed</span>'
            else:
                status_html = '<span style="font-size:0.65rem;color:#f59e0b;background:#1c1005;border:1px solid #92400e;border-radius:20px;padding:2px 8px;margin-left:6px;">⚠ No PDF yet</span>'

            c1, c2, c3, c4 = st.columns([0.4, 3.5, 1, 1])

            with c1:
                st.markdown(f"""
<div style="width:32px;height:32px;border-radius:8px;background:#0d1a2e;
            border:1px solid #1d4ed8;display:flex;align-items:center;
            justify-content:center;font-size:0.8rem;font-weight:800;
            color:#60a5fa;margin-top:4px;">{i+1}</div>
""", unsafe_allow_html=True)

            with c2:
                st.markdown(f"""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:10px;
            padding:10px 14px;display:flex;align-items:center;">
  <span style="font-size:0.9rem;font-weight:600;color:#f0f6ff;">{subj}</span>
  {status_html}
</div>
""", unsafe_allow_html=True)

            with c3:
                # Move up
                disabled_up = (i == 0)
                if not disabled_up:
                    if st.button("↑", key=f"up_{i}", use_container_width=True, help="Move up"):
                        lst = st.session_state.subjects_edit_list
                        lst[i], lst[i-1] = lst[i-1], lst[i]
                        st.session_state.subjects_edit_list = lst
                        st.rerun()
                else:
                    st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)

            with c4:
                if st.button("🗑", key=f"del_{i}", use_container_width=True, help=f"Remove {subj}"):
                    st.session_state[f"confirm_del_{i}"] = True
                    st.rerun()

            # Confirm delete dialog
            if st.session_state.get(f"confirm_del_{i}"):
                st.markdown(f"""
<div style="background:#1c0808;border:1px solid #7f1d1d;border-radius:10px;
            padding:12px 14px;margin-bottom:6px;">
  <span style="font-size:0.82rem;color:#f87171;">
    Remove <strong>{subj}</strong>? This won't delete your uploaded PDFs.
  </span>
</div>
""", unsafe_allow_html=True)
                yes_col, no_col = st.columns(2)
                with yes_col:
                    if st.button(f"✓ Yes, remove", key=f"yes_del_{i}",
                                 type="primary", use_container_width=True):
                        new_list = [s for s in st.session_state.subjects_edit_list if s != subj]
                        st.session_state.subjects_edit_list = new_list
                        st.session_state.pop(f"confirm_del_{i}", None)
                        st.rerun()
                with no_col:
                    if st.button("✗ Cancel", key=f"no_del_{i}", use_container_width=True):
                        st.session_state.pop(f"confirm_del_{i}", None)
                        st.rerun()

    # ── Save button ───────────────────────────────────────────────────────────
    st.divider()
    has_changes = (sorted(current) != sorted(get_current_subjects()) or
                   current != get_current_subjects())

    saved_col, reset_col = st.columns(2)

    with saved_col:
        btn_label = "💾 Save Changes" if has_changes else "✓ Up to date"
        if st.button(btn_label, type="primary", use_container_width=True,
                     disabled=(len(current) == 0)):
            with st.spinner("Saving to database..."):
                ok = save_subjects_to_db(uid, current)
            if ok:
                refresh_session_profile(current)
                st.success(f"✅ Saved! {len(current)} subject(s) active across all pages.")
                st.rerun()

    with reset_col:
        if st.button("↺ Reset", use_container_width=True):
            st.session_state.subjects_edit_list = get_current_subjects()
            st.rerun()


# ══ RIGHT: Add new subject ════════════════════════════════════════════════════
with col_right:
    st.markdown("""
<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;
            letter-spacing:0.15em;color:#10b981;margin-bottom:14px;">
  ➕ Add New Subject
</div>
""", unsafe_allow_html=True)

    # ── Custom subject input ──────────────────────────────────────────────────
    new_subject = st.text_input(
        "Subject name",
        placeholder="e.g. Machine Learning, Operating Systems...",
        key="new_subject_input",
        label_visibility="collapsed"
    )

    if st.button("➕ Add Subject", type="primary", use_container_width=True,
                 disabled=not new_subject.strip()):
        cleaned = new_subject.strip().title()
        if cleaned in st.session_state.subjects_edit_list:
            st.warning(f"**{cleaned}** is already in your list.")
        elif len(st.session_state.subjects_edit_list) >= 8:
            st.warning("Maximum 8 subjects allowed.")
        else:
            st.session_state.subjects_edit_list.append(cleaned)
            st.rerun()

    st.divider()

    # ── Quick-add common subjects ─────────────────────────────────────────────
    st.markdown("""
<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;
            letter-spacing:0.15em;color:#4a6080;margin-bottom:12px;">
  ⚡ Quick Add
</div>
""", unsafe_allow_html=True)

    QUICK_SUBJECTS = [
        ("💻", "Data Structures"),
        ("🧮", "Algorithms"),
        ("🤖", "Machine Learning"),
        ("🌐", "Computer Networks"),
        ("🗄️", "Database Systems"),
        ("⚙️", "Operating Systems"),
        ("🔢", "Linear Algebra"),
        ("📊", "Statistics"),
        ("🐍", "Python Programming"),
        ("☕", "Java Programming"),
        ("🌍", "Web Development"),
        ("🔐", "Cyber Security"),
        ("📱", "Mobile Development"),
        ("☁️", "Cloud Computing"),
        ("🧠", "Deep Learning"),
        ("📡", "Computer Architecture"),
    ]

    # Show in 2 columns
    qcol1, qcol2 = st.columns(2)
    for idx, (icon, subj) in enumerate(QUICK_SUBJECTS):
        already_added = subj in st.session_state.subjects_edit_list
        col = qcol1 if idx % 2 == 0 else qcol2
        with col:
            if already_added:
                st.markdown(f"""
<div style="background:#081810;border:1px solid #065f35;border-radius:8px;
            padding:7px 10px;margin-bottom:4px;font-size:0.75rem;color:#34d399;">
  ✓ {icon} {subj}
</div>
""", unsafe_allow_html=True)
            else:
                if st.button(f"{icon} {subj}", key=f"quick_{subj}",
                             use_container_width=True):
                    if len(st.session_state.subjects_edit_list) >= 8:
                        st.warning("Maximum 8 subjects.")
                    else:
                        st.session_state.subjects_edit_list.append(subj)
                        st.rerun()

    st.divider()

    # ── Info box ──────────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:#0d1524;border:1px solid #1a2540;border-radius:12px;padding:14px;">
  <div style="font-size:0.7rem;font-weight:700;color:#3b82f6;margin-bottom:8px;">ℹ️ How it works</div>
  <div style="font-size:0.75rem;color:#4a6080;line-height:1.7;">
    1. Add subjects here<br>
    2. Click <strong style="color:#d4dbe8;">Save Changes</strong><br>
    3. Go to <strong style="color:#d4dbe8;">Upload Syllabus</strong> to upload a PDF for each subject<br>
    4. Build the Knowledge Graph for each subject<br>
    5. Start studying!
  </div>
</div>
""", unsafe_allow_html=True)