from openpyxl import load_workbook
import pandas as pd

from app.excel_agent.executor import execute_plan
from app.excel_agent.profiler import profile_dataframe
from app.excel_agent.schemas import PlannerResult, ToolCall, WorkbookContext
from app.excel_agent.tools.registry import ToolContext


def test_highlight_column_export(tmp_path):
    df = pd.DataFrame({"Divisi": ["Ops"], "Sales": [100]})
    profile = profile_dataframe(df, WorkbookContext(file_name="demo.csv", file_type="csv"))
    ctx = ToolContext(original_df=df, working_df=df.copy(), data_profile=profile)
    plan = PlannerResult(
        assistant_response="",
        tool_calls=[
            ToolCall(tool="highlight_column", args={"column": "Divisi", "color": "red"}),
            ToolCall(tool="export_workbook", args={"output_name": str(tmp_path / "out.xlsx")}),
        ],
    )
    execute_plan(ctx, plan)
    wb = load_workbook(tmp_path / "out.xlsx")
    assert wb["cleaned_data"]["A2"].fill.fill_type == "solid"
