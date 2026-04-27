import pandas as pd

from app.excel_agent.executor import execute_plan
from app.excel_agent.profiler import profile_dataframe
from app.excel_agent.schemas import PlannerResult, ToolCall, WorkbookContext
from app.excel_agent.tools.registry import ToolContext


def test_group_summary_totals_sales_by_region():
    df = pd.DataFrame({"Region": ["A", "A", "B"], "Sales": [100, 50, 25]})
    profile = profile_dataframe(df, WorkbookContext(file_name="demo.csv", file_type="csv"))
    ctx = ToolContext(original_df=df, working_df=df.copy(), data_profile=profile)
    execute_plan(ctx, PlannerResult(assistant_response="", tool_calls=[ToolCall(tool="create_group_summary", args={"group_by": ["Region"], "value_column": "Sales", "agg": "sum"})]))
    summary = ctx.artifacts["group_summary"]
    assert summary.loc[summary["Region"] == "A", "Sales"].iloc[0] == 150
