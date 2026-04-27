from __future__ import annotations

from app.excel_agent.schemas import PlannerResult, ToolCall, ToolExecutionResult
from app.excel_agent.tools.registry import ToolContext, get_tool


DESTRUCTIVE_TOOLS = {"remove_duplicate_rows", "fill_missing_values", "split_sheet_by_column"}


def validate_tool_call(call: ToolCall) -> ToolCall:
    spec = get_tool(call.tool)
    args = spec.input_schema.model_validate(call.args)
    return ToolCall(tool=call.tool, args=args.model_dump(), requires_confirmation=spec.requires_confirmation)


def execute_tool_call(ctx: ToolContext, call: ToolCall) -> ToolExecutionResult:
    spec = get_tool(call.tool)
    args = spec.input_schema.model_validate(call.args)
    result = spec.execute(ctx, args)
    ctx.operation_history.append(f"{call.tool}: {result.message}")
    return result


def execute_plan(ctx: ToolContext, plan: PlannerResult) -> list[ToolExecutionResult]:
    results: list[ToolExecutionResult] = []
    for raw_call in plan.tool_calls:
        call = validate_tool_call(raw_call)
        results.append(execute_tool_call(ctx, call))
    return results
