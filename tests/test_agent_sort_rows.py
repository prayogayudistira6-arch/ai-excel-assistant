import pandas as pd

from app.excel_agent.executor import execute_plan
from app.excel_agent.planner import fallback_plan
from app.excel_agent.profiler import profile_dataframe
from app.excel_agent.schemas import WorkbookContext
from app.excel_agent.tools.registry import ToolContext


def test_agent_sorts_salary_descending_from_prompt():
    df = pd.DataFrame(
        {
            "departemen": ["Sales", "Ops", "Finance"],
            "gaji": [900, 1200, 700],
        }
    )
    profile = profile_dataframe(df, WorkbookContext(file_name="payroll.csv", file_type="csv"))
    plan = fallback_plan("urutkan gaji dari terbesar", profile)
    ctx = ToolContext(original_df=df, working_df=df.copy(), data_profile=profile)

    execute_plan(ctx, plan)

    assert ctx.working_df["gaji"].tolist() == [1200, 900, 700]
