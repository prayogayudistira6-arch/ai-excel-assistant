from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.ai.providers.base import ProviderConfig
from app.ai.model_registry import create_provider
from app.excel_agent.schemas import AgentDataProfile, PlannerResult, ToolCall
from app.excel_agent.tools.registry import available_tools, get_tool


SYSTEM_PROMPT = """You are a safe Excel AI agent.
You may answer questions using only the workbook profile, sample rows, statistics, and operation history.
You must not write or execute Python code.
When an action is needed, return JSON matching PlannerResult with tool_calls selected only from available tools.
Ask a clarification question if the user request is ambiguous."""


def _norm(value: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", value.lower())


def _find_column(profile: AgentDataProfile, text: str, aliases: dict[str, list[str]] | None = None) -> str | None:
    normalized_text = _norm(text)
    for col in profile.column_names:
        normalized_col = _norm(col)
        if normalized_col and normalized_col in normalized_text:
            return col
    aliases = aliases or {}
    for canonical, values in aliases.items():
        if any(alias in normalized_text for alias in values):
            for col in profile.column_names:
                normalized_col = _norm(col)
                if canonical in normalized_col or any(alias in normalized_col for alias in values):
                    return col
    return None


def _first_existing(profile: AgentDataProfile, candidates: list[str]) -> str | None:
    for candidate in candidates:
        found = _find_column(profile, candidate)
        if found:
            return found
    return None


def _answer_profile_question(message: str, profile: AgentDataProfile) -> str:
    issues = profile.detected_issues or ["No major issues were detected from the current profile."]
    if any(word in message for word in ["apa yang bisa", "analisa", "insight", "improved", "diperbaiki"]):
        return (
            f"I see {profile.total_rows} rows and {profile.total_columns} columns. "
            f"Main issues: {'; '.join(issues)}. "
            f"Recommended actions: {', '.join(profile.recommended_actions)}."
        )
    if "missing" in message or "kosong" in message:
        return f"Total missing values: {sum(profile.missing_values.values())}. Details by column: {profile.missing_values}."
    if "duplicate" in message or "duplikat" in message:
        return f"I found {profile.duplicate_count} duplicate rows."
    return f"Available columns: {', '.join(profile.column_names)}. I can help analyze, clean, highlight, split sheets, create summaries, build pivots, generate management reports, or export the workbook."


def fallback_plan(user_message: str, profile: AgentDataProfile | None, operation_history: list[str] | None = None) -> PlannerResult:
    text = user_message.lower().strip()
    if profile is None:
        return PlannerResult(assistant_response="Upload an Excel/CSV file first so I can analyze it and run tools.", confidence=1.0)

    calls: list[ToolCall] = []
    needs_confirmation = False

    color = "red" if "merah" in text or "red" in text else "yellow" if "kuning" in text or "yellow" in text else "green" if "hijau" in text or "green" in text else "red"
    aliases = {
        "divisi": ["divisi", "division", "departemen", "department"],
        "status": ["status"],
        "region": ["region", "wilayah"],
        "sales": ["sales", "revenue", "pendapatan", "total"],
        "gaji": ["gaji", "salary", "upah"],
        "tanggal": ["tanggal", "date"],
    }

    if any(word in text for word in ["warna", "color", "highlight"]) and "baris" not in text and "row" not in text:
        column = _find_column(profile, text, aliases)
        if not column:
            return PlannerResult(assistant_response="Which column should I color?", clarification_question="Which column should I color?", confidence=0.9)
        calls.append(ToolCall(tool="highlight_column", args={"column": column, "color": color}))

    if ("overdue" in text or "terlambat" in text) and ("highlight" in text or "warna" in text or "baris" in text):
        column = _find_column(profile, "status", aliases) or _find_column(profile, text, aliases)
        if not column:
            return PlannerResult(assistant_response="Which status column should I use to highlight overdue rows?", clarification_question="Which status column should I use?", confidence=0.8)
        calls.append(ToolCall(tool="highlight_rows_by_condition", args={"column": column, "equals": "overdue", "color": "yellow"}))

    if any(word in text for word in ["split", "pisah", "terpisah"]):
        column = _find_column(profile, text, aliases)
        if not column:
            return PlannerResult(assistant_response="Which column should I use to split the table?", clarification_question="The split column is unclear.", confidence=0.85)
        calls.append(ToolCall(tool="split_sheet_by_column", args={"column": column}, requires_confirmation=True))
        needs_confirmation = True

    if any(word in text for word in ["urutkan", "sort", "sorting"]):
        column = _find_column(profile, text, aliases)
        if not column:
            return PlannerResult(assistant_response="Which column should I sort by?", clarification_question="The sort column is unclear.", confidence=0.85)
        descending_terms = ["terbesar", "descending", "desc", "menurun", "tertinggi", "besar ke kecil"]
        calls.append(ToolCall(tool="sort_rows", args={"columns": [column], "ascending": not any(term in text for term in descending_terms)}))

    if "duplicate" in text or "duplikat" in text:
        if "hapus" in text or "remove" in text:
            calls.append(ToolCall(tool="remove_duplicate_rows", args={}, requires_confirmation=True))
            needs_confirmation = True
        else:
            calls.append(ToolCall(tool="flag_duplicate_rows", args={}))

    if "rapikan nama kolom" in text or "standard" in text:
        calls.append(ToolCall(tool="standardize_column_names", args={}))
    if "whitespace" in text or "spasi" in text:
        calls.append(ToolCall(tool="trim_whitespace", args={}))
    if "tanggal" in text or "date" in text:
        columns = profile.date_like_columns or ([column] if (column := _find_column(profile, text, aliases)) else [])
        if columns:
            calls.append(ToolCall(tool="parse_date_columns", args={"columns": columns, "date_format": "%Y-%m-%d"}))
    if "numeric" in text or "angka" in text or "gaji" in text or "sales" in text:
        columns = profile.suspicious_numeric_text_columns or ([column] if (column := _find_column(profile, text, aliases)) else [])
        if columns:
            calls.append(ToolCall(tool="convert_numeric_columns", args={"columns": columns}))
    if "missing" in text or "kosong" in text:
        if "jangan isi" in text or "cukup flag" in text or "hanya flag" in text:
            calls.append(ToolCall(tool="flag_missing_values", args={}))
        elif "isi" in text or "fill" in text:
            calls.append(ToolCall(tool="fill_missing_values", args={"strategy": "auto"}, requires_confirmation=True))
            needs_confirmation = True

    if "summary" in text or "ringkasan" in text or "total" in text:
        group_col = _find_column(profile, text, aliases) or _first_existing(profile, ["region", "divisi", "department", "status"])
        value_col = _find_column(profile, "sales", aliases) or _find_column(profile, "gaji", aliases)
        if group_col:
            calls.append(ToolCall(tool="create_group_summary", args={"group_by": [group_col], "value_column": value_col, "agg": "sum" if value_col else "count"}))
    if "pivot" in text:
        index = _find_column(profile, text, aliases) or _first_existing(profile, profile.categorical_columns)
        value = _find_column(profile, "sales", aliases) or _find_column(profile, "gaji", aliases)
        if index:
            calls.append(ToolCall(tool="create_pivot_table", args={"index": index, "values": value, "aggfunc": "sum" if value else "count"}))
    if "flagged issue" in text or "flag masalah" in text or "sheet flagged" in text:
        calls.append(ToolCall(tool="create_flagged_issues_sheet", args={}))
    if "management" in text or "manajemen" in text or "report" in text:
        calls.append(ToolCall(tool="create_management_report", args={}))
    if "api" in text or "enrich" in text or "negara" in text or "country" in text:
        calls.append(ToolCall(tool="enrich_with_external_api", args={}))
    if "undo" in text or "batalkan" in text:
        calls.append(ToolCall(tool="undo_last_operation", args={}))
    if "export" in text or "download" in text or "workbook" in text:
        calls.append(ToolCall(tool="export_workbook", args={}))

    if not calls:
        return PlannerResult(assistant_response=_answer_profile_question(text, profile), confidence=0.75)

    response = "I prepared this action plan:\n" + "\n".join(f"- {call.tool}" for call in calls)
    if needs_confirmation:
        response += "\n\nSome actions require confirmation before I run them."
    return PlannerResult(assistant_response=response, tool_calls=calls, needs_confirmation=needs_confirmation, confidence=0.85)


def plan_with_provider(user_message: str, profile: AgentDataProfile | None, operation_history: list[str], provider_config: ProviderConfig | None = None) -> PlannerResult:
    if provider_config is None or provider_config.provider == "mock" or not provider_config.api_key:
        return fallback_plan(user_message, profile, operation_history)
    provider = create_provider(provider_config)
    user_payload = {
        "user_message": user_message,
        "data_profile": profile.model_dump() if profile else None,
        "available_tools": available_tools(),
        "operation_history": operation_history[-20:],
    }
    try:
        raw = provider.generate(SYSTEM_PROMPT, json.dumps(user_payload, default=str))
        parsed = PlannerResult.model_validate_json(raw)
        # Validate only tool names here; executor validates schemas.
        allowed = {tool["name"] for tool in available_tools()}
        if any(call.tool not in allowed for call in parsed.tool_calls):
            return PlannerResult(assistant_response="I cannot run actions outside the safe whitelist. Please choose a supported spreadsheet action.", clarification_question="The requested action is not available in the whitelist.", confidence=0.2)
        validated_calls = []
        needs_confirmation = bool(parsed.needs_confirmation)
        for call in parsed.tool_calls:
            spec = get_tool(call.tool)
            validated_calls.append(ToolCall(tool=call.tool, args=call.args, requires_confirmation=spec.requires_confirmation))
            if spec.requires_confirmation:
                needs_confirmation = True
        parsed.tool_calls = validated_calls
        parsed.needs_confirmation = needs_confirmation
        return parsed
    except (ValueError, ValidationError, json.JSONDecodeError):
        return fallback_plan(user_message, profile, operation_history)
