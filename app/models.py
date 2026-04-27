from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AllowedAction(str, Enum):
    standardize_column_names = "standardize_column_names"
    trim_whitespace = "trim_whitespace"
    add_normalized_key = "add_normalized_key"
    coerce_numeric_columns = "coerce_numeric_columns"
    parse_date_columns = "parse_date_columns"
    fill_missing_values = "fill_missing_values"
    remove_duplicates = "remove_duplicates"
    merge_datasets = "merge_datasets"
    enrich_country_metadata = "enrich_country_metadata"
    flag_overdue_rows = "flag_overdue_rows"
    create_grouped_summary = "create_grouped_summary"


class DatasetProfile(BaseModel):
    dataset_name: str
    row_count: int
    column_count: int
    columns: list[str]
    sample_rows: list[dict[str, Any]]
    dtype_summary: dict[str, str]
    null_counts: dict[str, int]
    duplicate_count: int
    candidate_date_columns: list[str] = Field(default_factory=list)
    candidate_numeric_columns: list[str] = Field(default_factory=list)
    candidate_key_columns: list[str] = Field(default_factory=list)
    basic_anomalies: list[str] = Field(default_factory=list)


class IssueRecord(BaseModel):
    dataset: str
    row_index: int | str
    issue_type: str
    column_name: str
    severity: str
    detail: str


class ActionStep(BaseModel):
    id: str
    action: AllowedAction
    target: str
    params: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class ActionPlan(BaseModel):
    summary: str
    findings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    steps: list[ActionStep] = Field(default_factory=list)


class ExecutionLog(BaseModel):
    step_id: str
    action: str
    target: str
    status: str
    detail: str = ""


class DataProfile(BaseModel):
    file_name: str
    file_type: str
    sheet_names: list[str] = Field(default_factory=list)
    selected_sheet: str | None = None
    rows: int
    columns: int
    column_names: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
    duplicate_count: int
    sample_rows: list[dict[str, Any]]
    suspected_date_columns: list[str] = Field(default_factory=list)
    suspected_numeric_columns: list[str] = Field(default_factory=list)
    suspected_categorical_columns: list[str] = Field(default_factory=list)
    detected_issues: list[str] = Field(default_factory=list)
    casing_inconsistencies: dict[str, int] = Field(default_factory=dict)
    invalid_date_counts: dict[str, int] = Field(default_factory=dict)
    whitespace_issues: dict[str, int] = Field(default_factory=dict)
    possible_id_columns: list[str] = Field(default_factory=list)
    possible_name_columns: list[str] = Field(default_factory=list)


class CleaningAction(BaseModel):
    action_name: str
    enabled: bool = True
    columns: list[str] | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class CleaningPlan(BaseModel):
    actions: list[CleaningAction] = Field(default_factory=list)
    user_instruction: str | None = None


class CleaningResult(BaseModel):
    original_rows: int
    cleaned_rows: int
    removed_duplicates: int
    total_missing_values: int
    flagged_issues_count: int
    output_path: str
    change_log: list[str] = Field(default_factory=list)
    invalid_dates_found: int = 0
    numeric_conversion_issues: int = 0
    actions_executed: list[str] = Field(default_factory=list)


class DetectedIssue(BaseModel):
    issue_type: str
    affected_column: str | None = None
    affected_rows_count: int
    business_impact: str
    recommended_action: str
    severity: str = "Medium"


class ApiEnrichmentResult(BaseModel):
    key: str
    normalized_name: str | None = None
    region: str | None = None
    currency: str | None = None
    api_status: str
    detail: str = ""
