from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.processing.validator import FLAGGED_COLUMNS, detect_flagged_issues, make_issue


def empty_issues() -> pd.DataFrame:
    return pd.DataFrame(columns=FLAGGED_COLUMNS)


def standardize_column_names(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    result = df.copy()
    before = [str(col) for col in result.columns]
    result.columns = [re.sub(r"[^0-9a-zA-Z]+", "_", str(col).strip().lower()).strip("_") for col in result.columns]
    changed = sum(1 for old, new in zip(before, result.columns) if old != new)
    return result, empty_issues(), f"Standardized {changed} column names"


def trim_whitespace(df: pd.DataFrame, columns: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    result = df.copy()
    selected = columns or [str(col) for col in result.columns if result[col].dtype == "object" or str(result[col].dtype).startswith("str")]
    changed = 0
    for col in selected:
        if col not in result:
            continue
        before = result[col].copy()
        result[col] = result[col].map(lambda value: value.strip() if isinstance(value, str) else value)
        changed += int((before.astype(str) != result[col].astype(str)).sum())
    return result, empty_issues(), f"Trimmed whitespace in {len(selected)} columns ({changed} cells changed)"


def remove_duplicate_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    issues = pd.DataFrame(
        [
            make_issue(int(idx), "all_columns", "duplicate_row", "duplicate", "Remove duplicate row")
            for idx in df.index[df.duplicated(keep="first")]
        ],
        columns=FLAGGED_COLUMNS,
    )
    result = df.drop_duplicates(keep="first").reset_index(drop=True)
    removed = len(df) - len(result)
    return result, issues, f"Removed {removed} full duplicate rows"


def parse_date_columns(df: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    result = df.copy()
    issues: list[dict[str, object]] = []
    invalid_count = 0
    for col in columns:
        if col not in result:
            continue
        original = result[col].copy()
        parsed = pd.to_datetime(original, errors="coerce")
        bad = parsed.isna() & original.notna() & (original.astype(str).str.strip() != "")
        invalid_count += int(bad.sum())
        for idx in result.index[bad]:
            issues.append(make_issue(int(idx), col, "invalid_date", original.at[idx], "Leave blank and review source value"))
        result[col] = parsed
    return result, pd.DataFrame(issues, columns=FLAGGED_COLUMNS), f"Parsed {len(columns)} date columns; {invalid_count} invalid date values flagged"


def _parse_numeric_value(value: Any) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if not text:
        return None
    multiplier = 1.0
    if text.endswith("m"):
        multiplier = 1_000_000.0
        text = text[:-1]
    elif text.endswith("k"):
        multiplier = 1_000.0
        text = text[:-1]
    text = text.replace("$", "").replace(",", "").replace(" ", "")
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def convert_numeric_columns(df: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    result = df.copy()
    issues: list[dict[str, object]] = []
    invalid_count = 0
    for col in columns:
        if col not in result:
            continue
        converted = []
        for idx, value in result[col].items():
            parsed = _parse_numeric_value(value)
            if parsed is None and not pd.isna(value) and str(value).strip():
                invalid_count += 1
                issues.append(make_issue(int(idx), col, "invalid_numeric", value, "Review numeric text"))
            converted.append(parsed)
        result[col] = pd.Series(converted, index=result.index, dtype="float")
    return result, pd.DataFrame(issues, columns=FLAGGED_COLUMNS), f"Converted {len(columns)} numeric columns; {invalid_count} invalid numeric values flagged"


def fill_missing_values(df: pd.DataFrame, columns: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    result = df.copy()
    selected = columns or [str(col) for col in result.columns]
    issues: list[dict[str, object]] = []
    filled = 0
    for col in selected:
        if col not in result:
            continue
        mask = result[col].isna() | (result[col].astype(str).str.strip() == "")
        for idx in result.index[mask]:
            issues.append(make_issue(int(idx), col, "missing_value", result.at[idx, col], "Filled with default value" if not pd.api.types.is_datetime64_any_dtype(result[col]) else "Left blank for review"))
        if not bool(mask.any()):
            continue
        if pd.api.types.is_datetime64_any_dtype(result[col]):
            continue
        if pd.api.types.is_numeric_dtype(result[col]):
            value = result[col].median()
            if pd.isna(value):
                continue
            if pd.api.types.is_integer_dtype(result[col]) and not float(value).is_integer():
                result[col] = result[col].astype("float64")
            result.loc[mask, col] = value
            filled += int(mask.sum())
        else:
            result.loc[mask, col] = "Unknown"
            filled += int(mask.sum())
    return result, pd.DataFrame(issues, columns=FLAGGED_COLUMNS), f"Filled {filled} missing values with safe defaults"


def normalize_text_casing(df: pd.DataFrame, columns: list[str] | None = None, case: str = "lower") -> tuple[pd.DataFrame, pd.DataFrame, str]:
    result = df.copy()
    selected = columns or [str(col) for col in result.columns if result[col].dtype == "object" or str(result[col].dtype).startswith("str")]
    for col in selected:
        if col not in result:
            continue
        if case == "title":
            result[col] = result[col].map(lambda value: value.title() if isinstance(value, str) else value)
        else:
            result[col] = result[col].map(lambda value: value.lower() if isinstance(value, str) else value)
    return result, empty_issues(), f"Normalized text casing for {len(selected)} columns"


def flag_invalid_rows(df: pd.DataFrame, date_columns: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    issues = detect_flagged_issues(df, date_columns=date_columns)
    return df.copy(), issues, f"Created flagged issues sheet with {len(issues)} detected issues"


def sort_rows(df: pd.DataFrame, columns: list[str], ascending: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    selected = [col for col in columns if col in df]
    if not selected:
        raise ValueError("No valid sort column was provided")
    result = df.sort_values(by=selected, ascending=ascending, kind="mergesort").reset_index(drop=True)
    direction = "ascending" if ascending else "descending"
    return result, empty_issues(), f"Sorted rows by {', '.join(selected)} ({direction})"


def create_summary_sheet(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"metric": "total rows", "value": len(df)},
            {"metric": "total columns", "value": len(df.columns)},
            {"metric": "total missing values", "value": int(df.isna().sum().sum())},
            {"metric": "duplicate rows", "value": int(df.duplicated().sum())},
        ]
    )
