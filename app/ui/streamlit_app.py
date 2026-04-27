from __future__ import annotations

from datetime import datetime
from html import escape
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from app.ai.model_registry import default_models
from app.ai.providers.base import ProviderConfig
from app.chatbot.action_parser import recommended_actions
from app.chatbot.llm_client import AIProviderConfig, SpreadsheetAssistantClient
from app.excel_agent.executor import execute_plan
from app.excel_agent.planner import plan_with_provider
from app.excel_agent.profiler import profile_workbook
from app.excel_agent.schemas import AgentDataProfile, PlannerResult, ToolCall, WorkbookContext
from app.excel_agent.tools.registry import ToolContext
from app.models import DataProfile
from app.processing.profiler import profile_file
from app.ui.components import (
    render_action_plan_card,
    render_data_profile_card,
    render_empty_state,
    render_file_context,
    render_header,
    render_message,
    render_preview_expanders,
    render_provider_status,
    render_result_card,
)
from app.ui.styles import inject_css


UPLOAD_DIR = Path("data/uploaded")
GREETING = (
    "Hi, I'm your Excel AI Assistant. Upload a spreadsheet and I'll help you analyze, clean, "
    "format, and turn it into a management-ready workbook."
)


def _env_api_key(provider: str) -> str:
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY", "")
    if provider == "openrouter":
        return os.getenv("OPENROUTER_API_KEY", "")
    return ""


def _env_base_url(provider: str) -> str:
    if provider == "openai":
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if provider == "openrouter":
        return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return "https://api.openai.com/v1"


def _init_state() -> None:
    default_openai_key = os.getenv("OPENAI_API_KEY", "")
    defaults = {
        "stage": "idle",
        "uploaded_file_path": None,
        "original_df": None,
        "data_profile": None,
        "chat_history": [],
        "selected_actions": [],
        "cleaning_plan": None,
        "cleaning_result": None,
        "output_file_path": None,
        "recommended_action_names": [],
        "current_file_signature": None,
        "last_error": None,
        "original_preview": None,
        "cleaned_preview": None,
        "chat_messages": [],
        "uploaded_file_name": None,
        "uploaded_file_type": None,
        "workbook_context": None,
        "agent_data_profile": None,
        "working_df": None,
        "pending_tool_call": None,
        "pending_action_plan": None,
        "operation_history": [],
        "snapshots": [],
        "artifacts": {},
        "formatting": [],
        "latest_output_path": None,
        "last_tool_results": [],
        "uploader_key": 0,
        "selected_model": "mock-rule-based",
        "selected_provider": "mock",
        "api_key": "",
        "temperature": 0.2,
        "max_tokens": 1200,
        "use_mock": True,
        "provider_status": "Mock provider active. No API key required.",
        "provider_config": {},
        "ai_provider": "rule_based",
        "ai_api_key": default_openai_key,
        "ai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "ai_model": "mock-rule-based",
        "ai_models": [],
        "ai_connection_status": "Mock provider active. No API key required.",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not st.session_state.chat_history:
        _add_message("assistant", GREETING)
    _sync_provider_aliases()


def _sync_provider_aliases() -> None:
    provider = "mock" if st.session_state.ai_provider in {"rule_based", "mock"} else st.session_state.ai_provider
    st.session_state.selected_provider = provider
    st.session_state.selected_model = st.session_state.ai_model
    st.session_state.api_key = st.session_state.ai_api_key
    st.session_state.temperature = float(st.session_state.get("temperature", 0.2))
    st.session_state.max_tokens = int(st.session_state.get("max_tokens", 1200))
    st.session_state.use_mock = provider == "mock" or not st.session_state.ai_api_key.strip()
    st.session_state.provider_status = st.session_state.ai_connection_status


def _add_message(role: str, content: str) -> None:
    st.session_state.chat_history.append({"role": role, "content": content})


def _ai_config() -> AIProviderConfig:
    return AIProviderConfig(
        provider=st.session_state.ai_provider,
        api_key=st.session_state.ai_api_key,
        base_url=st.session_state.ai_base_url,
        model=st.session_state.ai_model,
    )


def _agent_provider_config() -> ProviderConfig:
    provider = "mock" if st.session_state.ai_provider in {"rule_based", "mock"} else st.session_state.ai_provider
    return ProviderConfig(
        provider=provider,
        api_key=st.session_state.ai_api_key,
        base_url=st.session_state.ai_base_url,
        model=st.session_state.ai_model,
        temperature=float(st.session_state.get("temperature", 0.2)),
        max_tokens=int(st.session_state.get("max_tokens", 1200)),
    )


def _assistant_client() -> SpreadsheetAssistantClient:
    return SpreadsheetAssistantClient(config=_ai_config())


def _reset_file_state() -> None:
    for key in [
        "uploaded_file_path",
        "uploaded_file_name",
        "uploaded_file_type",
        "original_df",
        "working_df",
        "workbook_context",
        "data_profile",
        "agent_data_profile",
        "pending_action_plan",
        "pending_tool_call",
        "cleaning_plan",
        "cleaning_result",
        "output_file_path",
        "latest_output_path",
        "original_preview",
        "cleaned_preview",
        "current_file_signature",
        "last_error",
    ]:
        st.session_state[key] = None
    st.session_state.operation_history = []
    st.session_state.artifacts = {}
    st.session_state.formatting = []
    st.session_state.snapshots = []
    st.session_state.last_tool_results = []
    st.session_state.uploader_key = int(st.session_state.get("uploader_key", 0)) + 1
    st.session_state.stage = "idle"


def _new_chat() -> None:
    _reset_file_state()
    st.session_state.chat_history = []
    st.session_state.chat_messages = []
    _add_message("assistant", GREETING)


def _reset_settings() -> None:
    st.session_state.ai_provider = "rule_based"
    st.session_state.ai_api_key = ""
    st.session_state.ai_base_url = "https://api.openai.com/v1"
    st.session_state.ai_model = "mock-rule-based"
    st.session_state.ai_models = []
    st.session_state.temperature = 0.2
    st.session_state.max_tokens = 1200
    st.session_state.ai_connection_status = "Mock provider active. No API key required."
    _sync_provider_aliases()


def _build_profile_review(profile: DataProfile, agent_profile: AgentDataProfile | None = None) -> str:
    total_missing = sum(profile.missing_values.values())
    date_cols = agent_profile.date_like_columns if agent_profile else profile.suspected_date_columns
    numeric_cols = agent_profile.suspicious_numeric_text_columns if agent_profile else profile.suspected_numeric_columns
    return (
        f"I've read `{profile.file_name}`. It has {profile.rows} rows and {profile.columns} columns.\n\n"
        "I found several potential issues in your spreadsheet:\n"
        f"- {total_missing} missing values\n"
        f"- {profile.duplicate_count} duplicate rows\n"
        f"- {len(date_cols)} date-like columns\n"
        f"- {len(numeric_cols)} numeric-looking text columns\n"
        f"- {len(profile.whitespace_issues)} columns with whitespace issues\n\n"
        "I can help clean and format it safely. I'll ask for confirmation before running actions that modify data or workbook structure."
    )


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-logo">
                <div class="sidebar-logo-mark">📊</div>
                <div>
                    <div class="sidebar-logo-title">Excel AI</div>
                    <div class="sidebar-logo-subtitle">Spreadsheet Agent</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("+ New Chat", use_container_width=True):
                _new_chat()
                st.rerun()
        with col_b:
            if st.button("Clear File", use_container_width=True):
                _reset_file_state()
                _sync_chat_message("assistant", "File context cleared. Upload a new spreadsheet when you're ready.")
                st.rerun()

        st.markdown('<div class="sidebar-section-label">Upload</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload CSV or Excel",
            type=["csv", "xlsx"],
            key=f"sidebar_uploader_{st.session_state.uploader_key}",
            help="Upload a messy spreadsheet to analyze, clean, and transform.",
        )
        if uploaded_file is not None:
            _profile_uploaded_file(uploaded_file)

        st.markdown('<div class="sidebar-section-label">File Context</div>', unsafe_allow_html=True)
        render_file_context(st.session_state.data_profile, st.session_state.latest_output_path)

        st.markdown('<div class="sidebar-section-label">AI Settings</div>', unsafe_allow_html=True)
        provider_labels = {"rule_based": "Mock", "openai": "OpenAI", "openrouter": "OpenRouter"}
        providers = list(provider_labels)
        current_provider = st.session_state.ai_provider if st.session_state.ai_provider in providers else "rule_based"
        selected_label = st.selectbox(
            "Provider",
            [provider_labels[item] for item in providers],
            index=providers.index(current_provider),
        )
        selected_provider = next(key for key, label in provider_labels.items() if label == selected_label)
        if selected_provider != st.session_state.ai_provider:
            st.session_state.ai_provider = selected_provider
            st.session_state.ai_models = []
            st.session_state.ai_api_key = _env_api_key(selected_provider)
            st.session_state.ai_base_url = _env_base_url(selected_provider)
            st.session_state.ai_model = default_models("mock" if selected_provider == "rule_based" else selected_provider)[0]

        if st.session_state.ai_provider == "rule_based":
            st.session_state.ai_api_key = ""
            st.session_state.ai_connection_status = "Mock provider active. No API key required."
            st.session_state.ai_model = st.selectbox("Model", default_models("mock"), index=0)
            st.text_input("API key", value="", type="password", disabled=True, help="Mock provider does not require an API key.")
        else:
            if st.session_state.ai_provider == "openrouter":
                st.session_state.ai_base_url = _env_base_url("openrouter")
                st.text_input("Base URL", value=st.session_state.ai_base_url, disabled=True)
                if st.session_state.ai_model not in default_models("openrouter"):
                    st.session_state.ai_model = "openrouter/free"
            else:
                st.session_state.ai_base_url = st.text_input("Base URL", value=st.session_state.ai_base_url)
            if not st.session_state.ai_api_key:
                st.session_state.ai_api_key = _env_api_key(st.session_state.ai_provider)
            st.session_state.ai_api_key = st.text_input("API key", value=st.session_state.ai_api_key, type="password")
            model_options = st.session_state.ai_models or default_models(st.session_state.ai_provider)
            if st.session_state.ai_model not in model_options:
                st.session_state.ai_model = model_options[0]
            st.session_state.ai_model = st.selectbox("Model", model_options, index=model_options.index(st.session_state.ai_model))
            if st.session_state.ai_api_key.strip():
                st.session_state.ai_connection_status = "API key configured. Use Test provider connection to validate models."
            else:
                st.session_state.ai_connection_status = "API key missing. The app will safely fall back to Mock planning."
            if st.button("Test provider connection", use_container_width=True):
                ok, message, models = _assistant_client().test_connection() if st.session_state.ai_api_key.strip() else (False, "API key is empty.", [])
                st.session_state.ai_connection_status = message
                if ok and models:
                    st.session_state.ai_models = models
                    st.session_state.ai_model = models[0]
                st.rerun()
        st.session_state.temperature = st.slider("Temperature", 0.0, 1.0, float(st.session_state.get("temperature", 0.2)), 0.1)
        st.session_state.max_tokens = st.number_input("Max tokens", min_value=256, max_value=8000, value=int(st.session_state.get("max_tokens", 1200)), step=256)
        _sync_provider_aliases()
        render_provider_status(st.session_state.selected_provider, st.session_state.api_key, st.session_state.provider_status)
        if st.button("Reset settings", use_container_width=True):
            _reset_settings()
            st.rerun()

        st.markdown('<div class="sidebar-section-label">Operations</div>', unsafe_allow_html=True)
        history = st.session_state.operation_history[-5:]
        if history:
            for item in history:
                st.markdown(f'<div class="sidebar-op">{escape(str(item))}</div>', unsafe_allow_html=True)
        else:
            st.caption("No operations yet")
        if st.session_state.latest_output_path and Path(st.session_state.latest_output_path).exists():
            output_path = Path(st.session_state.latest_output_path)
            st.download_button(
                "Download latest output",
                output_path.read_bytes(),
                file_name=output_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


def _sync_chat_message(role: str, content: str) -> None:
    _add_message(role, content)
    st.session_state.chat_messages = st.session_state.chat_history


def _tool_context() -> ToolContext:
    return ToolContext(
        original_df=st.session_state.original_df,
        working_df=st.session_state.working_df,
        data_profile=st.session_state.agent_data_profile,
        operation_history=st.session_state.operation_history,
        snapshots=st.session_state.get("snapshots", []),
        artifacts=st.session_state.get("artifacts", {}),
        formatting=st.session_state.get("formatting", []),
        latest_output_path=st.session_state.latest_output_path,
    )


def _save_tool_context(ctx: ToolContext) -> None:
    st.session_state.working_df = ctx.working_df
    st.session_state.operation_history = ctx.operation_history
    st.session_state.snapshots = ctx.snapshots
    st.session_state.artifacts = ctx.artifacts
    st.session_state.formatting = ctx.formatting
    st.session_state.latest_output_path = ctx.latest_output_path
    if ctx.latest_output_path:
        st.session_state.output_file_path = ctx.latest_output_path


def _execute_agent_plan(plan: PlannerResult) -> None:
    if st.session_state.original_df is None or st.session_state.working_df is None:
        _sync_chat_message("assistant", "Upload a spreadsheet before running tools.")
        return
    ctx = _tool_context()
    try:
        results = execute_plan(ctx, plan)
        if plan.tool_calls and not any(call.tool == "export_workbook" for call in plan.tool_calls):
            export_plan = PlannerResult(
                assistant_response="Export workbook",
                tool_calls=[ToolCall(tool="export_workbook", args={})],
            )
            results.extend(execute_plan(ctx, export_plan))
        _save_tool_context(ctx)
        st.session_state.last_tool_results = results
        lines = ["Done. I ran the tool plan:"]
        lines.extend(f"- {result.message}" for result in results)
        if st.session_state.latest_output_path:
            lines.append(f"\nThe output workbook is ready to download: `{st.session_state.latest_output_path}`")
        _sync_chat_message("assistant", "\n".join(lines))
    except Exception as exc:
        st.session_state.last_error = str(exc)
        _sync_chat_message("assistant", f"I couldn't run that plan safely. Detail: {exc}")


def _save_upload(uploaded_file) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in uploaded_file.name)
    path = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    path.write_bytes(uploaded_file.getvalue())
    return path


def _load_profile(path: Path, sheet_name: str | None = None) -> tuple[pd.DataFrame, DataProfile]:
    return profile_file(path, sheet_name=sheet_name)


def _load_agent_profile(path: Path, sheet_name: str | None = None) -> tuple[pd.DataFrame, WorkbookContext, AgentDataProfile]:
    return profile_workbook(path, sheet_name=sheet_name)


def _profile_uploaded_file(uploaded_file) -> None:
    signature = f"{uploaded_file.name}:{getattr(uploaded_file, 'size', len(uploaded_file.getvalue()))}"
    if st.session_state.current_file_signature == signature and st.session_state.data_profile is not None:
        return
    try:
        path = _save_upload(uploaded_file)
        df, workbook_context, agent_profile = _load_agent_profile(path)
        _, profile = _load_profile(path)
        recommended = recommended_actions(profile)
    except Exception as exc:
        st.session_state.stage = "idle"
        st.session_state.uploaded_file_path = None
        st.session_state.original_df = None
        st.session_state.working_df = None
        st.session_state.workbook_context = None
        st.session_state.agent_data_profile = None
        st.session_state.data_profile = None
        st.session_state.cleaning_plan = None
        st.session_state.cleaning_result = None
        st.session_state.output_file_path = None
        st.session_state.original_preview = None
        st.session_state.cleaned_preview = None
        st.session_state.current_file_signature = None
        st.session_state.last_error = str(exc)
        st.session_state.operation_history = []
        st.session_state.chat_history = []
        _add_message("assistant", GREETING)
        _add_message("assistant", f"I couldn't read this file. Please upload a valid CSV or XLSX file. Technical detail: {exc}")
        return

    st.session_state.stage = "waiting_for_user_choices"
    st.session_state.uploaded_file_path = str(path)
    st.session_state.uploaded_file_name = uploaded_file.name
    suffix = Path(uploaded_file.name).suffix.lower().lstrip(".")
    st.session_state.uploaded_file_type = suffix or "unknown"
    st.session_state.original_df = df
    st.session_state.working_df = df.copy()
    st.session_state.workbook_context = workbook_context
    st.session_state.data_profile = profile
    st.session_state.agent_data_profile = agent_profile
    st.session_state.operation_history = [f"Uploaded {uploaded_file.name}"]
    st.session_state.artifacts = {}
    st.session_state.formatting = []
    st.session_state.snapshots = []
    st.session_state.cleaning_plan = None
    st.session_state.cleaning_result = None
    st.session_state.output_file_path = None
    st.session_state.original_preview = df.head(5)
    st.session_state.cleaned_preview = None
    st.session_state.recommended_action_names = [action.action_name for action in recommended]
    st.session_state.selected_actions = st.session_state.recommended_action_names.copy()
    st.session_state.current_file_signature = signature
    st.session_state.last_error = None
    st.session_state.chat_history = []
    _add_message("system", f"📎 Uploaded {uploaded_file.name}")
    _add_message("assistant", _build_profile_review(profile, agent_profile))
    _add_message("assistant", "Try prompts like `Color the division column red`, `Split the table by division`, `Create summary total sales by region`, or `Highlight overdue rows`.")


def _submit_prompt(prompt: str) -> None:
    _sync_chat_message("user", prompt)
    if st.session_state.data_profile is None:
        _sync_chat_message("assistant", "Upload a CSV or Excel file first, then I can analyze it and run spreadsheet tools.")
        return

    plan = plan_with_provider(
        prompt,
        st.session_state.agent_data_profile,
        st.session_state.operation_history,
        _agent_provider_config(),
    )
    _sync_chat_message("assistant", plan.clarification_question or plan.assistant_response)
    if plan.clarification_question:
        st.session_state.stage = "waiting_for_user_choices"
        return
    if not plan.tool_calls:
        st.session_state.stage = "waiting_for_user_choices"
        return
    if plan.needs_confirmation:
        st.session_state.pending_action_plan = plan
        st.session_state.pending_tool_call = plan.tool_calls[0].model_dump()
        st.session_state.stage = "plan_ready"
        return
    st.session_state.pending_action_plan = None
    st.session_state.pending_tool_call = None
    _execute_agent_plan(plan)


def _render_quick_actions() -> None:
    actions = [
        ("Analyze", "Analyze what can be improved"),
        ("Clean", "Remove duplicate rows"),
        ("Format", "Export workbook"),
        ("Split", "Split the table by division"),
        ("Summary", "Create summary total sales by region"),
        ("Report", "Create management report"),
    ]
    st.markdown("#### Quick actions")
    cols = st.columns(3)
    for idx, (label, prompt) in enumerate(actions):
        with cols[idx % 3]:
            if st.button(label, key=f"quick_action_{idx}", use_container_width=True):
                _submit_prompt(prompt)
                st.rerun()


def _render_pending_plan() -> None:
    pending_plan: PlannerResult | None = st.session_state.pending_action_plan
    if pending_plan is None:
        return
    render_action_plan_card(pending_plan)
    if pending_plan.needs_confirmation:
        st.warning("This action may modify your data or workbook structure. Please review the plan before I run it.")
    col_run, col_cancel, col_modify = st.columns([1.2, 1, 1])
    with col_run:
        if st.button("Run this plan", type="primary", use_container_width=True):
            with st.status("Running plan...", expanded=True) as status:
                st.write("Analyzing request...")
                st.write("Applying transformations...")
                _execute_agent_plan(pending_plan)
                st.write("Generating workbook...")
                status.update(label="Done", state="complete")
            st.session_state.pending_action_plan = None
            st.session_state.pending_tool_call = None
            st.rerun()
    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.session_state.pending_action_plan = None
            st.session_state.pending_tool_call = None
            _sync_chat_message("assistant", "Action plan cancelled.")
            st.rerun()
    with col_modify:
        if st.button("Modify request", use_container_width=True):
            _sync_chat_message("assistant", "Tell me what you want to change in the plan, and I will prepare a revised version.")
            st.rerun()


def _render_latest_output() -> None:
    output_path = st.session_state.latest_output_path or st.session_state.output_file_path
    if not output_path or not Path(output_path).exists():
        return
    rows_before = len(st.session_state.original_df) if st.session_state.original_df is not None else None
    rows_after = len(st.session_state.working_df) if st.session_state.working_df is not None else None
    duplicates_removed = max((rows_before or 0) - (rows_after or 0), 0) if rows_before is not None and rows_after is not None else None
    issues_flagged = 0
    for key in ["flagged_issues", "flagged_missing", "flagged_duplicates"]:
        value = st.session_state.get("artifacts", {}).get(key)
        if isinstance(value, pd.DataFrame):
            issues_flagged += len(value)
    split_sheets = st.session_state.get("artifacts", {}).get("split_sheets", {})
    sheets_created = len(split_sheets) if isinstance(split_sheets, dict) else 0
    if st.session_state.last_tool_results:
        render_result_card(
            st.session_state.last_tool_results,
            output_path,
            rows_before=rows_before,
            rows_after=rows_after,
            duplicates_removed=duplicates_removed,
            issues_flagged=issues_flagged,
            sheets_created=sheets_created,
        )
    path = Path(output_path)
    st.download_button(
        "Download output workbook",
        path.read_bytes(),
        file_name=path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(page_title="Excel AI Assistant", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
    _init_state()
    inject_css()

    provider_options = ["Mock", "OpenAI", "OpenRouter"]
    provider_reverse = {"rule_based": "Mock", "mock": "Mock", "openai": "OpenAI", "openrouter": "OpenRouter"}
    provider_map = {"Mock": "rule_based", "OpenAI": "openai", "OpenRouter": "openrouter"}
    model_options_by_provider = {
        "Mock": ["mock", "mock-rule-based"],
        "OpenAI": ["gpt-4.1-mini", "gpt-4.1", "gpt-5.5"],
        "OpenRouter": ["openrouter/auto", "openrouter/free"],
    }
    current_provider_label = provider_reverse.get(st.session_state.ai_provider, "Mock")
    current_model_options = model_options_by_provider.get(current_provider_label, model_options_by_provider["Mock"])
    current_model = st.session_state.ai_model if st.session_state.ai_model in current_model_options else current_model_options[0]
    uploaded_file = None

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-title">📊 Excel AI</div>
                <div class="sidebar-brand-subtitle">Spreadsheet Agent</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown('<div class="sidebar-section-title">Session</div>', unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("+ New Chat", use_container_width=True):
                    _new_chat()
                    st.rerun()
            with col_b:
                if st.button("Clear File", use_container_width=True):
                    _reset_file_state()
                    _sync_chat_message("assistant", "File context cleared. Upload a new spreadsheet when you're ready.")
                    st.rerun()

        with st.container(border=True):
            st.markdown('<div class="sidebar-section-title">Upload Spreadsheet</div>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Upload CSV or Excel",
                type=["csv", "xlsx"],
                help="Upload a spreadsheet to analyze, clean, format, and export.",
                key=f"sidebar_file_uploader_{st.session_state.uploader_key}",
            )
            st.caption("Upload a messy spreadsheet to analyze, clean, and transform.")

        with st.container(border=True):
            st.markdown('<div class="sidebar-section-title">File Context</div>', unsafe_allow_html=True)
            profile = st.session_state.data_profile
            if profile is None:
                st.caption("No file uploaded yet")
            else:
                total_missing = sum(profile.missing_values.values())
                st.markdown(f"**File:** {profile.file_name}")
                st.markdown(f"**Rows x Columns:** {profile.rows} x {profile.columns}")
                st.markdown(f"**Duplicates:** {profile.duplicate_count}")
                st.markdown(f"**Missing values:** {total_missing}")
                st.markdown(f"**Active sheet:** {profile.selected_sheet or 'first sheet / CSV'}")

        with st.container(border=True):
            st.markdown('<div class="sidebar-section-title">AI Settings</div>', unsafe_allow_html=True)
            provider_label = st.selectbox(
                "Provider",
                provider_options,
                index=provider_options.index(current_provider_label),
                key="simple_provider_select",
            )
            selected_model_options = model_options_by_provider.get(provider_label, model_options_by_provider["Mock"])
            if current_model not in selected_model_options:
                current_model = selected_model_options[0]
            model = st.selectbox(
                "Model",
                selected_model_options,
                index=selected_model_options.index(current_model),
                key="simple_model_select",
            )
            api_key = st.text_input(
                "API Key",
                value=st.session_state.api_key,
                type="password",
                key="simple_api_key_input",
            )
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.5,
                value=float(st.session_state.temperature),
                step=0.1,
                key="simple_temperature_slider",
            )
            max_tokens = st.number_input(
                "Max tokens",
                min_value=256,
                max_value=8192,
                value=int(st.session_state.max_tokens),
                step=256,
                key="simple_max_tokens_input",
            )

            if provider_label == "Mock":
                status_class = "info"
                status_text = "Mock mode active"
            elif api_key.strip():
                status_class = "ok"
                status_text = "API key configured"
            else:
                status_class = "warn"
                status_text = "API key missing"
            st.markdown(
                f'<span class="provider-status {status_class}">{status_text}</span>',
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            st.markdown('<div class="sidebar-section-title">Output</div>', unsafe_allow_html=True)
            if st.session_state.latest_output_path and Path(st.session_state.latest_output_path).exists():
                output_path = Path(st.session_state.latest_output_path)
                st.download_button(
                    "Download latest workbook",
                    output_path.read_bytes(),
                    file_name=output_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.caption("No output workbook yet.")

    selected_provider_internal = provider_map[provider_label]
    st.session_state.selected_provider = provider_label
    st.session_state.selected_model = model
    st.session_state.api_key = api_key
    st.session_state.temperature = float(temperature)
    st.session_state.max_tokens = int(max_tokens)
    st.session_state.ai_provider = selected_provider_internal
    st.session_state.ai_model = model
    st.session_state.ai_api_key = "" if selected_provider_internal == "rule_based" else api_key
    st.session_state.ai_base_url = _env_base_url(selected_provider_internal)
    if selected_provider_internal == "rule_based":
        st.session_state.ai_connection_status = "Mock provider active. No API key required."
    elif api_key.strip():
        st.session_state.ai_connection_status = "API key configured."
    else:
        st.session_state.ai_connection_status = "API key missing. The app will safely fall back to Mock planning."
    _sync_provider_aliases()

    if uploaded_file is not None:
        _profile_uploaded_file(uploaded_file)

    profile: DataProfile | None = st.session_state.data_profile
    render_header(has_profile=profile is not None)

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

    if profile is None:
        render_empty_state()

    if profile and profile.sheet_names:
        with st.expander("Workbook sheet", expanded=False):
            selected_sheet = st.selectbox(
                "Active sheet",
                profile.sheet_names,
                index=profile.sheet_names.index(profile.selected_sheet) if profile.selected_sheet in profile.sheet_names else 0,
            )
            if selected_sheet != profile.selected_sheet:
                try:
                    df, agent_context, updated_agent_profile = _load_agent_profile(Path(st.session_state.uploaded_file_path), selected_sheet)
                    _, updated_profile = _load_profile(Path(st.session_state.uploaded_file_path), selected_sheet)
                except Exception as exc:
                    st.session_state.last_error = str(exc)
                    _sync_chat_message("assistant", f"I couldn't read sheet `{selected_sheet}`. Try another sheet or upload again. Detail: {exc}")
                    st.rerun()
                st.session_state.original_df = df
                st.session_state.working_df = df.copy()
                st.session_state.workbook_context = agent_context
                st.session_state.agent_data_profile = updated_agent_profile
                st.session_state.data_profile = updated_profile
                st.session_state.original_preview = df.head(5)
                st.session_state.cleaned_preview = None
                st.session_state.operation_history = [f"Selected sheet {selected_sheet}"]
                st.session_state.selected_actions = [action.action_name for action in recommended_actions(updated_profile)]
                st.session_state.cleaning_plan = None
                st.session_state.stage = "waiting_for_user_choices"
                _sync_chat_message("assistant", _build_profile_review(updated_profile, updated_agent_profile))
                st.rerun()

    for message in st.session_state.chat_history:
        if profile is None and message["role"] == "assistant" and message["content"] == GREETING:
            continue
        render_message(message["role"], message["content"])

    if profile is not None:
        render_data_profile_card(profile, st.session_state.agent_data_profile)
        _render_quick_actions()
        render_preview_expanders(st.session_state.original_df, st.session_state.working_df)

    _render_pending_plan()
    _render_latest_output()

    user_text = st.chat_input("Ask Excel AI what to do with your spreadsheet...")
    if user_text:
        _submit_prompt(user_text)
        st.rerun()


if __name__ == "__main__":
    main()
