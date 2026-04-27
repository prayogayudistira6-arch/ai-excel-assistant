from __future__ import annotations

import pandas as pd


ISSUE_COLUMNS = ["dataset", "row_index", "issue_type", "column_name", "severity", "detail"]
VALID_STAGES = {"intro", "meeting", "dd", "ic", "passed"}
VALID_FOLLOWUP_STATUS = {"pending", "in_progress", "done", "blocked"}
VALID_OPS_PRIORITY = {"low", "medium", "high", "critical"}
VALID_OPS_STATUS = {"open", "in_progress", "done", "closed"}


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [str(col).strip().lower().replace(" ", "_") for col in result.columns]
    return result


def _issue(dataset: str, row_index: int | str, issue_type: str, column: str, severity: str, detail: str) -> dict[str, object]:
    return {
        "dataset": dataset,
        "row_index": row_index,
        "issue_type": issue_type,
        "column_name": column,
        "severity": severity,
        "detail": detail,
    }


def _normalize_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for col in result.select_dtypes(include=["object"]).columns:
        result[col] = result[col].map(lambda value: value.strip() if isinstance(value, str) else value)
    return result


def validate_dataset(name: str, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cleaned = _normalize_text_columns(standardize_columns(df))
    issues: list[dict[str, object]] = []

    if name == "deal_pipeline":
        required = ["company_name"]
        for col in required:
            if col not in cleaned:
                issues.append(_issue(name, "dataset", "missing_column", col, "high", f"{col} is required"))
            else:
                blank = cleaned[col].isna() | (cleaned[col].astype(str).str.strip() == "")
                for idx in cleaned.index[blank]:
                    issues.append(_issue(name, int(idx), "missing_required", col, "high", f"{col} is blank"))
        if "stage" in cleaned:
            cleaned["stage"] = cleaned["stage"].astype(str).str.strip().str.lower()
            bad = ~cleaned["stage"].isin(VALID_STAGES)
            for idx in cleaned.index[bad]:
                issues.append(_issue(name, int(idx), "invalid_enum", "stage", "high", f"{cleaned.at[idx, 'stage']} not in allowed stages"))
        if "last_contact_date" in cleaned:
            parsed = pd.to_datetime(cleaned["last_contact_date"], errors="coerce")
            bad = parsed.isna() & cleaned["last_contact_date"].notna()
            for idx in cleaned.index[bad]:
                issues.append(_issue(name, int(idx), "invalid_date", "last_contact_date", "medium", "date failed parsing"))

    if name == "followups":
        for col in ["company_name", "due_date", "status"]:
            if col not in cleaned:
                issues.append(_issue(name, "dataset", "missing_column", col, "high", f"{col} is required"))
        if "status" in cleaned:
            cleaned["status"] = cleaned["status"].astype(str).str.strip().str.lower()
            bad = ~cleaned["status"].isin(VALID_FOLLOWUP_STATUS)
            for idx in cleaned.index[bad]:
                issues.append(_issue(name, int(idx), "invalid_enum", "status", "high", f"{cleaned.at[idx, 'status']} not in allowed statuses"))
        if "due_date" in cleaned:
            parsed = pd.to_datetime(cleaned["due_date"], errors="coerce")
            bad = parsed.isna() & cleaned["due_date"].notna()
            for idx in cleaned.index[bad]:
                issues.append(_issue(name, int(idx), "invalid_date", "due_date", "medium", "date failed parsing"))
            if "status" in cleaned:
                overdue = parsed.lt(pd.Timestamp.today().normalize()) & ~cleaned["status"].isin({"done"})
                for idx in cleaned.index[overdue.fillna(False)]:
                    issues.append(_issue(name, int(idx), "overdue_followup", "due_date", "high", "due_date before today and status not done"))
        if "owner" in cleaned:
            blank = cleaned["owner"].isna() | (cleaned["owner"].astype(str).str.strip() == "")
            for idx in cleaned.index[blank]:
                issues.append(_issue(name, int(idx), "missing_required", "owner", "medium", "owner is blank"))

    if name == "ops_requests":
        if "priority" in cleaned:
            cleaned["priority"] = cleaned["priority"].astype(str).str.strip().str.lower()
            bad = ~cleaned["priority"].isin(VALID_OPS_PRIORITY)
            for idx in cleaned.index[bad]:
                issues.append(_issue(name, int(idx), "invalid_enum", "priority", "high", "invalid priority"))
        if "status" in cleaned:
            cleaned["status"] = cleaned["status"].astype(str).str.strip().str.lower()
            bad = ~cleaned["status"].isin(VALID_OPS_STATUS)
            for idx in cleaned.index[bad]:
                issues.append(_issue(name, int(idx), "invalid_enum", "status", "medium", "invalid status"))
        if "request_date" in cleaned:
            parsed = pd.to_datetime(cleaned["request_date"], errors="coerce")
            bad = parsed.isna() & cleaned["request_date"].notna()
            for idx in cleaned.index[bad]:
                issues.append(_issue(name, int(idx), "invalid_date", "request_date", "medium", "date failed parsing"))

    return cleaned, pd.DataFrame(issues, columns=ISSUE_COLUMNS)


def validate_datasets(datasets: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    cleaned: dict[str, pd.DataFrame] = {}
    issue_frames: list[pd.DataFrame] = []
    for name, df in datasets.items():
        cleaned_df, issues_df = validate_dataset(name, df)
        cleaned[name] = cleaned_df
        issue_frames.append(issues_df)
    issues = pd.concat(issue_frames, ignore_index=True) if issue_frames else pd.DataFrame(columns=ISSUE_COLUMNS)
    return cleaned, issues
