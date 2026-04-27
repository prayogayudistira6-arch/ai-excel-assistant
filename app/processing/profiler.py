from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.models import DataProfile, DetectedIssue


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _looks_numeric(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    values = series.dropna().astype(str).str.strip()
    if values.empty:
        return False
    cleaned = values.str.replace(r"[\$,]", "", regex=True).str.replace(r"(?i)(m|k)$", "", regex=True)
    parsed = pd.to_numeric(cleaned, errors="coerce")
    return parsed.notna().mean() >= 0.6


def _invalid_date_count(series: pd.Series) -> int:
    parsed = pd.to_datetime(series, errors="coerce")
    return int((parsed.isna() & series.notna() & (series.astype(str).str.strip() != "")).sum())


def _casing_inconsistency_count(series: pd.Series) -> int:
    values = series.dropna().astype(str).str.strip()
    if values.empty:
        return 0
    normalized = values.str.lower()
    count = 0
    for _, group in values.groupby(normalized):
        if group.nunique() > 1:
            count += int(group.nunique())
    return count


def _whitespace_issue_count(series: pd.Series) -> int:
    if not (series.dtype == "object" or str(series.dtype).startswith("str")):
        return 0
    values = series.dropna().astype(str)
    return int((values != values.str.strip()).sum())


def read_uploaded_table(path: str | Path, sheet_name: str | int | None = None) -> tuple[pd.DataFrame, list[str], str | None]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file_path, on_bad_lines="warn"), [], None
    if suffix in {".xlsx", ".xls"}:
        excel = pd.ExcelFile(file_path)
        selected = sheet_name if sheet_name is not None else excel.sheet_names[0]
        return pd.read_excel(file_path, sheet_name=selected), excel.sheet_names, str(selected)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


def profile_dataframe(
    df: pd.DataFrame,
    file_name: str,
    file_type: str,
    sheet_names: list[str] | None = None,
    selected_sheet: str | None = None,
) -> DataProfile:
    dtypes = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
    missing_values = {str(col): int(count) for col, count in df.isna().sum().items()}
    suspected_date_columns: list[str] = []
    suspected_numeric_columns: list[str] = []
    suspected_categorical_columns: list[str] = []
    casing_inconsistencies: dict[str, int] = {}
    invalid_date_counts: dict[str, int] = {}
    whitespace_issues: dict[str, int] = {}
    possible_id_columns: list[str] = []
    possible_name_columns: list[str] = []
    detected_issues: list[str] = []

    for col in df.columns:
        col_name = str(col)
        lower = col_name.lower()
        series = df[col]
        if lower in {"id", "record_id"} or lower.endswith("_id") or lower.endswith(" id"):
            possible_id_columns.append(col_name)
        if "name" in lower or lower in {"owner", "assignee", "customer", "company"}:
            possible_name_columns.append(col_name)
        if "date" in lower or lower.endswith("_at"):
            suspected_date_columns.append(col_name)
            invalid_count = _invalid_date_count(series)
            if invalid_count:
                invalid_date_counts[col_name] = invalid_count
                detected_issues.append(f"{col_name} has {invalid_count} invalid date values")
        if _looks_numeric(series):
            suspected_numeric_columns.append(col_name)
        if series.dtype == "object" or str(series.dtype).startswith("str"):
            unique_ratio = series.nunique(dropna=True) / max(len(series), 1)
            if unique_ratio <= 0.5:
                suspected_categorical_columns.append(col_name)
            casing_count = _casing_inconsistency_count(series)
            if casing_count:
                casing_inconsistencies[col_name] = casing_count
            whitespace_count = _whitespace_issue_count(series)
            if whitespace_count:
                whitespace_issues[col_name] = whitespace_count

    total_missing = sum(missing_values.values())
    duplicate_count = int(df.duplicated().sum())
    if total_missing:
        detected_issues.append(f"{total_missing} missing values found")
    if duplicate_count:
        detected_issues.append(f"{duplicate_count} duplicate rows found")
    nonstandard_cols = [str(col) for col in df.columns if str(col).strip().lower().replace(" ", "_") != str(col)]
    if nonstandard_cols:
        detected_issues.append(f"{len(nonstandard_cols)} column names are not standardized")
    if casing_inconsistencies:
        detected_issues.append("String casing inconsistencies detected")
    if whitespace_issues:
        detected_issues.append("Whitespace issues detected")

    sample_rows = [
        {str(col): _json_value(value) for col, value in row.items()}
        for row in df.head(5).to_dict(orient="records")
    ]
    return DataProfile(
        file_name=file_name,
        file_type=file_type,
        sheet_names=sheet_names or [],
        selected_sheet=selected_sheet,
        rows=int(len(df)),
        columns=int(len(df.columns)),
        column_names=[str(col) for col in df.columns],
        dtypes=dtypes,
        missing_values=missing_values,
        duplicate_count=duplicate_count,
        sample_rows=sample_rows,
        suspected_date_columns=suspected_date_columns,
        suspected_numeric_columns=suspected_numeric_columns,
        suspected_categorical_columns=suspected_categorical_columns,
        detected_issues=detected_issues,
        casing_inconsistencies=casing_inconsistencies,
        invalid_date_counts=invalid_date_counts,
        whitespace_issues=whitespace_issues,
        possible_id_columns=possible_id_columns,
        possible_name_columns=possible_name_columns,
    )


def profile_file(path: str | Path, sheet_name: str | int | None = None) -> tuple[pd.DataFrame, DataProfile]:
    file_path = Path(path)
    df, sheet_names, selected_sheet = read_uploaded_table(file_path, sheet_name)
    profile = profile_dataframe(
        df,
        file_name=file_path.name,
        file_type=file_path.suffix.lower().lstrip("."),
        sheet_names=sheet_names,
        selected_sheet=selected_sheet,
    )
    return df, profile


def data_profile_frame(profile: DataProfile) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"metric": "file_name", "value": profile.file_name},
            {"metric": "file_type", "value": profile.file_type},
            {"metric": "selected_sheet", "value": profile.selected_sheet or ""},
            {"metric": "total_rows", "value": profile.rows},
            {"metric": "total_columns", "value": profile.columns},
            {"metric": "column_names", "value": ", ".join(profile.column_names)},
            {"metric": "possible_id_columns", "value": ", ".join(profile.possible_id_columns)},
            {"metric": "possible_name_columns", "value": ", ".join(profile.possible_name_columns)},
            {"metric": "possible_date_columns", "value": ", ".join(profile.suspected_date_columns)},
            {"metric": "possible_numeric_columns", "value": ", ".join(profile.suspected_numeric_columns)},
            {"metric": "possible_categorical_columns", "value": ", ".join(profile.suspected_categorical_columns)},
            {"metric": "duplicate_rows", "value": profile.duplicate_count},
            {"metric": "missing_values_total", "value": sum(profile.missing_values.values())},
            {"metric": "invalid_dates_total", "value": sum(profile.invalid_date_counts.values())},
            {"metric": "whitespace_issues_total", "value": sum(profile.whitespace_issues.values())},
        ]
    )


def build_inefficiency_report(profile: DataProfile) -> pd.DataFrame:
    issues: list[DetectedIssue] = []
    total_missing = sum(profile.missing_values.values())
    if total_missing:
        for col, count in profile.missing_values.items():
            if count:
                impact = "Missing owner may delay follow-up ownership" if col.lower() in {"owner", "assignee"} else "Missing values may require manual review before reporting"
                issues.append(DetectedIssue(issue_type="missing_values", affected_column=col, affected_rows_count=count, business_impact=impact, recommended_action="fill_missing_values or flag_invalid_rows", severity="High" if col.lower() in {"owner", "assignee"} else "Medium"))
    if profile.duplicate_count:
        issues.append(DetectedIssue(issue_type="duplicate_rows", affected_column=None, affected_rows_count=profile.duplicate_count, business_impact="Duplicate rows may cause double counting in reports", recommended_action="remove_duplicate_rows", severity="High"))
    for col, count in profile.invalid_date_counts.items():
        issues.append(DetectedIssue(issue_type="invalid_dates", affected_column=col, affected_rows_count=count, business_impact="Invalid dates may break timeline reporting", recommended_action="parse_date_columns", severity="High"))
    for col in profile.suspected_numeric_columns:
        if profile.dtypes.get(col, "").lower() in {"object", "str", "string"}:
            issues.append(DetectedIssue(issue_type="numeric_stored_as_text", affected_column=col, affected_rows_count=profile.rows, business_impact="Numeric fields stored as text may break financial calculations", recommended_action="convert_numeric_columns", severity="Medium"))
    for col, count in profile.casing_inconsistencies.items():
        issues.append(DetectedIssue(issue_type="inconsistent_casing", affected_column=col, affected_rows_count=count, business_impact="Inconsistent status values may make dashboards unreliable", recommended_action="normalize_text_casing", severity="Medium"))
    for col, count in profile.whitespace_issues.items():
        issues.append(DetectedIssue(issue_type="whitespace_issues", affected_column=col, affected_rows_count=count, business_impact="Extra whitespace may prevent matching and lookup workflows", recommended_action="trim_whitespace", severity="Low"))
    return pd.DataFrame([issue.model_dump() for issue in issues])


def build_management_view(profile: DataProfile, cleaned_rows: int | None = None, actions: list[str] | None = None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if profile.duplicate_count:
        rows.append({"insight": "Duplicate records may distort reporting accuracy", "severity": "High", "affected_area": "Reporting", "recommended_action": "remove_duplicate_rows", "expected_impact": "Prevent duplicate follow-ups"})
    if any(col.lower() in {"owner", "assignee"} and count for col, count in profile.missing_values.items()):
        rows.append({"insight": "Missing owner/assignee may cause accountability gaps", "severity": "High", "affected_area": "Operations ownership", "recommended_action": "fill_missing_values or assign owners", "expected_impact": "Improve accountability"})
    if profile.invalid_date_counts:
        rows.append({"insight": "Invalid dates may delay timeline tracking", "severity": "High", "affected_area": "Timeline reporting", "recommended_action": "parse_date_columns", "expected_impact": "Improve reporting reliability"})
    if profile.casing_inconsistencies:
        rows.append({"insight": "Inconsistent status values may make dashboards unreliable", "severity": "Medium", "affected_area": "Dashboard filters", "recommended_action": "normalize_text_casing", "expected_impact": "Reduce manual review time"})
    if profile.suspected_numeric_columns:
        rows.append({"insight": "Numeric fields stored as text may break calculations", "severity": "Medium", "affected_area": "Financial analysis", "recommended_action": "convert_numeric_columns", "expected_impact": "Improve reporting reliability"})
    rows.append({"insight": f"Workflow processed {profile.rows} records and can produce management-ready reports", "severity": "Low", "affected_area": "Spreadsheet operations", "recommended_action": ", ".join(actions or ["review recommendations"]), "expected_impact": "Reduce manual review time"})
    return pd.DataFrame(rows)
