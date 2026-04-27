from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.excel_agent.schemas import AgentDataProfile, WorkbookContext


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def read_workbook(path: str | Path, sheet_name: str | int | None = None) -> tuple[pd.DataFrame, WorkbookContext]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(file_path, on_bad_lines="warn")
        return df, WorkbookContext(file_name=file_path.name, file_type="csv")
    if suffix in {".xlsx", ".xls"}:
        excel = pd.ExcelFile(file_path)
        selected = sheet_name if sheet_name is not None else excel.sheet_names[0]
        df = pd.read_excel(file_path, sheet_name=selected)
        return df, WorkbookContext(file_name=file_path.name, file_type=suffix.lstrip("."), sheet_names=excel.sheet_names, selected_sheet=str(selected))
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


def _numeric_text_ratio(series: pd.Series) -> float:
    values = series.dropna().astype(str).str.strip()
    if values.empty:
        return 0.0
    cleaned = values.str.replace(r"[\$,]", "", regex=True).str.replace(r"(?i)(m|k)$", "", regex=True)
    return float(pd.to_numeric(cleaned, errors="coerce").notna().mean())


def profile_dataframe(df: pd.DataFrame, context: WorkbookContext) -> AgentDataProfile:
    numeric_columns: list[str] = []
    text_columns: list[str] = []
    date_like_columns: list[str] = []
    categorical_columns: list[str] = []
    potential_id_columns: list[str] = []
    suspicious_numeric_text_columns: list[str] = []
    inconsistent_casing: dict[str, int] = {}
    whitespace_issues: dict[str, int] = {}
    invalid_date_candidates: dict[str, int] = {}
    unique_value_count: dict[str, int] = {}
    numeric_stats: dict[str, dict[str, float | None]] = {}
    issues: list[str] = []
    actions: list[str] = ["analyze_workbook", "create_management_report", "export_workbook"]

    for col in df.columns:
        name = str(col)
        lower = name.lower()
        series = df[col]
        unique_value_count[name] = int(series.nunique(dropna=True))
        if pd.api.types.is_numeric_dtype(series):
            numeric_columns.append(name)
            numeric_stats[name] = {
                "min": float(series.min()) if series.notna().any() else None,
                "max": float(series.max()) if series.notna().any() else None,
                "mean": float(series.mean()) if series.notna().any() else None,
            }
        else:
            text_columns.append(name)
            ratio = _numeric_text_ratio(series)
            if ratio >= 0.6:
                suspicious_numeric_text_columns.append(name)
                actions.append("convert_numeric_columns")
        if "date" in lower or lower.endswith("_at") or "tanggal" in lower:
            date_like_columns.append(name)
            parsed = pd.to_datetime(series, errors="coerce")
            invalid = int((parsed.isna() & series.notna() & (series.astype(str).str.strip() != "")).sum())
            if invalid:
                invalid_date_candidates[name] = invalid
                actions.append("parse_date_columns")
        if lower in {"id", "record_id"} or lower.endswith("_id") or lower.endswith(" id"):
            potential_id_columns.append(name)
        if series.dtype == "object" or str(series.dtype).startswith("str"):
            values = series.dropna().astype(str)
            if not values.empty:
                normalized = values.str.strip().str.lower()
                casing = sum(int(group.nunique() > 1) for _, group in values.groupby(normalized))
                if casing:
                    inconsistent_casing[name] = casing
                    actions.append("normalize_text_casing")
                whitespace = int((values != values.str.strip()).sum())
                if whitespace:
                    whitespace_issues[name] = whitespace
                    actions.append("trim_whitespace")
            if unique_value_count[name] <= max(20, int(len(df) * 0.25)):
                categorical_columns.append(name)

    missing_values = {str(col): int(count) for col, count in df.isna().sum().items()}
    duplicate_count = int(df.duplicated().sum())
    if sum(missing_values.values()):
        issues.append(f"{sum(missing_values.values())} missing values found")
        actions.extend(["flag_missing_values", "fill_missing_values"])
    if duplicate_count:
        issues.append(f"{duplicate_count} duplicate rows found")
        actions.extend(["flag_duplicate_rows", "remove_duplicate_rows"])
    if invalid_date_candidates:
        issues.append("Invalid date values detected")
    if suspicious_numeric_text_columns:
        issues.append("Numeric-looking text columns detected")
    if whitespace_issues:
        issues.append("Whitespace issues detected")
    if inconsistent_casing:
        issues.append("Inconsistent casing detected")

    sample_rows = [{str(col): _json_value(value) for col, value in row.items()} for row in df.head(5).to_dict(orient="records")]
    return AgentDataProfile(
        file_name=context.file_name,
        file_type=context.file_type,
        sheet_names=context.sheet_names,
        selected_sheet=context.selected_sheet,
        total_rows=int(len(df)),
        total_columns=int(len(df.columns)),
        column_names=[str(col) for col in df.columns],
        dtypes={str(col): str(dtype) for col, dtype in df.dtypes.items()},
        missing_values=missing_values,
        duplicate_count=duplicate_count,
        sample_rows=sample_rows,
        numeric_columns=numeric_columns,
        text_columns=text_columns,
        date_like_columns=date_like_columns,
        categorical_columns=categorical_columns,
        potential_id_columns=potential_id_columns,
        suspicious_numeric_text_columns=suspicious_numeric_text_columns,
        inconsistent_casing=inconsistent_casing,
        whitespace_issues=whitespace_issues,
        invalid_date_candidates=invalid_date_candidates,
        unique_value_count=unique_value_count,
        basic_numeric_stats=numeric_stats,
        detected_issues=issues,
        recommended_actions=sorted(set(actions)),
    )


def profile_workbook(path: str | Path, sheet_name: str | int | None = None) -> tuple[pd.DataFrame, WorkbookContext, AgentDataProfile]:
    df, context = read_workbook(path, sheet_name)
    return df, context, profile_dataframe(df, context)
