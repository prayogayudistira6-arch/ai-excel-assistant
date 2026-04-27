from __future__ import annotations

import streamlit as st

APPLE_THEME = {
    "page-bg": "#F5F5F7",
    "main-surface": "#FFFFFF",
    "sidebar-bg": "#FBFBFD",
    "card-bg": "#FFFFFF",
    "surface-2": "#F9FAFB",
    "text-primary": "#1D1D1F",
    "text-secondary": "#6E6E73",
    "text-tertiary": "#86868B",
    "placeholder": "#A1A1AA",
    "border": "rgba(0, 0, 0, 0.08)",
    "border-soft": "rgba(0, 0, 0, 0.05)",
    "accent": "#0071E3",
    "accent-hover": "#0077ED",
    "accent-soft": "#EAF4FF",
    "accent-soft-border": "#BBDFFF",
    "success": "#34C759",
    "warning": "#FF9F0A",
    "danger": "#FF3B30",
    "success-soft": "#ECFDF5",
    "warning-soft": "#FFF7ED",
    "danger-soft": "#FEF2F2",
    "control-border": "rgba(0, 0, 0, 0.12)",
}


def _root_vars() -> str:
    return "\n".join(f"        --{key}: {value};" for key, value in APPLE_THEME.items())


def _safe_css() -> str:
    return """
    <style>
    :root {
__ROOT_VARS__
    }

    #MainMenu, footer, [data-testid="stDecoration"] {
        visibility: hidden !important;
        display: none !important;
    }

    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background: var(--page-bg) !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stMain"] {
        background: var(--page-bg) !important;
    }

    .block-container {
        max-width: 960px !important;
        padding-top: 0.9rem !important;
        padding-bottom: 6.4rem !important;
    }

    section[data-testid="stSidebar"] {
        background: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border) !important;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 1rem !important;
    }

    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--card-bg) !important;
        border: 1px solid var(--border) !important;
        border-radius: 18px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        padding: 0.72rem 0.8rem !important;
        margin-bottom: 0.78rem !important;
    }

    .sidebar-brand {
        margin-bottom: 0.45rem;
    }

    .sidebar-brand-title {
        margin: 0;
        color: var(--text-primary);
        font-size: 1.08rem;
        font-weight: 720;
        line-height: 1.2;
        letter-spacing: -0.01em;
    }

    .sidebar-brand-subtitle {
        margin-top: 0.12rem;
        color: var(--text-secondary);
        font-size: 0.78rem;
    }

    .sidebar-section-title {
        color: var(--text-secondary);
        font-size: 0.76rem;
        font-weight: 680;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.45rem;
    }

    .sidebar-file-card {
        background: var(--surface-2);
        border: 1px solid var(--border-soft);
        border-radius: 14px;
        padding: 0.62rem 0.72rem;
        margin-top: 0.34rem;
    }

    .sidebar-file-name {
        color: var(--text-primary);
        font-size: 0.86rem;
        font-weight: 640;
        line-height: 1.35;
    }

    .sidebar-file-meta {
        color: var(--text-secondary);
        font-size: 0.78rem;
        margin-top: 0.2rem;
        line-height: 1.35;
    }

    .sidebar-op {
        color: var(--text-secondary);
        font-size: 0.78rem;
        border-bottom: 1px solid var(--border-soft);
        padding: 0.28rem 0;
    }

    .provider-status {
        margin-top: 0.32rem;
        border-radius: 999px;
        padding: 0.24rem 0.58rem;
        font-size: 0.74rem;
        font-weight: 620;
        display: inline-block;
        border: 1px solid transparent;
        background: var(--surface-2);
        color: var(--text-secondary);
    }
    .provider-status.ok {
        background: var(--success-soft);
        color: #0f5132;
        border-color: rgba(52, 199, 89, 0.35);
    }
    .provider-status.warn {
        background: var(--warning-soft);
        color: #92400e;
        border-color: rgba(255, 159, 10, 0.35);
    }
    .provider-status.info {
        background: var(--accent-soft);
        color: var(--accent);
        border-color: var(--accent-soft-border);
    }

    .app-header {
        margin: 0 auto 0.62rem auto;
    }

    .app-hero {
        text-align: center;
        padding: 2.3rem 0 1.2rem 0;
    }

    .hero-badge {
        display: inline-block;
        background: var(--accent-soft);
        border: 1px solid var(--accent-soft-border);
        color: var(--accent);
        border-radius: 999px;
        font-size: 0.79rem;
        font-weight: 610;
        padding: 0.34rem 0.76rem;
        margin-bottom: 0.82rem;
    }

    .hero-title {
        margin: 0;
        color: var(--text-primary);
        font-size: clamp(2.15rem, 6vw, 3.9rem);
        font-weight: 740;
        letter-spacing: -0.02em;
        line-height: 1.05;
    }

    .hero-subtitle {
        margin: 0.9rem auto 0 auto;
        max-width: 770px;
        color: var(--text-secondary);
        font-size: 1rem;
        line-height: 1.58;
    }

    .app-header-compact {
        padding-top: 0.26rem;
    }

    .app-title {
        margin: 0;
        color: var(--text-primary);
        font-size: 1.56rem;
        font-weight: 720;
        letter-spacing: -0.01em;
    }

    .app-subtitle {
        margin-top: 0.28rem;
        color: var(--text-secondary);
        font-size: 0.95rem;
    }

    .soft-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        padding: 0.9rem 1rem;
        margin: 0.65rem 0;
    }

    .welcome-state {
        max-width: 780px;
        margin: 0 auto 0.8rem auto;
        border: 0;
        background: transparent;
        box-shadow: none;
        padding-top: 0.3rem;
    }

    .empty-icon-circle {
        width: 62px;
        height: 62px;
        margin: 0 auto 0.76rem auto;
        border-radius: 20px;
        display: grid;
        place-items: center;
        font-size: 1.7rem;
        border: 1px solid var(--accent-soft-border);
        background: linear-gradient(135deg, var(--accent-soft), #f4fbff);
    }

    .empty-title {
        color: var(--text-primary);
        font-size: 1.34rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }

    .empty-copy {
        max-width: 640px;
        margin: 0 auto 0.78rem auto;
        color: var(--text-secondary);
        line-height: 1.56;
    }

    .prompt-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.62rem;
        margin-top: 0.76rem;
    }

    .prompt-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        color: #374151;
        padding: 0.7rem 0.82rem;
        font-size: 0.88rem;
        text-align: left;
    }

    .prompt-card:hover {
        background: var(--surface-2);
        border-color: var(--accent-soft-border);
    }

    .chat-row {
        display: flex;
        align-items: flex-start;
        gap: 0.58rem;
        margin: 0.36rem 0 0.52rem 0;
    }
    .chat-row.user-row { justify-content: flex-end; }

    .assistant-avatar {
        width: 30px;
        height: 30px;
        border-radius: 999px;
        display: grid;
        place-items: center;
        background: #fff7ed;
        border: 1px solid rgba(255, 159, 10, 0.28);
        color: #c2410c;
        font-size: 0.76rem;
        font-weight: 700;
        flex: 0 0 auto;
        margin-top: 0.1rem;
    }

    .chat-bubble {
        border: 1px solid var(--border);
        border-radius: 20px;
        line-height: 1.52;
        font-size: 0.95rem;
        padding: 0.72rem 0.92rem;
        max-width: min(72%, 760px);
    }

    .assistant-bubble {
        background: var(--card-bg);
        color: var(--text-primary);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        max-width: min(760px, 95%);
    }

    .assistant-content { color: var(--text-primary); }

    .user-bubble {
        background: var(--accent-soft);
        border-color: var(--accent-soft-border);
        color: var(--text-primary);
    }

    .system-event {
        margin: 0.5rem 0;
        text-align: center;
    }

    .system-pill {
        display: inline-flex;
        align-items: center;
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 0.34rem 0.67rem;
        background: var(--surface-2);
        color: var(--text-tertiary);
        font-size: 0.77rem;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.6rem;
        margin: 0.74rem 0 0.35rem 0;
    }

    .metric-card {
        background: var(--surface-2);
        border: 1px solid var(--border-soft);
        border-radius: 13px;
        padding: 0.68rem;
    }

    .metric-label {
        color: var(--text-tertiary);
        font-size: 0.76rem;
        margin-bottom: 0.24rem;
    }

    .metric-value {
        color: var(--text-primary);
        font-size: 1.08rem;
        font-weight: 700;
    }

    .section-title {
        color: var(--text-primary);
        font-weight: 700;
        margin-bottom: 0.38rem;
    }

    .section-subtitle {
        color: var(--text-secondary);
        font-size: 0.88rem;
        margin-bottom: 0.62rem;
    }

    .badge {
        display: inline-block;
        border-radius: 999px;
        padding: 0.16rem 0.5rem;
        margin-left: 0.35rem;
        font-size: 0.74rem;
        font-weight: 670;
        white-space: nowrap;
        border: 1px solid transparent;
    }
    .badge-safe { background: var(--success-soft); color: #166534; border-color: rgba(52, 199, 89, 0.3); }
    .badge-warn { background: var(--warning-soft); color: #92400e; border-color: rgba(255, 159, 10, 0.3); }
    .badge-danger { background: var(--danger-soft); color: #991b1b; border-color: rgba(255, 59, 48, 0.25); }
    .badge-blue { background: var(--accent-soft); color: var(--accent); border-color: var(--accent-soft-border); }

    .action-row {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: flex-start;
        padding: 0.8rem 0;
        border-top: 1px solid var(--border-soft);
    }

    .action-row:first-of-type { border-top: 0; }

    .muted {
        color: var(--text-secondary);
        font-size: 0.86rem;
    }

    .success-card {
        border-color: rgba(52, 199, 89, 0.35);
        background: #ffffff;
    }

    .success-title {
        color: #0f5132;
        font-weight: 760;
    }

    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: 999px !important;
        border: 1px solid var(--control-border) !important;
        background: var(--card-bg) !important;
        color: var(--text-primary) !important;
        min-height: 2.2rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }

    div.stButton > button:hover,
    div.stDownloadButton > button:hover {
        border-color: var(--accent-soft-border) !important;
        background: var(--surface-2) !important;
        color: var(--accent) !important;
    }

    div.stButton > button[kind="primary"] {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #ffffff !important;
    }

    div.stButton > button[kind="primary"]:hover {
        background: var(--accent-hover) !important;
        border-color: var(--accent-hover) !important;
    }

    div[data-testid="stFileUploader"] {
        background: var(--card-bg) !important;
        border: 1px dashed var(--control-border) !important;
        border-radius: 14px !important;
        padding: 0.4rem !important;
    }

    div[data-testid="stFileUploader"] section {
        background: var(--surface-2) !important;
        border-radius: 12px !important;
        border: 0 !important;
        min-height: 0 !important;
    }

    div[data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] {
        color: var(--text-tertiary) !important;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"] > div,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stPasswordInput"] input {
        background: var(--card-bg) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--control-border) !important;
        border-radius: 12px !important;
    }

    div[data-baseweb="select"] > div *,
    div[data-baseweb="input"] > div *,
    div[data-baseweb="base-input"] > div * {
        color: var(--text-primary) !important;
    }

    div[data-baseweb="select"]:focus-within > div,
    div[data-baseweb="input"]:focus-within > div,
    div[data-baseweb="base-input"]:focus-within > div,
    div[data-testid="stTextInput"]:focus-within input,
    div[data-testid="stNumberInput"]:focus-within input,
    div[data-testid="stPasswordInput"]:focus-within input {
        border-color: var(--accent-soft-border) !important;
        box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.14) !important;
    }

    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label {
        color: var(--text-secondary) !important;
    }

    div[data-testid="stBottom"],
    div[data-testid="stBottom"] > div,
    div[data-testid="stBottomBlockContainer"],
    div[data-testid="stChatFloatingInputContainer"] {
        background: var(--page-bg) !important;
        border: 0 !important;
        box-shadow: none !important;
    }

    div[data-testid="stBottom"] {
        padding: 0 0.8rem 0.74rem 0.8rem !important;
    }

    div[data-testid="stBottomBlockContainer"] {
        max-width: 840px !important;
        margin: 0 auto !important;
        padding: 0 !important;
    }

    div[data-testid="stChatInput"] {
        max-width: 840px !important;
        margin: 0 auto !important;
        background: transparent !important;
    }

    div[data-testid="stChatInput"] > div:first-child {
        min-height: 56px !important;
        border: 1px solid var(--control-border) !important;
        border-radius: 28px !important;
        background: var(--card-bg) !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08) !important;
        padding: 0.34rem 0.6rem 0.34rem 0.86rem !important;
    }

    div[data-testid="stChatInput"] textarea,
    div[data-testid="stChatInput"] textarea:focus {
        min-height: 44px !important;
        background: var(--card-bg) !important;
        color: var(--text-primary) !important;
        border: 0 !important;
        outline: 0 !important;
        box-shadow: none !important;
    }

    div[data-testid="stChatInput"] textarea::placeholder {
        color: var(--placeholder) !important;
    }

    div[data-testid="stChatInput"] button,
    div[data-testid="stChatInput"] button:hover {
        width: 2.2rem !important;
        height: 2.2rem !important;
        border-radius: 999px !important;
        background: var(--accent) !important;
        border: 1px solid var(--accent) !important;
        color: #ffffff !important;
    }

    div[data-testid="stChatInput"] button:hover {
        background: var(--accent-hover) !important;
        border-color: var(--accent-hover) !important;
    }

    div[data-testid="stExpander"] {
        background: var(--card-bg) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }

    @media (max-width: 760px) {
        .hero-title { font-size: 2rem; }
        .metric-grid, .prompt-grid { grid-template-columns: 1fr; }
        .chat-bubble { max-width: 92%; }
    }
    </style>
    """.replace("__ROOT_VARS__", _root_vars())


def inject_css() -> None:
    st.markdown(_safe_css(), unsafe_allow_html=True)
