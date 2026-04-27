from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

from app.excel_agent.schemas import AgentDataProfile, PlannerResult, ToolExecutionResult
from app.models import DataProfile


def inject_css() -> None:
    from app.ui.styles import inject_css as inject_modern_css

    inject_modern_css()


def render_header(has_profile: bool = False) -> None:
    if has_profile:
        st.markdown(
            """
            <div class="app-header app-header-compact">
                <h1 class="app-title">Excel AI Assistant</h1>
                <div class="app-subtitle">Analyze, clean, format, and transform spreadsheets with AI.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        """
        <div class="app-header app-hero">
            <div class="hero-badge">AI-powered spreadsheet automation</div>
            <h1 class="hero-title">Your spreadsheet, upgraded with AI.</h1>
            <div class="hero-subtitle">
                Upload an Excel or CSV file, then ask the assistant to analyze, clean, format, split,
                summarize, and export a management-ready workbook.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    prompts = [
        ("🔍", "Analyze this spreadsheet"),
        ("🧹", "Clean duplicates and missing values"),
        ("📑", "Split sheets by division"),
        ("🧾", "Create a management report"),
    ]
    chips = "".join(f'<div class="prompt-card"><strong>{icon}</strong>&nbsp; {escape(prompt)}</div>' for icon, prompt in prompts)
    st.markdown(
        f"""
        <div class="empty-card welcome-state">
            <div class="empty-icon-circle">📊</div>
            <div class="empty-title">What would you like to do with your spreadsheet?</div>
            <div class="empty-copy">
                Upload a file from the sidebar, then ask me to analyze, clean, format, split, or summarize it.
            </div>
            <div class="prompt-grid">{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_message(role: str, content: str) -> None:
    safe = escape(content).replace("\n", "<br>")
    if role in {"system", "tool"}:
        st.markdown(f'<div class="system-event"><span class="system-pill">{safe}</span></div>', unsafe_allow_html=True)
        return
    if role == "user":
        st.markdown(
            f'<div class="chat-row user-row"><div class="chat-bubble user-bubble">{safe}</div></div>',
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        f"""
        <div class="chat-row">
            <div class="assistant-avatar">AI</div>
            <div class="chat-bubble assistant-bubble"><div class="assistant-content">{safe}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_data_profile_card(profile: DataProfile, agent_profile: AgentDataProfile | None = None) -> None:
    total_missing = sum(profile.missing_values.values())
    date_cols = agent_profile.date_like_columns if agent_profile else profile.suspected_date_columns
    numeric_cols = agent_profile.suspicious_numeric_text_columns if agent_profile else profile.suspected_numeric_columns
    issues = profile.detected_issues[:5] or ["No major issues detected from the current profile."]
    issue_items = "".join(f"<li>{escape(issue)}</li>" for issue in issues)
    st.markdown(
        f"""
        <div class="soft-card">
            <div class="section-title">Data Profile</div>
            <div class="muted">{escape(profile.file_name)}{f" · Sheet: {escape(str(profile.selected_sheet))}" if profile.selected_sheet else ""}</div>
            <div class="metric-grid">
                <div class="metric-card"><div class="metric-label">Rows</div><div class="metric-value">{profile.rows}</div></div>
                <div class="metric-card"><div class="metric-label">Columns</div><div class="metric-value">{profile.columns}</div></div>
                <div class="metric-card"><div class="metric-label">Duplicates</div><div class="metric-value">{profile.duplicate_count}</div></div>
                <div class="metric-card"><div class="metric-label">Missing values</div><div class="metric-value">{total_missing}</div></div>
            </div>
            <div class="muted">Date-like columns: {escape(', '.join(date_cols) or 'none detected')}</div>
            <div class="muted">Numeric text columns: {escape(', '.join(numeric_cols) or 'none detected')}</div>
            <div class="section-title" style="margin-top:0.85rem;">Detected Issues</div>
            <ul>{issue_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_action_plan_card(plan: PlannerResult) -> None:
    rows = []
    for call in plan.tool_calls:
        destructive = call.tool in {"remove_duplicate_rows", "fill_missing_values"}
        formatting = call.tool in {"highlight_column", "highlight_rows_by_condition", "export_workbook"}
        if destructive:
            badge, badge_class = "Destructive", "badge-danger"
        elif call.requires_confirmation or plan.needs_confirmation:
            badge, badge_class = "Needs confirmation", "badge-warn"
        elif formatting:
            badge, badge_class = "Formatting only", "badge-blue"
        else:
            badge, badge_class = "Safe", "badge-safe"
        args = ", ".join(f"{key}: {value}" for key, value in call.args.items()) or "default settings"
        icon = "⚙️"
        if "highlight" in call.tool:
            icon = "🎨"
        elif "split" in call.tool:
            icon = "📑"
        elif "summary" in call.tool or "report" in call.tool:
            icon = "📊"
        elif "duplicate" in call.tool:
            icon = "🧹"
        elif "export" in call.tool:
            icon = "📦"
        label = call.tool.replace("_", " ").title()
        rows.append(
            f"""
            <div class="action-row">
                <div>
                    <strong>{icon} {escape(label)}</strong>
                    <div class="muted">{escape(args)}</div>
                </div>
                <div><span class="badge {badge_class}">{badge}</span></div>
            </div>
            """
        )
    st.markdown(
        f"""
        <div class="soft-card">
            <div class="section-title">Proposed Action Plan</div>
            <div class="section-subtitle">Please review before I modify your workbook. Actions are validated against the safe tool registry.</div>
            {''.join(rows)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result_card(
    results: Iterable[ToolExecutionResult],
    output_path: str | None,
    rows_before: int | None = None,
    rows_after: int | None = None,
    duplicates_removed: int | None = None,
    issues_flagged: int | None = None,
    sheets_created: int | None = None,
) -> None:
    items = "".join(f"<li>{escape(result.message)}</li>" for result in results)
    output = escape(output_path or "No output file yet")
    metrics = ""
    if rows_before is not None:
        metrics = f"""
        <div class="metric-grid">
            <div class="metric-card"><div class="metric-label">Rows before</div><div class="metric-value">{rows_before}</div></div>
            <div class="metric-card"><div class="metric-label">Rows after</div><div class="metric-value">{rows_after if rows_after is not None else '-'}</div></div>
            <div class="metric-card"><div class="metric-label">Duplicates removed</div><div class="metric-value">{duplicates_removed if duplicates_removed is not None else 0}</div></div>
            <div class="metric-card"><div class="metric-label">Issues flagged</div><div class="metric-value">{issues_flagged if issues_flagged is not None else 0}</div></div>
        </div>
        <div class="muted">Sheets created: {sheets_created if sheets_created is not None else 0}</div>
        """
    st.markdown(
        f"""
        <div class="soft-card success-card">
            <div class="section-title success-title">✓ Workbook generated successfully <span class="badge badge-safe">Done</span></div>
            {metrics}
            <ul>{items}</ul>
            <div class="muted">Latest output: {output}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_provider_status(provider: str, api_key: str, status_message: str) -> None:
    if provider in {"mock", "rule_based"}:
        label = "Mock mode active"
        badge_class = "badge-warn"
    elif api_key.strip():
        label = "API key configured"
        badge_class = "badge-safe"
    else:
        label = "API key missing"
        badge_class = "badge-warn"
    st.markdown(
        f"""
        <div class="sidebar-file-card">
            <div class="sidebar-file-name">Provider status <span class="badge {badge_class}">{escape(label)}</span></div>
            <div class="sidebar-file-meta">{escape(status_message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_file_context(profile: DataProfile | None, latest_output_path: str | None) -> None:
    if profile is None:
        st.markdown(
            """
            <div class="sidebar-file-card">
                <div class="sidebar-file-name">No file uploaded yet</div>
                <div class="sidebar-file-meta">Upload a CSV or XLSX file to start.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    total_missing = sum(profile.missing_values.values())
    file_type = profile.file_type.upper()
    latest = f'<div class="sidebar-file-meta">Latest output: {escape(Path(latest_output_path).name)}</div>' if latest_output_path else ""
    st.markdown(
        f"""
        <div class="sidebar-file-card">
            <div class="sidebar-file-name">{escape(profile.file_name)}</div>
            <div class="sidebar-file-meta">Type: {escape(file_type)}</div>
            <div class="sidebar-file-meta">{profile.rows} rows × {profile.columns} columns</div>
            <div class="sidebar-file-meta">Active sheet: {escape(str(profile.selected_sheet or 'first sheet / CSV'))}</div>
            <div class="sidebar-file-meta">Duplicates: {profile.duplicate_count}</div>
            <div class="sidebar-file-meta">Missing values: {total_missing}</div>
            {latest}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_preview_expanders(original_df: pd.DataFrame | None, working_df: pd.DataFrame | None) -> None:
    if original_df is not None:
        with st.expander("Preview uploaded data", expanded=False):
            st.dataframe(original_df.head(20), use_container_width=True)
    if working_df is not None and original_df is not None and not working_df.equals(original_df):
        with st.expander("Preview current working data", expanded=False):
            st.dataframe(working_df.head(20), use_container_width=True)
