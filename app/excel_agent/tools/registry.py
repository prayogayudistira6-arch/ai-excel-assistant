from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from app.excel_agent.schemas import ToolExecutionResult


class AnalyzeWorkbookArgs(BaseModel):
    pass


class AnswerDataQuestionArgs(BaseModel):
    question: str


class ColumnsArgs(BaseModel):
    columns: list[str] | None = None


class ParseDateArgs(BaseModel):
    columns: list[str]
    date_format: str | None = None


class NumericArgs(BaseModel):
    columns: list[str]


class FillMissingArgs(BaseModel):
    strategy: str = "auto"
    columns: list[str] | None = None


class NormalizeTextArgs(BaseModel):
    columns: list[str] | None = None
    case: str = "lower"


class HighlightColumnArgs(BaseModel):
    column: str
    color: str = "red"


class HighlightRowsConditionArgs(BaseModel):
    column: str
    equals: str
    color: str = "yellow"


class SplitSheetArgs(BaseModel):
    column: str


class SortRowsArgs(BaseModel):
    columns: list[str]
    ascending: bool = True


class GroupSummaryArgs(BaseModel):
    group_by: list[str]
    value_column: str | None = None
    agg: str = "sum"


class PivotTableArgs(BaseModel):
    index: str
    columns: str | None = None
    values: str | None = None
    aggfunc: str = "sum"


class ExportWorkbookArgs(BaseModel):
    output_name: str | None = None


class EnrichApiArgs(BaseModel):
    pass


class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    original_df: pd.DataFrame
    working_df: pd.DataFrame
    data_profile: object | None = None
    operation_history: list[str] = Field(default_factory=list)
    snapshots: list[pd.DataFrame] = Field(default_factory=list)
    artifacts: dict[str, object] = Field(default_factory=dict)
    formatting: list[dict[str, object]] = Field(default_factory=list)
    latest_output_path: str | None = None


ToolFunction = Callable[[ToolContext, BaseModel], ToolExecutionResult]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: type[BaseModel]
    requires_confirmation: bool
    execute: ToolFunction


TOOLS: dict[str, ToolSpec] = {}


def register_tool(spec: ToolSpec) -> None:
    TOOLS[spec.name] = spec


def get_tool(name: str) -> ToolSpec:
    if name not in TOOLS:
        raise ValueError(f"Tool not allowed: {name}")
    return TOOLS[name]


def available_tools() -> list[dict[str, object]]:
    ensure_tools_registered()
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "requires_confirmation": spec.requires_confirmation,
            "schema": spec.input_schema.model_json_schema(),
        }
        for spec in TOOLS.values()
    ]


def ensure_tools_registered() -> None:
    if TOOLS:
        return
    import importlib

    importlib.import_module("app.excel_agent.tools.implementations")


ensure_tools_registered()
