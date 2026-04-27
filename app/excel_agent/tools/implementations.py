from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from app.excel_agent.api_client import enrich_dataframe
from app.excel_agent.exporter import export_agent_workbook
from app.excel_agent.profiler import profile_dataframe
from app.excel_agent.schemas import ToolExecutionResult
from app.excel_agent.tools.registry import (
    AnalyzeWorkbookArgs,
    AnswerDataQuestionArgs,
    ColumnsArgs,
    EnrichApiArgs,
    ExportWorkbookArgs,
    FillMissingArgs,
    GroupSummaryArgs,
    HighlightColumnArgs,
    HighlightRowsConditionArgs,
    NormalizeTextArgs,
    NumericArgs,
    ParseDateArgs,
    PivotTableArgs,
    SplitSheetArgs,
    SortRowsArgs,
    ToolContext,
    ToolSpec,
    register_tool,
)


def _normalize_column(name: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower()).strip("_")


def _resolve_column(df: pd.DataFrame, column: str) -> str:
    normalized = _normalize_column(column)
    for col in df.columns:
        if str(col) == column or _normalize_column(str(col)) == normalized:
            return str(col)
    raise ValueError(f"Column not found: {column}")


def _snapshot(ctx: ToolContext) -> None:
    ctx.snapshots.append(ctx.working_df.copy())


def analyze_workbook(ctx: ToolContext, args: AnalyzeWorkbookArgs) -> ToolExecutionResult:
    profile = ctx.data_profile
    if profile is None:
        profile = profile_dataframe(ctx.working_df, type("Context", (), {"file_name": "session", "file_type": "dataframe", "sheet_names": [], "selected_sheet": None})())
        ctx.data_profile = profile
    return ToolExecutionResult(success=True, message="Workbook analyzed.", artifacts={"profile": profile.model_dump() if hasattr(profile, "model_dump") else {}})


def answer_data_question(ctx: ToolContext, args: AnswerDataQuestionArgs) -> ToolExecutionResult:
    q = args.question.lower()
    profile = ctx.data_profile
    if profile is None:
        return ToolExecutionResult(success=True, message="Upload file dulu agar saya bisa menjawab berdasarkan data.")
    if "row" in q or "baris" in q:
        return ToolExecutionResult(success=True, message=f"Data memiliki {profile.total_rows} baris dan {profile.total_columns} kolom.")
    if "missing" in q or "kosong" in q:
        total = sum(profile.missing_values.values())
        return ToolExecutionResult(success=True, message=f"Saya menemukan {total} missing values. Kolom terdampak: {profile.missing_values}.")
    if "insight" in q or "bisa diperbaiki" in q or "analisa" in q:
        issues = profile.detected_issues or ["Tidak ada masalah besar yang terdeteksi dari sample/profile."]
        actions = ", ".join(profile.recommended_actions)
        return ToolExecutionResult(success=True, message=f"Insight utama: {'; '.join(issues)}. Rekomendasi tool: {actions}.")
    return ToolExecutionResult(success=True, message=f"Kolom tersedia: {', '.join(profile.column_names)}. Tanyakan missing values, duplicate, summary, atau insight utama.")


def standardize_column_names(ctx: ToolContext, args: ColumnsArgs) -> ToolExecutionResult:
    _snapshot(ctx)
    ctx.working_df.columns = [_normalize_column(col) for col in ctx.working_df.columns]
    return ToolExecutionResult(success=True, message="Column names standardized.", changed=True)


def trim_whitespace(ctx: ToolContext, args: ColumnsArgs) -> ToolExecutionResult:
    _snapshot(ctx)
    cols = args.columns or [str(col) for col in ctx.working_df.columns if ctx.working_df[col].dtype == "object" or str(ctx.working_df[col].dtype).startswith("str")]
    for col in cols:
        resolved = _resolve_column(ctx.working_df, col)
        ctx.working_df[resolved] = ctx.working_df[resolved].map(lambda value: value.strip() if isinstance(value, str) else value)
    return ToolExecutionResult(success=True, message=f"Whitespace trimmed in {len(cols)} columns.", changed=True)


def remove_duplicate_rows(ctx: ToolContext, args: AnalyzeWorkbookArgs) -> ToolExecutionResult:
    _snapshot(ctx)
    before = len(ctx.working_df)
    ctx.working_df = ctx.working_df.drop_duplicates().reset_index(drop=True)
    return ToolExecutionResult(success=True, message=f"Removed {before - len(ctx.working_df)} duplicate rows.", changed=True)


def flag_duplicate_rows(ctx: ToolContext, args: AnalyzeWorkbookArgs) -> ToolExecutionResult:
    duplicate_rows = ctx.working_df[ctx.working_df.duplicated(keep=False)].copy()
    duplicate_rows["issue_type"] = "duplicate_row"
    ctx.artifacts["flagged_duplicates"] = duplicate_rows
    return ToolExecutionResult(success=True, message=f"Flagged {len(duplicate_rows)} duplicate rows.", artifacts={"rows": len(duplicate_rows)})


def parse_date_columns(ctx: ToolContext, args: ParseDateArgs) -> ToolExecutionResult:
    _snapshot(ctx)
    invalid = 0
    for col in args.columns:
        resolved = _resolve_column(ctx.working_df, col)
        original = ctx.working_df[resolved].copy()
        parsed = pd.to_datetime(original, errors="coerce")
        invalid += int((parsed.isna() & original.notna() & (original.astype(str).str.strip() != "")).sum())
        ctx.working_df[resolved] = parsed.dt.strftime(args.date_format or "%Y-%m-%d")
    return ToolExecutionResult(success=True, message=f"Parsed date columns. Invalid dates flagged: {invalid}.", changed=True)


def _parse_number(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip().lower().replace("$", "").replace(",", "")
    multiplier = 1
    if text.endswith("m"):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.endswith("k"):
        multiplier = 1_000
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def convert_numeric_columns(ctx: ToolContext, args: NumericArgs) -> ToolExecutionResult:
    _snapshot(ctx)
    invalid = 0
    for col in args.columns:
        resolved = _resolve_column(ctx.working_df, col)
        converted = ctx.working_df[resolved].map(_parse_number)
        invalid += int(converted.isna().sum() - ctx.working_df[resolved].isna().sum())
        ctx.working_df[resolved] = converted
    return ToolExecutionResult(success=True, message=f"Converted numeric columns. Invalid numeric values: {max(invalid, 0)}.", changed=True)


def fill_missing_values(ctx: ToolContext, args: FillMissingArgs) -> ToolExecutionResult:
    _snapshot(ctx)
    cols = args.columns or [str(col) for col in ctx.working_df.columns]
    filled = 0
    for col in cols:
        resolved = _resolve_column(ctx.working_df, col)
        mask = ctx.working_df[resolved].isna() | (ctx.working_df[resolved].astype(str).str.strip() == "")
        if not mask.any():
            continue
        if pd.api.types.is_numeric_dtype(ctx.working_df[resolved]):
            ctx.working_df.loc[mask, resolved] = ctx.working_df[resolved].median()
        else:
            ctx.working_df.loc[mask, resolved] = "Unknown"
        filled += int(mask.sum())
    return ToolExecutionResult(success=True, message=f"Filled {filled} missing values.", changed=True)


def flag_missing_values(ctx: ToolContext, args: ColumnsArgs) -> ToolExecutionResult:
    cols = args.columns or [str(col) for col in ctx.working_df.columns]
    rows = []
    for col in cols:
        resolved = _resolve_column(ctx.working_df, col)
        mask = ctx.working_df[resolved].isna() | (ctx.working_df[resolved].astype(str).str.strip() == "")
        for idx in ctx.working_df.index[mask]:
            rows.append({"row_index": int(idx), "column": resolved, "issue_type": "missing_value", "original_value": "", "suggested_fix": "Review or fill value"})
    ctx.artifacts["flagged_missing"] = pd.DataFrame(rows)
    return ToolExecutionResult(success=True, message=f"Flagged {len(rows)} missing values.", artifacts={"rows": len(rows)})


def normalize_text_casing(ctx: ToolContext, args: NormalizeTextArgs) -> ToolExecutionResult:
    _snapshot(ctx)
    cols = args.columns or [str(col) for col in ctx.working_df.columns if ctx.working_df[col].dtype == "object" or str(ctx.working_df[col].dtype).startswith("str")]
    for col in cols:
        resolved = _resolve_column(ctx.working_df, col)
        if args.case == "title":
            ctx.working_df[resolved] = ctx.working_df[resolved].map(lambda value: value.title() if isinstance(value, str) else value)
        elif args.case == "upper":
            ctx.working_df[resolved] = ctx.working_df[resolved].map(lambda value: value.upper() if isinstance(value, str) else value)
        else:
            ctx.working_df[resolved] = ctx.working_df[resolved].map(lambda value: value.lower() if isinstance(value, str) else value)
    return ToolExecutionResult(success=True, message=f"Text casing normalized for {len(cols)} columns.", changed=True)


def highlight_column(ctx: ToolContext, args: HighlightColumnArgs) -> ToolExecutionResult:
    resolved = _resolve_column(ctx.working_df, args.column)
    ctx.formatting.append({"type": "column", "column": resolved, "color": args.color})
    return ToolExecutionResult(success=True, message=f"Column `{resolved}` will be highlighted {args.color}.")


def highlight_rows_by_condition(ctx: ToolContext, args: HighlightRowsConditionArgs) -> ToolExecutionResult:
    resolved = _resolve_column(ctx.working_df, args.column)
    ctx.formatting.append({"type": "row_condition", "column": resolved, "equals": args.equals, "color": args.color})
    return ToolExecutionResult(success=True, message=f"Rows where `{resolved}` equals `{args.equals}` will be highlighted {args.color}.")


def split_sheet_by_column(ctx: ToolContext, args: SplitSheetArgs) -> ToolExecutionResult:
    resolved = _resolve_column(ctx.working_df, args.column)
    split_sheets = {}
    for value, frame in ctx.working_df.groupby(resolved, dropna=False):
        safe = re.sub(r"[^0-9a-zA-Z]+", "_", str(value or "blank")).strip("_")[:25] or "blank"
        split_sheets[f"{resolved}_{safe}"] = frame.reset_index(drop=True)
    ctx.artifacts["split_sheets"] = split_sheets
    return ToolExecutionResult(success=True, message=f"Created {len(split_sheets)} split sheets by `{resolved}`.", artifacts={"sheets": list(split_sheets)})


def sort_rows(ctx: ToolContext, args: SortRowsArgs) -> ToolExecutionResult:
    _snapshot(ctx)
    selected = [_resolve_column(ctx.working_df, col) for col in args.columns]
    ctx.working_df = ctx.working_df.sort_values(by=selected, ascending=args.ascending, kind="mergesort").reset_index(drop=True)
    direction = "ascending" if args.ascending else "descending"
    return ToolExecutionResult(success=True, message=f"Sorted rows by {', '.join(selected)} ({direction}).", changed=True)


def create_group_summary(ctx: ToolContext, args: GroupSummaryArgs) -> ToolExecutionResult:
    group_cols = [_resolve_column(ctx.working_df, col) for col in args.group_by]
    value_col = _resolve_column(ctx.working_df, args.value_column) if args.value_column else None
    if value_col and pd.api.types.is_numeric_dtype(ctx.working_df[value_col]):
        summary = ctx.working_df.groupby(group_cols, dropna=False)[value_col].agg(args.agg).reset_index()
    else:
        summary = ctx.working_df.groupby(group_cols, dropna=False).size().reset_index(name="count")
    ctx.artifacts["group_summary"] = summary
    return ToolExecutionResult(success=True, message="Group summary created.", artifacts={"rows": len(summary)})


def create_pivot_table(ctx: ToolContext, args: PivotTableArgs) -> ToolExecutionResult:
    index = _resolve_column(ctx.working_df, args.index)
    columns = _resolve_column(ctx.working_df, args.columns) if args.columns else None
    values = _resolve_column(ctx.working_df, args.values) if args.values else None
    pivot = pd.pivot_table(ctx.working_df, index=index, columns=columns, values=values, aggfunc=args.aggfunc, fill_value=0)
    ctx.artifacts["pivot_table"] = pivot.reset_index()
    return ToolExecutionResult(success=True, message="Pivot table created.", artifacts={"rows": len(ctx.artifacts["pivot_table"])})


def create_flagged_issues_sheet(ctx: ToolContext, args: AnalyzeWorkbookArgs) -> ToolExecutionResult:
    rows = []
    for col in ctx.working_df.columns:
        mask = ctx.working_df[col].isna() | (ctx.working_df[col].astype(str).str.strip() == "")
        for idx in ctx.working_df.index[mask]:
            rows.append({"row_index": int(idx), "column": str(col), "issue_type": "missing_value", "original_value": "", "suggested_fix": "Review value"})
    duplicate = ctx.working_df[ctx.working_df.duplicated(keep=False)]
    for idx in duplicate.index:
        rows.append({"row_index": int(idx), "column": "all_columns", "issue_type": "duplicate_row", "original_value": "duplicate", "suggested_fix": "Review duplicate"})
    ctx.artifacts["flagged_issues"] = pd.DataFrame(rows)
    return ToolExecutionResult(success=True, message=f"Flagged issues sheet created with {len(rows)} rows.")


def create_management_report(ctx: ToolContext, args: AnalyzeWorkbookArgs) -> ToolExecutionResult:
    profile = ctx.data_profile
    rows = [
        {"metric": "total_rows", "value": len(ctx.working_df)},
        {"metric": "total_columns", "value": len(ctx.working_df.columns)},
        {"metric": "missing_values", "value": int(ctx.working_df.isna().sum().sum())},
        {"metric": "duplicate_rows", "value": int(ctx.working_df.duplicated().sum())},
        {"metric": "recommended_actions", "value": ", ".join(profile.recommended_actions if profile else [])},
    ]
    ctx.artifacts["management_report"] = pd.DataFrame(rows)
    return ToolExecutionResult(success=True, message="Management report created.", artifacts={"rows": len(rows)})


def enrich_with_external_api(ctx: ToolContext, args: EnrichApiArgs) -> ToolExecutionResult:
    enrichment = enrich_dataframe(ctx.working_df)
    ctx.artifacts["api_enrichment"] = enrichment
    return ToolExecutionResult(success=True, message=f"API enrichment completed with {len(enrichment)} rows.", artifacts={"rows": len(enrichment)})


def export_workbook(ctx: ToolContext, args: ExportWorkbookArgs) -> ToolExecutionResult:
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (args.output_name or "excel_agent_output.xlsx")
    export_agent_workbook(output_path, ctx)
    ctx.latest_output_path = str(output_path)
    return ToolExecutionResult(success=True, message=f"Workbook exported to {output_path}.", artifacts={"output_path": str(output_path)})


def undo_last_operation(ctx: ToolContext, args: AnalyzeWorkbookArgs) -> ToolExecutionResult:
    if not ctx.snapshots:
        return ToolExecutionResult(success=False, message="No snapshot available to undo.")
    ctx.working_df = ctx.snapshots.pop()
    return ToolExecutionResult(success=True, message="Last dataframe operation undone.", changed=True)


def register_default_tools() -> None:
    specs = [
        ToolSpec("analyze_workbook", "Create workbook profile and recommendations.", AnalyzeWorkbookArgs, False, analyze_workbook),
        ToolSpec("answer_data_question", "Answer a question from profile/statistics/sample data.", AnswerDataQuestionArgs, False, answer_data_question),
        ToolSpec("standardize_column_names", "Standardize columns to snake_case.", ColumnsArgs, False, standardize_column_names),
        ToolSpec("trim_whitespace", "Trim whitespace from text cells.", ColumnsArgs, False, trim_whitespace),
        ToolSpec("remove_duplicate_rows", "Remove duplicate rows.", AnalyzeWorkbookArgs, True, remove_duplicate_rows),
        ToolSpec("flag_duplicate_rows", "Flag duplicate rows without deleting.", AnalyzeWorkbookArgs, False, flag_duplicate_rows),
        ToolSpec("parse_date_columns", "Parse selected date columns.", ParseDateArgs, False, parse_date_columns),
        ToolSpec("convert_numeric_columns", "Convert numeric-looking text columns.", NumericArgs, False, convert_numeric_columns),
        ToolSpec("fill_missing_values", "Fill missing values with a selected strategy.", FillMissingArgs, True, fill_missing_values),
        ToolSpec("flag_missing_values", "Flag missing values without editing data.", ColumnsArgs, False, flag_missing_values),
        ToolSpec("normalize_text_casing", "Normalize text casing.", NormalizeTextArgs, False, normalize_text_casing),
        ToolSpec("highlight_column", "Highlight a column in the exported workbook.", HighlightColumnArgs, False, highlight_column),
        ToolSpec("highlight_rows_by_condition", "Highlight rows matching a simple equality condition.", HighlightRowsConditionArgs, False, highlight_rows_by_condition),
        ToolSpec("split_sheet_by_column", "Create separate sheets by unique values in a column.", SplitSheetArgs, True, split_sheet_by_column),
        ToolSpec("sort_rows", "Sort rows by one or more columns.", SortRowsArgs, False, sort_rows),
        ToolSpec("create_group_summary", "Create groupby summary.", GroupSummaryArgs, False, create_group_summary),
        ToolSpec("create_pivot_table", "Create a simple pivot table.", PivotTableArgs, False, create_pivot_table),
        ToolSpec("create_flagged_issues_sheet", "Create flagged issues sheet.", AnalyzeWorkbookArgs, False, create_flagged_issues_sheet),
        ToolSpec("create_management_report", "Create management report.", AnalyzeWorkbookArgs, False, create_management_report),
        ToolSpec("enrich_with_external_api", "Run API enrichment with fallback.", EnrichApiArgs, False, enrich_with_external_api),
        ToolSpec("export_workbook", "Export workbook with styling and artifacts.", ExportWorkbookArgs, False, export_workbook),
        ToolSpec("undo_last_operation", "Rollback to previous dataframe snapshot.", AnalyzeWorkbookArgs, False, undo_last_operation),
    ]
    for spec in specs:
        register_tool(spec)


register_default_tools()
