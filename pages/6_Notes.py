"""
pages/6_Notes.py
Notes & Highlights — save AI explanations, write personal notes,
highlight key concepts, organize by subject/topic.
"""

import streamlit as st
import time
import json
from database.db import get_topics

st.set_page_config(page_title="Notes | LLM-ITS", page_icon="📝", layout="wide")

# ── Professional CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,300;0,600;1,300&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.stApp { background: #0f1117; color: #e8e8e8; }

/* ── Header ── */
.notes-header {
    background: linear-gradient(135deg, #1a1f2e 0%, #12161f 100%);
    border: 1px solid #2a3040;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.notes-header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(167,139,250,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.notes-header h1 {
    font-family: 'Fraunces', serif;
    font-size: 2rem;
    font-weight: 600;
    color: #f0f4ff;
    margin: 0 0 4px 0;
    letter-spacing: -0.5px;
}
.notes-header p { color: #7a8499; font-size: 0.9rem; margin: 0; font-weight: 300; }

/* ── Note card ── */
.note-card {
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
    transition: border-color 0.2s, box-shadow 0.2s;
    position: relative;
}
.note-card:hover {
    border-color: #2d3a52;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.note-card.highlight {
    border-left: 3px solid #f59e0b;
    background: linear-gradient(135deg, #1c1a10, #161b27);
}
.note-card.ai-saved {
    border-left: 3px solid #3b82f6;
    background: linear-gradient(135deg, #101c30, #161b27);
}
.note-card.personal {
    border-left: 3px solid #a78bfa;
    background: linear-gradient(135deg, #150f1e, #161b27);
}

/* ── Note meta ── */
.note-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    flex-wrap: wrap;
}
.note-subject-tag {
    background: #1a2235;
    border: 1px solid #2d3a52;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.73rem;
    color: #93c5fd;
    font-weight: 500;
}
.note-topic-tag {
    background: #1e1a35;
    border: 1px solid #3d2d52;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.73rem;
    color: #c4b5fd;
}
.note-type-tag {
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.73rem;
    font-weight: 500;
}
.tag-ai    { background: #0d1f3c; border: 1px solid #1d4ed8; color: #60a5fa; }
.tag-hl    { background: #1c1505; border: 1px solid #92400e; color: #fbbf24; }
.tag-note  { background: #160d2a; border: 1px solid #5b21b6; color: #a78bfa; }

.note-time { font-size: 0.7rem; color: #3a4258; margin-left: auto; }

/* ── Note content ── */
.note-content {
    font-size: 0.87rem;
    color: #c0c8dc;
    line-height: 1.65;
    border-top: 1px solid #1e2535;
    padding-top: 12px;
    margin-top: 6px;
    white-space: pre-wrap;
}
.note-title {
    font-family: 'Fraunces', serif;
    font-size: 1.05rem;
    color: #f0f4ff;
    font-weight: 600;
    margin-bottom: 2px;
}

/* ── Highlight text ── */
.highlight-text {
    background: linear-gradient(120deg, rgba(245,158,11,0.15), rgba(245,158,11,0.05));
    border-left: 3px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    font-size: 0.87rem;
    color: #fde68a;
    font-style: italic;
    line-height: 1.6;
}

/* ── Stats bar ── */
.stats-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}
.stat-chip {
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 10px;
    padding: 10px 18px;
    text-align: center;
    flex: 1;
    min-width: 100px;
}
.stat-chip .num {
    font-family: 'Fraunces', serif;
    font-size: 1.6rem;
    color: #f0f4ff;
    display: block;
    line-height: 1.2;
}
.stat-chip .lbl { font-size: 0.72rem; color: #4a5568; text-transform: uppercase; letter-spacing: 0.08em; }

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #4a5568;
}
.empty-state .icon { font-size: 3rem; margin-bottom: 16px; }
.empty-state h3 {
    font-family: 'Fraunces', serif;
    font-size: 1.3rem;
    color: #6b7a99;
    margin-bottom: 8px;
}
.empty-state p { font-size: 0.85rem; }

/* ── Buttons ── */
.stButton > button {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    transition: all 0.18s ease !important;
    border: 1px solid #2a3040 !important;
    background: #161b27 !important;
    color: #c0c8dc !important;
}
.stButton > button:hover {
    background: #1e2535 !important;
    border-color: #63b3ed !important;
    color: #f0f4ff !important;
}
button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
    border-color: #7c3aed !important;
    color: #fff !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #8b5cf6, #7c3aed) !important;
    box-shadow: 0 4px 16px rgba(124,58,237,0.3) !important;
}

/* ── Inputs ── */
[data-baseweb="select"], [data-baseweb="input"], [data-baseweb="textarea"] {
    background: #161b27 !important;
    border-color: #2a3040 !important;
    border-radius: 10px !important;
}
textarea { background: #161b27 !important; color: #e8e8e8 !important; }

/* ── Tabs ── */
[data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid #1e2535 !important; }
[data-baseweb="tab"] { color: #4a5568 !important; font-family: 'DM Sans', sans-serif !important; }
[aria-selected="true"] { color: #a78bfa !important; border-bottom-color: #7c3aed !important; }

hr { border-color: #1e2535 !important; }
.sidebar-label {
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4a5568;
    margin: 16px 0 6px 0;
}
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("uid"):
    st.warning("Please login from the Home page first.")
    st.stop()

uid      = st.session_state.uid
profile  = st.session_state.profile
subjects = profile.get("subjects_list") or profile.get("subject_list", "").split(",")

# ── Init session state ────────────────────────────────────────────────────────
if "notes" not in st.session_state:
    st.session_state.notes = []
if "highlights" not in st.session_state:
    st.session_state.highlights = []

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="notes-header">
    <h1>📝 Notes & Highlights</h1>
    <p>Save AI explanations, write personal notes, and highlight key concepts from your study sessions.</p>
</div>
""", unsafe_allow_html=True)

# ── Stats ─────────────────────────────────────────────────────────────────────
all_notes = st.session_state.notes
all_hl    = st.session_state.highlights
total     = len(all_notes) + len(all_hl)
ai_saved  = sum(1 for n in all_notes if n.get("type") == "ai")
personal  = sum(1 for n in all_notes if n.get("type") == "personal")

st.markdown(f"""
<div class="stats-bar">
    <div class="stat-chip"><span class="num">{total}</span><span class="lbl">Total Notes</span></div>
    <div class="stat-chip"><span class="num">{ai_saved}</span><span class="lbl">AI Saved</span></div>
    <div class="stat-chip"><span class="num">{personal}</span><span class="lbl">Personal</span></div>
    <div class="stat-chip"><span class="num">{len(all_hl)}</span><span class="lbl">Highlights</span></div>
    <div class="stat-chip"><span class="num">{len(set(n.get('subject','') for n in all_notes + all_hl))}</span><span class="lbl">Subjects</span></div>
</div>
""", unsafe_allow_html=True)

# ── Layout ────────────────────────────────────────────────────────────────────
col_main, col_side = st.columns([3, 1])

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with col_side:
    st.markdown("### ✏️ Add New Note")
    st.divider()

    note_type = st.selectbox("Type", ["Personal Note", "Highlight"], key="note_type")

    st.markdown('<div class="sidebar-label">Subject</div>', unsafe_allow_html=True)
    note_subject = st.selectbox("", subjects, key="note_subj", label_visibility="collapsed")

    topics = get_topics(note_subject)
    st.markdown('<div class="sidebar-label">Topic</div>', unsafe_allow_html=True)
    if topics:
        note_topic = st.selectbox("", topics, key="note_topic", label_visibility="collapsed")
    else:
        note_topic = st.text_input("", placeholder="Enter topic name...", key="note_topic_manual", label_visibility="collapsed")

    st.markdown('<div class="sidebar-label">Title</div>', unsafe_allow_html=True)
    note_title = st.text_input("", placeholder="Give your note a title...", key="note_title", label_visibility="collapsed")

    st.markdown('<div class="sidebar-label">Content</div>', unsafe_allow_html=True)
    note_content = st.text_area(
        "",
        placeholder="Write your note here...\n\nFor highlights: paste the key passage you want to remember.",
        height=160,
        key="note_content",
        label_visibility="collapsed"
    )

    if st.button("💾 Save Note", type="primary", use_container_width=True):
        if note_content.strip():
            entry = {
                "id":        int(time.time() * 1000),
                "subject":   note_subject,
                "topic":     note_topic,
                "title":     note_title or f"{note_subject} — {note_topic}",
                "content":   note_content.strip(),
                "type":      "highlight" if note_type == "Highlight" else "personal",
                "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            }
            if note_type == "Highlight":
                st.session_state.highlights.append(entry)
            else:
                st.session_state.notes.append(entry)
            st.toast("✅ Note saved!", icon="📝")
            st.rerun()
        else:
            st.error("Please write some content first.")

    # ── Filters ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🔍 Filter")

    filter_subject = st.selectbox("Subject", ["All"] + subjects, key="filt_subj")
    filter_type    = st.selectbox("Type", ["All", "AI Saved", "Personal Note", "Highlight"], key="filt_type")
    search_notes   = st.text_input("Search content", placeholder="🔍 Search...", key="note_search")

    if st.button("🗑️ Clear All Notes", use_container_width=True):
        st.session_state.notes      = []
        st.session_state.highlights = []
        st.rerun()

# ── MAIN AREA ─────────────────────────────────────────────────────────────────
with col_main:
    tab1, tab2, tab3 = st.tabs(["📋 All Notes", "⭐ Highlights", "📤 Export"])

    # Build unified list
    all_items = (
        [dict(n, _src="note") for n in st.session_state.notes] +
        [dict(h, _src="highlight") for h in st.session_state.highlights]
    )
    all_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # Apply filters
    def apply_filters(items):
        if filter_subject != "All":
            items = [i for i in items if i.get("subject") == filter_subject]
        if filter_type == "AI Saved":
            items = [i for i in items if i.get("type") == "ai"]
        elif filter_type == "Personal Note":
            items = [i for i in items if i.get("type") == "personal"]
        elif filter_type == "Highlight":
            items = [i for i in items if i.get("type") == "highlight"]
        if search_notes:
            q = search_notes.lower()
            items = [i for i in items if q in i.get("content","").lower()
                     or q in i.get("title","").lower()
                     or q in i.get("topic","").lower()]
        return items

    def render_note_card(item, idx, col=None):
        t         = item.get("type", "personal")
        css_class = {"ai": "ai-saved", "highlight": "highlight", "personal": "personal"}.get(t, "personal")
        type_tag  = {"ai": "tag-ai", "highlight": "tag-hl", "personal": "tag-note"}.get(t, "tag-note")
        type_lbl  = {"ai": "🤖 AI Saved", "highlight": "⭐ Highlight", "personal": "✏️ Personal"}.get(t, "Personal")

        content_html = (
            f'<div class="highlight-text">{item["content"]}</div>'
            if t == "highlight"
            else f'<div class="note-content">{item["content"]}</div>'
        )

        st.markdown(f"""
        <div class="note-card {css_class}">
            <div class="note-meta">
                <span class="note-subject-tag">{item.get('subject','')}</span>
                <span class="note-topic-tag">{item.get('topic','')}</span>
                <span class="note-type-tag {type_tag}">{type_lbl}</span>
                <span class="note-time">{item.get('timestamp','')}</span>
            </div>
            <div class="note-title">{item.get('title','Untitled')}</div>
            {content_html}
        </div>
        """, unsafe_allow_html=True)

        # Delete button
        c1, c2 = st.columns([5, 1])
        with c2:
            if st.button("🗑️", key=f"del_{item['id']}_{idx}", use_container_width=True):
                if item["_src"] == "highlight":
                    st.session_state.highlights = [
                        h for h in st.session_state.highlights if h["id"] != item["id"]
                    ]
                else:
                    st.session_state.notes = [
                        n for n in st.session_state.notes if n["id"] != item["id"]
                    ]
                st.rerun()

    # ── Tab 1: All Notes ─────────────────────────────────────────────
    with tab1:
        filtered = apply_filters(all_items)
        if not filtered:
            st.markdown("""
            <div class="empty-state">
                <div class="icon">📭</div>
                <h3>No notes yet</h3>
                <p>Save AI explanations from Study page or write personal notes using the form on the left.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption(f"Showing {len(filtered)} note{'s' if len(filtered) != 1 else ''}")
            for i, item in enumerate(filtered):
                render_note_card(item, i)

    # ── Tab 2: Highlights only ───────────────────────────────────────
    with tab2:
        hl_items = apply_filters([dict(h, _src="highlight") for h in st.session_state.highlights])
        if not hl_items:
            st.markdown("""
            <div class="empty-state">
                <div class="icon">⭐</div>
                <h3>No highlights yet</h3>
                <p>Use the form on the left and select "Highlight" to save key passages from your study material.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Group by subject
            by_subject = {}
            for h in hl_items:
                subj = h.get("subject", "General")
                by_subject.setdefault(subj, []).append(h)

            for subj, items in by_subject.items():
                st.markdown(f"""
                <div style="font-family:'Fraunces',serif; font-size:1.1rem; color:#f0f4ff;
                            margin: 16px 0 10px 0; padding-bottom: 6px; border-bottom: 1px solid #1e2535;">
                    📚 {subj} <span style="font-size:0.75rem; color:#4a5568; font-family:'DM Sans',sans-serif;">
                    — {len(items)} highlight{'s' if len(items) != 1 else ''}</span>
                </div>
                """, unsafe_allow_html=True)
                for i, item in enumerate(items):
                    render_note_card(item, f"hl_{subj}_{i}")

    # ── Tab 3: Export ─────────────────────────────────────────────────
    with tab3:
        st.markdown("""
        <div style="font-family:'Fraunces',serif; font-size:1.2rem; color:#f0f4ff; margin-bottom:16px;">
            Export Your Notes
        </div>
        """, unsafe_allow_html=True)

        if not all_items:
            st.info("No notes to export yet.")
        else:
            # Build plain text export
            lines = ["═══════════════════════════════════════",
                     "     LLM-ITS — My Study Notes",
                     f"     Exported: {time.strftime('%Y-%m-%d %H:%M')}",
                     "═══════════════════════════════════════\n"]

            by_subj = {}
            for item in all_items:
                by_subj.setdefault(item.get("subject", "General"), []).append(item)

            for subj, items in by_subj.items():
                lines.append(f"\n{'─'*40}")
                lines.append(f"  📚 {subj}")
                lines.append(f"{'─'*40}")
                for item in items:
                    t_icon = {"ai": "🤖", "highlight": "⭐", "personal": "✏️"}.get(item.get("type"), "📝")
                    lines.append(f"\n{t_icon} [{item.get('topic','')}] {item.get('title','Untitled')}")
                    lines.append(f"   {item.get('timestamp','')}")
                    lines.append(f"\n{item.get('content','')}\n")

            export_text = "\n".join(lines)

            st.download_button(
                "⬇️ Download Notes as .txt",
                export_text,
                file_name=f"study_notes_{time.strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )

            # JSON export
            export_json = json.dumps(all_items, indent=2, default=str)
            st.download_button(
                "⬇️ Download as JSON",
                export_json,
                file_name=f"study_notes_{time.strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )

            st.divider()
            st.markdown("**Preview:**")
            st.text(export_text[:800] + ("..." if len(export_text) > 800 else ""))
