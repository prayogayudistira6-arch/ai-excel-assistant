from __future__ import annotations

import pandas as pd

FLAGGED_COLUMNS = ["row_index", "column", "issue_type", "original_value", "suggested_fix"]


def make_issue(row_index: int | str, column: str, issue_type: str, original_value: object, suggested_fix: str) -> dict[str, object]:
    return {
        "row_index": row_index,
        "column": column,
        "issue_type": issue_type,
        "original_value": "" if pd.isna(original_value) else original_value,
        "suggested_fix": suggested_fix,
    }


def detect_missing_issues(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    target_columns = columns or [str(col) for col in df.columns]
    issues: list[dict[str, object]] = []
    for col in target_columns:
        if col not in df:
            continue
        mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        for idx in df.index[mask]:
            issues.append(make_issue(int(idx), col, "missing_value", df.at[idx, col], "Fill or verify value"))
    return pd.DataFrame(issues, columns=FLAGGED_COLUMNS)


def detect_duplicate_issues(df: pd.DataFrame, subset: list[str] | None = None) -> pd.DataFrame:
    mask = df.duplicated(subset=subset, keep="first")
    issues = [
        make_issue(int(idx), ",".join(subset or ["all_columns"]), "duplicate_row", "duplicate", "Remove duplicate row")
        for idx in df.index[mask]
    ]
    return pd.DataFrame(issues, columns=FLAGGED_COLUMNS)


def detect_invalid_date_issues(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    issues: list[dict[str, object]] = []
    for col in columns:
        if col not in df:
            continue
        parsed = pd.to_datetime(df[col], errors="coerce")
        bad = parsed.isna() & df[col].notna() & (df[col].astype(str).str.strip() != "")
        for idx in df.index[bad]:
            issues.append(make_issue(int(idx), col, "invalid_date", df.at[idx, col], "Review date format"))
    return pd.DataFrame(issues, columns=FLAGGED_COLUMNS)


def detect_flagged_issues(df: pd.DataFrame, date_columns: list[str] | None = None) -> pd.DataFrame:
    frames = [
        detect_missing_issues(df),
        detect_duplicate_issues(df),
        detect_invalid_date_issues(df, date_columns or []),
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=FLAGGED_COLUMNS)
