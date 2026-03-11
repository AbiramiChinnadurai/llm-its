"""
utils/theme.py
─────────────────────────────────────────────────────────────────────────────
Theme system for LLM-ITS — Dark (navy/blue) and Light (white/orange).
Import and call inject_theme() at the top of every page after st.set_page_config.
Call render_theme_toggle() in the sidebar.
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st

# ─── Theme tokens ─────────────────────────────────────────────────────────────

DARK = {
    "name":          "dark",
    "emoji":         "🌙",
    "label":         "Dark",
    # Backgrounds
    "app_bg":        "#080c14",
    "card_bg":       "#0d1524",
    "card_bg2":      "#0a0f1a",
    "sidebar_bg":    "#080c14",
    "input_bg":      "#0d1524",
    "hover_bg":      "#1a2540",
    # Borders
    "border":        "#1a2540",
    "border2":       "#1e2d40",
    # Text
    "text_primary":  "#f0f6ff",
    "text_secondary":"#d4dbe8",
    "text_muted":    "#4a6080",
    "text_faint":    "#2a3a50",
    # Accent (blue)
    "accent":        "#2563eb",
    "accent2":       "#1d4ed8",
    "accent_light":  "#3b82f6",
    "accent_hover":  "#60a5fa",
    # Orange accent
    "orange":        "#f59e0b",
    "orange2":       "#d97706",
    # Success / Warning / Error
    "success":       "#10b981",
    "success_bg":    "#064e2e",
    "warning":       "#f59e0b",
    "warning_bg":    "#1c1005",
    "error":         "#ef4444",
    "error_bg":      "#1c0808",
    # Watermark
    "watermark":     "rgba(255,255,255,0.022)",
    # Tab active gradient
    "tab_active_bg": "linear-gradient(135deg,#2563eb,#1d4ed8)",
    "tab_active_shadow": "0 4px 16px rgba(37,99,235,0.35)",
    "tab_hover_bg":  "#1a2540",
    "tab_hover_text":"#d4dbe8",
    "tab_text":      "#4a6080",
    "tab_list_bg":   "#0d1524",
    # Primary button
    "btn_primary":   "linear-gradient(135deg,#2563eb,#1d4ed8)",
    "btn_primary_h": "linear-gradient(135deg,#3b82f6,#2563eb)",
    "btn_primary_sh":"0 4px 20px rgba(37,99,235,0.35)",
    "btn_bg":        "#0d1524",
    "btn_color":     "#8090a8",
    "btn_border":    "#1a2540",
    # Sidebar header text
    "header_bg":     "linear-gradient(160deg, #0d1524 0%, #080c14 60%)",
    "header_border": "#1a2540",
}

LIGHT = {
    "name":          "light",
    "emoji":         "☀️",
    "label":         "Light",
    # Backgrounds — crisp white + soft orange warmth
    "app_bg":        "#fffbf7",
    "card_bg":       "#ffffff",
    "card_bg2":      "#fff8f3",
    "sidebar_bg":    "#fff5eb",
    "input_bg":      "#ffffff",
    "hover_bg":      "#ffedd5",
    # Borders
    "border":        "#e8e0d8",
    "border2":       "#ede6dd",
    # Text — dark enough for readability on white/cream
    "text_primary":  "#0f0a00",
    "text_secondary":"#2d1f0f",
    "text_muted":    "#5c4a3a",
    "text_faint":    "#6b5a4a",
    # Accent (orange)
    "accent":        "#ea580c",
    "accent2":       "#c2410c",
    "accent_light":  "#f97316",
    "accent_hover":  "#fb923c",
    # Orange accent
    "orange":        "#ea580c",
    "orange2":       "#c2410c",
    # Success / Warning / Error
    "success":       "#16a34a",
    "success_bg":    "#f0fdf4",
    "warning":       "#d97706",
    "warning_bg":    "#fffbeb",
    "error":         "#dc2626",
    "error_bg":      "#fef2f2",
    # Watermark
    "watermark":     "rgba(0,0,0,0.04)",
    # Tab active gradient
    "tab_active_bg": "linear-gradient(135deg,#ea580c,#c2410c)",
    "tab_active_shadow": "0 4px 16px rgba(234,88,12,0.25)",
    "tab_hover_bg":  "#fff0e6",
    "tab_hover_text":"#1a0f00",
    "tab_text":      "#8a7060",
    "tab_list_bg":   "#fff8f3",
    # Primary button
    "btn_primary":   "linear-gradient(135deg,#ea580c,#c2410c)",
    "btn_primary_h": "linear-gradient(135deg,#f97316,#ea580c)",
    "btn_primary_sh":"0 4px 20px rgba(234,88,12,0.30)",
    "btn_bg":        "#ffffff",
    "btn_color":     "#2d1f0f",
    "btn_border":    "#e8e0d8",
    # Sidebar header text
    "header_bg":     "linear-gradient(160deg, #fff5eb 0%, #fffbf7 60%)",
    "header_border": "#ffedd5",
}


# ─── Get current theme ────────────────────────────────────────────────────────

def get_theme() -> dict:
    """
    Returns current theme dict (DARK or LIGHT).
    Sidebar toggle takes precedence; falls back to Streamlit's theme (Settings menu).
    """
    # 1. Sidebar toggle (explicit user click) takes precedence
    theme = st.session_state.get("theme")
    if theme == "light":
        return LIGHT
    if theme == "dark":
        return DARK

    # 2. Fallback: Streamlit's theme from Settings menu
    try:
        if hasattr(st, "context") and hasattr(st.context, "theme"):
            t = getattr(st.context.theme, "type", None)
            if t == "light":
                return LIGHT
            if t == "dark":
                return DARK
    except Exception:
        pass

    # 3. Default dark
    return DARK


def is_dark() -> bool:
    return get_theme() is DARK


# ─── CSS generator ────────────────────────────────────────────────────────────

def build_css(t: dict) -> str:
    """Build complete CSS string from theme tokens."""
    return f"""
<style>
/* ── CSS Variables for inline HTML compatibility ── */
:root {{
    --app-bg:    {t['app_bg']};
    --card-bg:   {t['card_bg']};
    --card-bg2:  {t['card_bg2']};
    --sidebar-bg:{t['sidebar_bg']};
    --border:    {t['border']};
    --text:      {t['text_secondary']};
    --text-h:    {t['text_primary']};
    --text-m:    {t['text_muted']};
    --text-f:    {t['text_faint']};
    --accent:    {t['accent']};
    --accent-l:  {t['accent_light']};
    --orange:    {t['orange']};
    --success:   {t['success']};
    --success-bg:{t['success_bg']};
    --warning:   {t['warning']};
    --warning-bg:{t['warning_bg']};
    --error:     {t['error']};
    --error-bg:  {t['error_bg']};
    --watermark: {t['watermark']};
}}
/* Force Streamlit containers to respect theme */
.main .block-container {{ background: {t['app_bg']} !important; color: {t['text_secondary']} !important; }}
div[data-testid="stVerticalBlock"] > div {{ color: {t['text_secondary']} !important; }}
/* Override Streamlit's default light-theme gray text */
.block-container, [data-testid="stVerticalBlock"] {{ color: {t['text_secondary']} !important; }}

@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=Instrument+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{ font-family: 'Instrument Sans', sans-serif; }}
.stApp {{ background: {t['app_bg']} !important; color: {t['text_secondary']}; }}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background: {t['sidebar_bg']} !important;
    border-right: 1px solid {t['border']} !important;
}}
section[data-testid="stSidebar"] * {{ color: {t['text_secondary']}; }}

/* Tabs */
[data-baseweb="tab-list"] {{
    background: {t['tab_list_bg']} !important;
    border-radius: 14px !important; padding: 6px !important;
    gap: 4px !important; border: 1px solid {t['border']} !important;
    margin-bottom: 24px !important;
}}
[data-baseweb="tab"] {{
    background: transparent !important; border-radius: 10px !important;
    color: {t['tab_text']} !important; font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important; font-size: 0.88rem !important;
    padding: 10px 24px !important; border: none !important;
    transition: all 0.18s !important;
}}
[data-baseweb="tab"]:hover {{
    color: {t['tab_hover_text']} !important;
    background: {t['tab_hover_bg']} !important;
}}
[aria-selected="true"][data-baseweb="tab"] {{
    background: {t['tab_active_bg']} !important;
    color: #fff !important; box-shadow: {t['tab_active_shadow']} !important;
}}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display: none !important; }}

/* Buttons */
.stButton > button {{
    border-radius: 10px !important; font-family: 'Instrument Sans', sans-serif !important;
    font-size: 0.84rem !important; font-weight: 500 !important;
    transition: all 0.2s !important; border: 1px solid {t['btn_border']} !important;
    background: {t['btn_bg']} !important; color: {t['btn_color']} !important;
}}
.stButton > button:hover {{
    background: {t['hover_bg']} !important;
    border-color: {t['accent_light']} !important;
    color: {t['text_primary']} !important; transform: translateY(-2px) !important;
}}
button[kind="primary"] {{
    background: {t['btn_primary']} !important;
    border-color: {t['accent_light']} !important;
    color: #fff !important; font-weight: 600 !important;
}}
button[kind="primary"]:hover {{
    background: {t['btn_primary_h']} !important;
    box-shadow: {t['btn_primary_sh']} !important;
}}

/* Inputs */
[data-baseweb="select"] {{
    background: {t['input_bg']} !important;
    border-color: {t['border']} !important; border-radius: 10px !important;
}}
[data-baseweb="input"] {{
    background: {t['input_bg']} !important;
    border-color: {t['border']} !important; border-radius: 10px !important;
}}
textarea {{
    background: {t['card_bg2']} !important; border-color: {t['border']} !important;
    border-radius: 10px !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important; color: {t['text_primary']} !important;
}}
hr {{ border-color: {t['border']} !important; }}

/* Chat */
[data-testid="stChatMessage"] {{
    background: {t['card_bg']} !important; border: 1px solid {t['border']} !important;
    border-radius: 14px !important; margin-bottom: 12px !important; padding: 16px !important;
}}
[data-testid="stChatInput"] {{
    background: {t['input_bg']} !important;
    border: 1px solid {t['border']} !important; border-radius: 14px !important;
}}
[data-testid="stChatInput"]:focus-within {{
    border-color: {t['accent_light']} !important;
    box-shadow: 0 0 0 3px {t['accent']}22 !important;
}}

/* Expanders */
[data-testid="stExpander"] {{
    background: {t['card_bg']} !important; border: 1px solid {t['border']} !important;
    border-radius: 12px !important;
}}

/* Metric — ensure labels and values are readable */
[data-testid="stMetric"], [data-testid="metric-container"] {{
    background: {t['card_bg']} !important;
    border-radius: 10px !important;
}}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"],
[data-testid="stMetric"] label, [data-testid="stMetric"] div,
[data-testid="metric-container"] label, [data-testid="metric-container"] div {{
    color: {t['text_primary']} !important;
}}

/* Titles, headers — force readable text */
.main h1, .main h2, .main h3, .main [data-testid="stMarkdown"] p,
.main [data-testid="stMarkdown"] {{
    color: {t['text_primary']} !important;
}}

/* Expander header */
[data-testid="stExpander"] summary, [data-testid="stExpander"] label {{
    color: {t['text_primary']} !important;
}}

/* General main content text */
.main p, .main [data-testid="stMarkdown"] {{
    color: {t['text_secondary']} !important;
}}

/* ── Component classes ── */
.hud-header {{
    background: {t['header_bg']};
    border: 1px solid {t['header_border']}; border-radius: 20px;
    padding: 28px 36px; margin-bottom: 28px;
    position: relative; overflow: hidden;
}}
.hud-title {{ font-family:'Syne',sans-serif; font-size:2rem; font-weight:800; color:{t['text_primary']}; margin:0 0 4px 0; }}
.hud-sub   {{ color:{t['text_muted']}; font-size:0.88rem; margin:0; font-weight:300; }}

.meta-row {{ display:flex; gap:14px; margin-top:8px; padding-top:8px; border-top:1px solid {t['border']}; }}
.meta-pill {{
    background:{t['card_bg2']}; border:1px solid {t['border']};
    border-radius:6px; padding:3px 10px; font-size:0.73rem; color:{t['text_muted']};
}}
.sidebar-label {{
    font-size:0.7rem; font-weight:600; letter-spacing:0.12em;
    text-transform:uppercase; color:{t['text_faint']}; margin:20px 0 8px 0;
}}
.ael-badge {{
    display:inline-flex; align-items:center; gap:8px;
    background:{t['card_bg']}; border:1px solid {t['border']};
    border-radius:20px; padding:6px 14px; font-size:0.8rem;
    color:{t['accent_light']}; font-weight:500; margin-top:6px;
}}
.ael-dot {{
    width:8px; height:8px; border-radius:50%;
    background:{t['accent_light']};
    box-shadow:0 0 6px {t['accent']}99; animation:pulse 2s infinite;
}}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}

.weak-tag {{
    display:inline-block; background:{t['error_bg']};
    border:1px solid {t['error']}66; color:{t['error']};
    border-radius:6px; padding:3px 10px; font-size:0.75rem; margin:3px 2px;
}}
.status-indexed {{
    background:{t['success_bg']}; border:1px solid {t['success']}66;
    color:{t['success']}; border-radius:8px; padding:6px 12px; font-size:0.78rem; font-weight:500;
}}
.status-missing {{
    background:{t['warning_bg']}; border:1px solid {t['warning']}66;
    color:{t['warning']}; border-radius:8px; padding:6px 12px; font-size:0.78rem;
}}

/* Quiz cards */
.q-card {{
    background:{t['card_bg']}; border:1px solid {t['border']};
    border-radius:16px; padding:24px 28px; margin-bottom:20px;
}}
.q-meta {{ display:flex; gap:10px; margin-bottom:14px; flex-wrap:wrap; }}
.q-badge {{ font-size:0.68rem; border-radius:8px; padding:3px 10px; font-weight:600; border:1px solid; }}
.badge-subject {{ background:{t['accent']}18; color:{t['accent_light']}; border-color:{t['accent']}44; }}
.badge-topic   {{ background:{t['success']}18; color:{t['success']}; border-color:{t['success']}44; }}
.badge-mastery {{ background:{t['orange']}18; color:{t['orange']}; border-color:{t['orange']}44; }}
.badge-mode    {{ background:#8b5cf618; color:#8b5cf6; border-color:#8b5cf644; }}
.q-text {{ font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:600; color:{t['text_primary']}; line-height:1.5; }}
.result-correct {{ background:{t['success_bg']}; border:1px solid {t['success']}66; border-radius:12px; padding:16px 20px; margin:12px 0; }}
.result-wrong   {{ background:{t['error_bg']}; border:1px solid {t['error']}66; border-radius:12px; padding:16px 20px; margin:12px 0; }}
.result-partial {{ background:{t['warning_bg']}; border:1px solid {t['warning']}66; border-radius:12px; padding:16px 20px; margin:12px 0; }}
.result-title {{ font-family:'Syne',sans-serif; font-size:1rem; font-weight:700; margin-bottom:8px; }}
.result-correct .result-title {{ color:{t['success']}; }}
.result-wrong   .result-title {{ color:{t['error']}; }}
.result-partial .result-title {{ color:{t['warning']}; }}
.result-body {{ font-size:0.84rem; color:{t['text_muted']}; line-height:1.7; }}
.xp-popup {{
    background: {t['btn_primary']}; border-radius:12px; padding:12px 20px; margin:12px 0;
    font-family:'Syne',sans-serif; font-size:0.9rem; font-weight:700;
    color:#fff; text-align:center; box-shadow:{t['btn_primary_sh']};
}}

/* Roadmap */
.hud-cell {{ background:{t['card_bg']}; border:1px solid {t['border']}; border-radius:14px; padding:18px 20px; position:relative; overflow:hidden; }}
.hud-cell::before {{ content:''; position:absolute; bottom:0; left:0; right:0; height:2px; }}
.hud-cell.completed::before {{ background:linear-gradient(90deg,{t['success']},{t['success']}aa); }}
.hud-cell.pending::before   {{ background:linear-gradient(90deg,{t['accent']},{t['accent2']}); }}
.hud-cell.total::before     {{ background:linear-gradient(90deg,#8b5cf6,#6d28d9); }}
.hud-cell.xp::before        {{ background:linear-gradient(90deg,{t['orange']},{t['orange2']}); }}
.hud-num {{ font-family:'Syne',sans-serif; font-size:2.4rem; font-weight:800; line-height:1; margin-bottom:4px; }}
.hud-cell.completed .hud-num {{ color:{t['success']}; }}
.hud-cell.pending   .hud-num {{ color:{t['accent']}; }}
.hud-cell.total     .hud-num {{ color:#8b5cf6; }}
.hud-cell.xp        .hud-num {{ color:{t['orange']}; }}
.hud-label {{ font-size:0.7rem; color:{t['text_faint']}; text-transform:uppercase; letter-spacing:0.1em; font-weight:500; }}
.progress-track-bar {{ height:6px; background:{t['card_bg2']}; border-radius:10px; overflow:hidden; margin:8px 0 6px 0; border:1px solid {t['border']}; }}
.progress-track-fill {{ height:100%; border-radius:10px; background:linear-gradient(90deg,{t['success']},{t['accent']},#8b5cf6); transition:width 0.6s ease; }}
.progress-caption {{ display:flex; justify-content:space-between; font-size:0.72rem; color:{t['text_faint']}; }}
.node-label-card {{ background:{t['card_bg']}; border:1px solid {t['border']}; border-radius:12px; padding:10px 14px; max-width:200px; margin:0 14px; transition:all 0.2s; }}
.node-label-card.done   {{ border-color:{t['success']}66; background:{t['success_bg']}; }}
.node-label-card.active {{ border-color:{t['accent']}; background:{t['card_bg']}; box-shadow:0 0 0 1px {t['accent']}22; }}
.node-label-card.locked {{ opacity:0.4; }}
.nlc-day   {{ font-size:0.62rem; text-transform:uppercase; letter-spacing:0.1em; font-weight:600; margin-bottom:3px; }}
.nlc-day.done   {{ color:{t['success']}; }}
.nlc-day.active {{ color:{t['accent_light']}; }}
.nlc-day.locked {{ color:{t['text_faint']}; }}
.nlc-title {{ font-family:'Syne',sans-serif; font-size:0.82rem; font-weight:600; color:{t['text_secondary']}; }}
.nlc-title.done   {{ color:{t['text_faint']}; text-decoration:line-through; }}
.nlc-title.locked {{ color:{t['text_faint']}; }}
.nlc-badge {{ display:inline-block; font-size:0.62rem; border-radius:20px; padding:2px 8px; margin-top:4px; font-weight:500; }}
.badge-done    {{ background:{t['success_bg']}; color:{t['success']}; border:1px solid {t['success']}66; }}
.badge-active  {{ background:{t['accent']}; color:#fff; border:1px solid {t['accent2']}; }}
.badge-locked  {{ background:{t['card_bg2']}; color:{t['text_faint']}; border:1px solid {t['border']}; }}
.badge-pending {{ background:{t['accent']}18; color:{t['accent_light']}; border:1px solid {t['accent']}44; }}
.detail-panel {{ background:{t['card_bg']}; border:1px solid {t['accent']}; border-radius:16px; padding:20px 24px; margin:16px 0; box-shadow:0 0 0 1px {t['accent']}22, 0 8px 32px {t['app_bg']}88; }}
.dp-header {{ font-family:'Syne',sans-serif; font-size:1rem; font-weight:700; color:{t['text_primary']}; margin-bottom:10px; }}
.dp-content {{ font-size:0.84rem; color:{t['text_muted']}; line-height:1.75; }}
.dp-subject-tag {{ display:inline-block; background:{t['accent']}; color:#fff; border-radius:8px; padding:3px 10px; font-size:0.7rem; font-weight:600; margin-bottom:10px; }}
.mastery-chip {{ border-radius:12px; padding:12px 18px; display:flex; flex-direction:column; gap:2px; flex:1; min-width:120px; border:1px solid; }}
.mastery-chip.strong   {{ background:{t['success_bg']}; border-color:{t['success']}66; }}
.mastery-chip.moderate {{ background:{t['warning_bg']}; border-color:{t['warning']}66; }}
.mastery-chip.weak     {{ background:{t['error_bg']}; border-color:{t['error']}66; }}
.mastery-chip .subj {{ font-family:'Syne',sans-serif; font-size:0.8rem; font-weight:600; }}
.mastery-chip.strong   .subj {{ color:{t['success']}; }}
.mastery-chip.moderate .subj {{ color:{t['warning']}; }}
.mastery-chip.weak     .subj {{ color:{t['error']}; }}
.mastery-chip .pct {{ font-family:'Syne',sans-serif; font-size:1.3rem; font-weight:800; color:{t['text_primary']}; }}
.mastery-chip .wk {{ font-size:0.68rem; color:{t['text_muted']}; }}
.stat-card {{ background:{t['card_bg']}; border:1px solid {t['border']}; border-radius:12px; padding:14px 16px; margin-bottom:10px; }}
.stat-val   {{ font-family:'Syne',sans-serif; font-size:1.8rem; font-weight:800; color:{t['text_primary']}; }}
.stat-label {{ font-size:0.68rem; color:{t['text_faint']}; text-transform:uppercase; letter-spacing:0.1em; }}
.section-label {{ font-size:0.68rem; font-weight:600; letter-spacing:0.12em; text-transform:uppercase; color:{t['text_faint']}; margin:16px 0 8px 0; }}
.meta-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:20px; }}
.meta-cell {{ background:{t['card_bg']}; border:1px solid {t['border']}; border-radius:12px; padding:14px 16px; }}
.meta-cell .val {{ font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:800; color:{t['text_primary']}; }}
.meta-cell .lbl {{ font-size:0.68rem; color:{t['text_faint']}; text-transform:uppercase; letter-spacing:0.1em; }}
.dynamic-alert {{ background:{t['success_bg']}; border:1px solid {t['success']}66; border-radius:12px; padding:12px 18px; margin-bottom:20px; font-size:0.82rem; color:{t['success']}; }}
.dynamic-alert.warn {{ background:{t['warning_bg']}; border-color:{t['warning']}66; color:{t['warning']}; }}
.code-wrap {{ background:{t['card_bg2']}; border:1px solid {t['border']}; border-radius:12px; padding:4px; margin:16px 0; }}
.milestone-flag {{
    background:{t['btn_primary']}; border:1px solid {t['accent2']};
    border-radius:12px; padding:8px 16px; margin:8px auto; text-align:center;
    font-family:'Syne',sans-serif; font-size:0.75rem; font-weight:700;
    color:#fff; max-width:200px; box-shadow:{t['btn_primary_sh']};
}}

/* ── Notes page ── */
.note-card {{
    background:{t['card_bg']}; border:1px solid {t['border']};
    border-radius:14px; padding:20px 22px; margin-bottom:14px;
    transition:border-color 0.2s, box-shadow 0.2s; position:relative;
}}
.note-card:hover {{ border-color:{t['accent_light']}; }}
.note-card.highlight {{ border-left:3px solid {t['orange']}; background:linear-gradient(135deg,{t['warning_bg']},{t['card_bg']}); }}
.note-card.ai-saved {{ border-left:3px solid {t['accent']}; background:linear-gradient(135deg,{t['accent']}18,{t['card_bg']}); }}
.note-card.personal {{ border-left:3px solid #8b5cf6; background:linear-gradient(135deg,#8b5cf618,{t['card_bg']}); }}
.note-meta {{ display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap; }}
.note-subject-tag {{ background:{t['card_bg2']}; border:1px solid {t['accent']}; border-radius:20px; padding:3px 12px; font-size:0.73rem; color:{t['accent_light']}; font-weight:500; }}
.note-topic-tag {{ background:{t['card_bg2']}; border:1px solid #8b5cf6; border-radius:20px; padding:3px 12px; font-size:0.73rem; color:#a78bfa; }}
.note-type-tag {{ border-radius:20px; padding:3px 12px; font-size:0.73rem; font-weight:500; }}
.tag-ai {{ background:{t['accent']}18; border:1px solid {t['accent']}; color:{t['accent_light']}; }}
.tag-hl {{ background:{t['warning_bg']}; border:1px solid {t['orange']}; color:{t['orange']}; }}
.tag-note {{ background:#8b5cf618; border:1px solid #8b5cf6; color:#a78bfa; }}
.note-time {{ font-size:0.7rem; color:{t['text_muted']}; margin-left:auto; }}
.note-content {{ font-size:0.87rem; color:{t['text_secondary']}; line-height:1.65; border-top:1px solid {t['border']}; padding-top:12px; margin-top:6px; white-space:pre-wrap; }}
.note-title {{ font-family:'Syne',sans-serif; font-size:1.05rem; color:{t['text_primary']}; font-weight:600; margin-bottom:2px; }}
.highlight-text {{ background:linear-gradient(120deg,{t['orange']}26,{t['orange']}0d); border-left:3px solid {t['orange']}; border-radius:0 8px 8px 0; padding:10px 14px; font-size:0.87rem; color:{t['orange2']}; font-style:italic; line-height:1.6; }}
.stats-bar {{ display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap; }}
.stat-chip {{ background:{t['card_bg']}; border:1px solid {t['border']}; border-radius:10px; padding:10px 18px; text-align:center; flex:1; min-width:100px; }}
.stat-chip .num {{ font-family:'Syne',sans-serif; font-size:1.6rem; font-weight:800; color:{t['text_primary']}; display:block; line-height:1.2; }}
.stat-chip .lbl {{ font-size:0.72rem; color:{t['text_muted']}; text-transform:uppercase; letter-spacing:0.08em; font-weight:600; }}
.empty-state {{ text-align:center; padding:60px 20px; color:{t['text_muted']}; }}
.empty-state .icon {{ font-size:3rem; margin-bottom:16px; }}
.empty-state h3 {{ font-family:'Syne',sans-serif; font-size:1.3rem; font-weight:700; color:{t['text_secondary']}; margin-bottom:8px; }}
.empty-state p {{ font-size:0.85rem; }}
</style>"""


# ─── Inject theme CSS ─────────────────────────────────────────────────────────

def inject_theme():
    """
    Call this on every page right after st.set_page_config().
    Injects the full CSS for the current theme.
    """
    t = get_theme()
    st.markdown(build_css(t), unsafe_allow_html=True)


# ─── Theme toggle widget ──────────────────────────────────────────────────────

def render_theme_toggle():
    """
    Renders a compact toggle button in the sidebar.
    Call this inside any sidebar block.
    """
    t    = get_theme()
    other = LIGHT if is_dark() else DARK

    # Build toggle button HTML
    bg      = t['card_bg']
    border  = t['border']
    color   = t['text_muted']
    acc     = t['accent_light']

    st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:12px;
            padding:8px 12px;margin-bottom:12px;display:flex;
            align-items:center;justify-content:space-between;">
  <div style="display:flex;align-items:center;gap:7px;">
    <span style="font-size:1rem;">{t['emoji']}</span>
    <span style="font-size:0.72rem;font-weight:600;color:{color};
                 text-transform:uppercase;letter-spacing:0.1em;">{t['label']} Mode</span>
  </div>
  <span style="font-size:0.68rem;color:{acc};">→ {other['emoji']} {other['label']}</span>
</div>
""", unsafe_allow_html=True)

    if st.button(
        f"Switch to {other['emoji']} {other['label']}",
        key="theme_toggle_btn",
        use_container_width=True
    ):
        st.session_state["theme"] = other["name"]
        st.rerun()


# ─── Helper: themed inline div ────────────────────────────────────────────────

def card(content_html: str, accent_color: str = None) -> str:
    """Return a themed card div string for use in st.markdown."""
    t      = get_theme()
    border = accent_color or t['border']
    return (
        f'<div style="background:{t["card_bg"]};border:1px solid {border};'
        f'border-radius:12px;padding:14px 16px;margin-bottom:8px;">'
        f'{content_html}</div>'
    )


def text_color(role: str = "primary") -> str:
    """Return a color string for the given text role in the current theme."""
    t = get_theme()
    return {
        "primary":   t["text_primary"],
        "secondary": t["text_secondary"],
        "muted":     t["text_muted"],
        "faint":     t["text_faint"],
        "accent":    t["accent_light"],
    }.get(role, t["text_secondary"])