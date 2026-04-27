import pandas as pd

from app.ai.providers.base import ProviderConfig
from app.excel_agent.planner import fallback_plan, plan_with_provider
from app.excel_agent.profiler import profile_dataframe
from app.excel_agent.schemas import WorkbookContext


def _profile():
    df = pd.DataFrame({"Divisi": ["Ops", "Finance"], "Sales": [100, 200], "Status": ["overdue", "done"]})
    return profile_dataframe(df, WorkbookContext(file_name="demo.csv", file_type="csv"))


def test_planner_maps_highlight_column_prompt():
    plan = fallback_plan("buat warna kolom divisi jadi merah", _profile(), [])
    assert plan.tool_calls[0].tool == "highlight_column"
    assert plan.tool_calls[0].args["column"] == "Divisi"
    assert plan.tool_calls[0].args["color"] == "red"


def test_planner_requires_confirmation_for_split_sheet():
    plan = fallback_plan("buat tabel terpisah berdasarkan divisi", _profile(), [])
    assert plan.needs_confirmation is True
    assert plan.tool_calls[0].tool == "split_sheet_by_column"


def test_provider_plan_forces_confirmation_from_tool_registry(monkeypatch):
    class FakeProvider:
        def generate(self, system_prompt, user_prompt):
            return '{"assistant_response":"plan","tool_calls":[{"tool":"split_sheet_by_column","args":{"column":"Divisi"}}],"needs_confirmation":false}'

    monkeypatch.setattr("app.excel_agent.planner.create_provider", lambda config: FakeProvider())

    plan = plan_with_provider(
        "buat tabel terpisah berdasarkan divisi",
        _profile(),
        [],
        ProviderConfig(provider="openai_compatible", api_key="test", model="demo"),
    )

    assert plan.needs_confirmation is True
    assert plan.tool_calls[0].requires_confirmation is True
