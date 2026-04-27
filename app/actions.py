from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.executor import ExecutionContext, register_action
from app.services.country_api import get_country_metadata
from app.validation import ISSUE_COLUMNS


def _normalize_key(value: object) -> str:
    return re.sub(r"[^0-9a-z]+", " ", "" if value is None else str(value).lower()).strip()


def _append_issues(ctx: ExecutionContext, rows: list[dict[str, object]]) -> None:
    if rows:
        ctx.issues = pd.concat([ctx.issues, pd.DataFrame(rows, columns=ISSUE_COLUMNS)], ignore_index=True)


def standardize_column_names(ctx: ExecutionContext, target: str) -> ExecutionContext:
    df = ctx.datasets[target].copy()
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
    ctx.datasets[target] = df
    return ctx


def trim_whitespace(ctx: ExecutionContext, target: str, columns: list[str] | None = None) -> ExecutionContext:
    df = ctx.datasets[target].copy()
    selected = columns or list(df.select_dtypes(include=["object"]).columns)
    for col in selected:
        if col in df:
            df[col] = df[col].map(lambda value: value.strip() if isinstance(value, str) else value)
    ctx.datasets[target] = df
    return ctx


def add_normalized_key(
    ctx: ExecutionContext,
    target: str,
    source_col: str = "company_name",
    output_col: str = "normalized_key",
) -> ExecutionContext:
    df = ctx.datasets[target].copy()
    if source_col not in df:
        raise ValueError(f"{source_col} not found in {target}")
    df[output_col] = df[source_col].map(_normalize_key)
    ctx.datasets[target] = df
    return ctx


def coerce_numeric_columns(ctx: ExecutionContext, target: str, columns: list[str]) -> ExecutionContext:
    df = ctx.datasets[target].copy()
    for col in columns:
        if col not in df:
            continue
        values = df[col].astype(str).str.lower().str.replace(",", "", regex=False).str.strip()
        multiplier = values.str.endswith("m").map(lambda flag: 1_000_000 if flag else 1)
        values = values.str.rstrip("m")
        df[col] = pd.to_numeric(values, errors="coerce") * multiplier
    ctx.datasets[target] = df
    return ctx


def parse_date_columns(ctx: ExecutionContext, target: str, columns: list[str], dayfirst: bool = False) -> ExecutionContext:
    df = ctx.datasets[target].copy()
    issues: list[dict[str, object]] = []
    for col in columns:
        if col not in df:
            continue
        original = df[col]
        parsed = pd.to_datetime(original, errors="coerce", dayfirst=dayfirst)
        bad = parsed.isna() & original.notna()
        for idx in df.index[bad]:
            issues.append({"dataset": target, "row_index": int(idx), "issue_type": "invalid_date", "column_name": col, "severity": "medium", "detail": "date failed parsing"})
        df[col] = parsed
    ctx.datasets[target] = df
    _append_issues(ctx, issues)
    return ctx


def fill_missing_values(ctx: ExecutionContext, target: str, rules: dict[str, Any]) -> ExecutionContext:
    df = ctx.datasets[target].copy()
    for col, value in rules.items():
        if col in df:
            df[col] = df[col].fillna(value)
    ctx.datasets[target] = df
    return ctx


def remove_duplicates(ctx: ExecutionContext, target: str, subset: list[str], keep: str = "first") -> ExecutionContext:
    df = ctx.datasets[target].copy()
    duplicate_mask = df.duplicated(subset=subset, keep=keep)
    issues = [
        {
            "dataset": target,
            "row_index": int(idx),
            "issue_type": "duplicate_normalized_key",
            "column_name": ",".join(subset),
            "severity": "high",
            "detail": "duplicate row removed",
        }
        for idx in df.index[duplicate_mask]
    ]
    ctx.datasets[target] = df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
    _append_issues(ctx, issues)
    return ctx


def merge_datasets(
    ctx: ExecutionContext,
    target: str,
    left: str,
    right: str,
    on: list[str] | str,
    output_name: str,
    how: str = "left",
    validate: str | None = None,
) -> ExecutionContext:
    ctx.datasets[output_name] = ctx.datasets[left].merge(ctx.datasets[right], on=on, how=how, validate=validate)
    return ctx


def enrich_country_metadata(ctx: ExecutionContext, target: str, country_col: str) -> ExecutionContext:
    df = ctx.datasets[target].copy()
    if country_col not in df:
        raise ValueError(f"{country_col} not found in {target}")
    metadata_rows = [get_country_metadata(value) for value in df[country_col]]
    metadata = pd.DataFrame(metadata_rows)
    metadata.insert(0, country_col, df[country_col].to_list())
    for col in ["country_name", "iso2", "iso3", "region", "income_level", "capital_city", "latitude", "longitude"]:
        df[col] = metadata[col]
    ctx.datasets[target] = df
    ctx.api_enrichment = metadata
    return ctx


def flag_overdue_rows(
    ctx: ExecutionContext,
    target: str,
    due_date_col: str,
    status_col: str,
    done_values: list[str] | None = None,
) -> ExecutionContext:
    df = ctx.datasets[target].copy()
    done = {value.lower() for value in (done_values or ["done"])}
    due = pd.to_datetime(df[due_date_col], errors="coerce")
    status = df[status_col].astype(str).str.lower()
    overdue = due.lt(pd.Timestamp.today().normalize()) & ~status.isin(done)
    df["overdue_followup"] = overdue.fillna(False)
    issues = [
        {"dataset": target, "row_index": int(idx), "issue_type": "overdue_followup", "column_name": due_date_col, "severity": "high", "detail": "due_date before today and status not done"}
        for idx in df.index[df["overdue_followup"]]
    ]
    ctx.datasets[target] = df
    _append_issues(ctx, issues)
    return ctx


def create_grouped_summary(ctx: ExecutionContext, target: str, by: list[str], output_name: str) -> ExecutionContext:
    df = ctx.datasets[target]
    existing = [col for col in by if col in df]
    if existing:
        ctx.summary = df.groupby(existing, dropna=False).size().reset_index(name="count")
    else:
        ctx.summary = pd.DataFrame({"count": [len(df)]})
    ctx.datasets[output_name] = ctx.summary
    return ctx


for _name, _fn in {
    "standardize_column_names": standardize_column_names,
    "trim_whitespace": trim_whitespace,
    "add_normalized_key": add_normalized_key,
    "coerce_numeric_columns": coerce_numeric_columns,
    "parse_date_columns": parse_date_columns,
    "fill_missing_values": fill_missing_values,
    "remove_duplicates": remove_duplicates,
    "merge_datasets": merge_datasets,
    "enrich_country_metadata": enrich_country_metadata,
    "flag_overdue_rows": flag_overdue_rows,
    "create_grouped_summary": create_grouped_summary,
}.items():
    register_action(_name, _fn)
