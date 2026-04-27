from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkbookContext(BaseModel):
    file_name: str
    file_type: str
    sheet_names: list[str] = Field(default_factory=list)
    selected_sheet: str | None = None


class AgentDataProfile(BaseModel):
    file_name: str
    file_type: str
    sheet_names: list[str] = Field(default_factory=list)
    selected_sheet: str | None = None
    total_rows: int
    total_columns: int
    column_names: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
    duplicate_count: int
    sample_rows: list[dict[str, Any]]
    numeric_columns: list[str] = Field(default_factory=list)
    text_columns: list[str] = Field(default_factory=list)
    date_like_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    potential_id_columns: list[str] = Field(default_factory=list)
    suspicious_numeric_text_columns: list[str] = Field(default_factory=list)
    inconsistent_casing: dict[str, int] = Field(default_factory=dict)
    whitespace_issues: dict[str, int] = Field(default_factory=dict)
    invalid_date_candidates: dict[str, int] = Field(default_factory=dict)
    unique_value_count: dict[str, int] = Field(default_factory=dict)
    basic_numeric_stats: dict[str, dict[str, float | None]] = Field(default_factory=dict)
    detected_issues: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False


class PlannerResult(BaseModel):
    assistant_response: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    needs_confirmation: bool = False
    clarification_question: str | None = None
    confidence: float = 0.7


class ToolExecutionResult(BaseModel):
    success: bool
    message: str
    changed: bool = False
    artifacts: dict[str, Any] = Field(default_factory=dict)


class AgentRuntimeState(BaseModel):
    operation_history: list[str] = Field(default_factory=list)
    latest_output_path: str | None = None


ColorName = Literal["red", "yellow", "green", "blue", "orange", "purple", "gray"]
