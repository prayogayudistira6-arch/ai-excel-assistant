from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.models import CleaningPlan, CleaningResult, DataProfile
from app.processing import cleaners
from app.processing.api_client import enrich_dataframe
from app.processing.excel_exporter import export_cleaning_workbook
from app.processing.profiler import build_inefficiency_report, build_management_view, data_profile_frame
from app.processing.validator import FLAGGED_COLUMNS


ALLOWED_CLEANING_ACTIONS = {
    "standardize_column_names",
    "trim_whitespace",
    "remove_duplicate_rows",
    "parse_date_columns",
    "convert_numeric_columns",
    "fill_missing_values",
    "normalize_text_casing",
    "flag_invalid_rows",
    "sort_rows",
    "enrich_with_api",
    "create_summary_sheet",
    "create_management_view",
    "create_inefficiency_report",
    "style_excel_output",
}


def _standardize_name(column: str) -> str:
    import re

    return re.sub(r"[^0-9a-zA-Z]+", "_", str(column).strip().lower()).strip("_")


def _resolve_columns(df: pd.DataFrame, columns: list[str] | None) -> list[str]:
    if not columns:
        return []
    existing = set(df.columns)
    standardized_lookup = {_standardize_name(col): col for col in df.columns}
    resolved: list[str] = []
    for col in columns:
        if col in existing:
            resolved.append(col)
            continue
        standardized = _standardize_name(col)
        if standardized in existing:
            resolved.append(standardized)
        elif standardized in standardized_lookup:
            resolved.append(standardized_lookup[standardized])
    return resolved


@dataclass
class CleaningExecution:
    original_df: pd.DataFrame
    cleaned_df: pd.DataFrame
    flagged_issues: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=FLAGGED_COLUMNS))
    summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    inefficiency_report: pd.DataFrame = field(default_factory=pd.DataFrame)
    management_view: pd.DataFrame = field(default_factory=pd.DataFrame)
    api_enrichment: pd.DataFrame = field(default_factory=pd.DataFrame)
    change_log: list[str] = field(default_factory=list)
    actions_executed: list[str] = field(default_factory=list)


def _append_issues(current: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    if new.empty:
        return current
    return pd.concat([current, new], ignore_index=True)


def execute_cleaning_plan(
    df: pd.DataFrame,
    profile: DataProfile,
    plan: CleaningPlan,
    output_path: str | Path,
) -> CleaningResult:
    execution = CleaningExecution(original_df=df.copy(), cleaned_df=df.copy())
    original_duplicate_count = int(df.duplicated().sum())

    for action in plan.actions:
        if not action.enabled:
            continue
        name = action.action_name
        if name not in ALLOWED_CLEANING_ACTIONS:
            raise ValueError(f"Unsupported cleaning action: {name}")
        if name == "style_excel_output":
            continue

        before_rows = len(execution.cleaned_df)
        issues = pd.DataFrame(columns=FLAGGED_COLUMNS)
        message = ""
        columns = _resolve_columns(execution.cleaned_df, action.columns)

        if name == "standardize_column_names":
            execution.cleaned_df, issues, message = cleaners.standardize_column_names(execution.cleaned_df)
        elif name == "trim_whitespace":
            execution.cleaned_df, issues, message = cleaners.trim_whitespace(execution.cleaned_df, columns)
        elif name == "remove_duplicate_rows":
            execution.cleaned_df, issues, message = cleaners.remove_duplicate_rows(execution.cleaned_df)
        elif name == "parse_date_columns":
            execution.cleaned_df, issues, message = cleaners.parse_date_columns(execution.cleaned_df, columns or _resolve_columns(execution.cleaned_df, profile.suspected_date_columns))
        elif name == "convert_numeric_columns":
            execution.cleaned_df, issues, message = cleaners.convert_numeric_columns(execution.cleaned_df, columns or _resolve_columns(execution.cleaned_df, profile.suspected_numeric_columns))
        elif name == "fill_missing_values":
            execution.cleaned_df, issues, message = cleaners.fill_missing_values(execution.cleaned_df, columns)
        elif name == "normalize_text_casing":
            execution.cleaned_df, issues, message = cleaners.normalize_text_casing(
                execution.cleaned_df,
                columns,
                case=str(action.parameters.get("case", "lower")),
            )
        elif name == "flag_invalid_rows":
            execution.cleaned_df, issues, message = cleaners.flag_invalid_rows(execution.cleaned_df, profile.suspected_date_columns)
        elif name == "sort_rows":
            execution.cleaned_df, issues, message = cleaners.sort_rows(
                execution.cleaned_df,
                columns,
                ascending=bool(action.parameters.get("ascending", True)),
            )
        elif name == "enrich_with_api":
            execution.api_enrichment = enrich_dataframe(execution.cleaned_df)
            message = f"Created API enrichment with {len(execution.api_enrichment)} rows"
        elif name == "create_management_view":
            execution.management_view = build_management_view(profile, len(execution.cleaned_df), execution.actions_executed)
            message = "Created management view"
        elif name == "create_inefficiency_report":
            execution.inefficiency_report = build_inefficiency_report(profile)
            message = "Created inefficiency report"
        elif name == "create_summary_sheet":
            execution.summary = cleaners.create_summary_sheet(execution.cleaned_df)
            message = "Created summary sheet"

        execution.flagged_issues = _append_issues(execution.flagged_issues, issues)
        if name in {"remove_duplicate_rows"}:
            removed = before_rows - len(execution.cleaned_df)
            if removed > 0 and not message.startswith("Removed"):
                message = f"Removed {removed} duplicate rows"
        execution.change_log.append(message)
        execution.actions_executed.append(name)

    if execution.summary.empty:
        execution.summary = cleaners.create_summary_sheet(execution.cleaned_df)
    if execution.inefficiency_report.empty:
        execution.inefficiency_report = build_inefficiency_report(profile)
    if execution.management_view.empty:
        execution.management_view = build_management_view(profile, len(execution.cleaned_df), execution.actions_executed)
    if execution.api_enrichment.empty:
        execution.api_enrichment = enrich_dataframe(execution.cleaned_df)

    removed_duplicates = max(original_duplicate_count, len(df) - len(execution.cleaned_df))
    invalid_dates = int((execution.flagged_issues["issue_type"] == "invalid_date").sum()) if not execution.flagged_issues.empty else 0
    numeric_issues = int((execution.flagged_issues["issue_type"] == "invalid_numeric").sum()) if not execution.flagged_issues.empty else 0
    total_missing = int(sum(profile.missing_values.values()))

    export_cleaning_workbook(
        output_path=output_path,
        original_df=df,
        cleaned_df=execution.cleaned_df,
        flagged_issues=execution.flagged_issues,
        summary=execution.summary,
        data_profile=data_profile_frame(profile),
        inefficiency_report=execution.inefficiency_report,
        ai_recommendations=_ai_recommendations_frame(plan),
        cleaning_plan=pd.DataFrame([action.model_dump() for action in plan.actions]),
        api_enrichment=execution.api_enrichment,
        management_view=execution.management_view,
        change_log=execution.change_log,
        metrics={
            "total rows before": len(df),
            "total rows after": len(execution.cleaned_df),
            "total columns": len(execution.cleaned_df.columns),
            "missing values found": total_missing,
            "duplicates removed": removed_duplicates,
            "invalid dates found": invalid_dates,
            "numeric conversion issues": numeric_issues,
            "actions executed": ", ".join(execution.actions_executed),
        },
    )

    return CleaningResult(
        original_rows=len(df),
        cleaned_rows=len(execution.cleaned_df),
        removed_duplicates=removed_duplicates,
        total_missing_values=total_missing,
        flagged_issues_count=len(execution.flagged_issues),
        output_path=str(output_path),
        change_log=execution.change_log,
        invalid_dates_found=invalid_dates,
        numeric_conversion_issues=numeric_issues,
        actions_executed=execution.actions_executed,
    )


def _ai_recommendations_frame(plan: CleaningPlan) -> pd.DataFrame:
    risky = {"remove_duplicate_rows", "fill_missing_values"}
    high = {"standardize_column_names", "trim_whitespace", "parse_date_columns", "convert_numeric_columns", "flag_invalid_rows", "create_inefficiency_report"}
    rows = []
    for action in plan.actions:
        priority = "High" if action.action_name in high else "Medium"
        if action.action_name in risky:
            priority = "High"
        if action.action_name in {"create_summary_sheet", "create_management_view", "enrich_with_api", "sort_rows"}:
            priority = "Medium"
        rows.append(
            {
                "recommendation": action.action_name,
                "reason": action.reason,
                "priority": priority,
                "related_action": action.action_name,
            }
        )
    return pd.DataFrame(rows)
