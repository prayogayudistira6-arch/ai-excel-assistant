from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from app.models import ActionPlan, ActionStep, ExecutionLog
from app.validation import ISSUE_COLUMNS


@dataclass
class ExecutionContext:
    datasets: dict[str, pd.DataFrame]
    issues: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=ISSUE_COLUMNS))
    api_enrichment: pd.DataFrame = field(default_factory=pd.DataFrame)
    summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    action_log: list[ExecutionLog] = field(default_factory=list)


ActionFn = Callable[..., ExecutionContext]
ALLOWED_ACTIONS: dict[str, ActionFn] = {}


def register_action(name: str, fn: ActionFn) -> None:
    ALLOWED_ACTIONS[name] = fn


def validate_step(step: ActionStep) -> None:
    if step.action.value not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action: {step.action.value}")
    if step.target and step.target not in {"", "summary"} and step.target not in getattr(validate_step, "datasets", set()):
        return


def apply_step(ctx: ExecutionContext, step: ActionStep) -> ExecutionContext:
    action_name = step.action.value
    if action_name not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action: {action_name}")
    if step.target not in ctx.datasets:
        raise ValueError(f"Unknown target dataset: {step.target}")
    fn = ALLOWED_ACTIONS[action_name]
    try:
        ctx = fn(ctx, target=step.target, **step.params)
        ctx.action_log.append(ExecutionLog(step_id=step.id, action=action_name, target=step.target, status="ok"))
        return ctx
    except Exception as exc:
        ctx.action_log.append(ExecutionLog(step_id=step.id, action=action_name, target=step.target, status="error", detail=str(exc)))
        raise


def execute_plan(ctx: ExecutionContext, plan: ActionPlan) -> ExecutionContext:
    # Lazy import registers actions without circular imports at module load time.
    import app.actions  # noqa: F401

    for step in plan.steps:
        ctx = apply_step(ctx, step)
    return ctx
