import pandas as pd

from app.chatbot.action_parser import parse_user_instruction, parse_user_text_to_plan, priority_recommendations, recommended_actions, sanitize_cleaning_plan
from app.models import CleaningAction, CleaningPlan
from app.processing.profiler import profile_dataframe


def test_recommended_actions_are_rule_based_from_profile():
    df = pd.DataFrame({"date": ["2026-01-01", "bad"], "amount": ["1,200", "2.5M"], "name": ["A", None]})
    profile = profile_dataframe(df, "sample.csv", "csv")
    actions = [action.action_name for action in recommended_actions(profile)]
    assert "standardize_column_names" in actions
    assert "parse_date_columns" in actions
    assert "convert_numeric_columns" in actions
    assert "fill_missing_values" in actions
    assert "flag_invalid_rows" in actions


def test_parse_user_text_to_plan_uses_keywords():
    df = pd.DataFrame({"due_date": ["2026-01-01"], "amount": ["1,200"]})
    profile = profile_dataframe(df, "sample.csv", "csv")
    plan = parse_user_text_to_plan("tolong parse tanggal dan convert numeric", profile)
    assert [action.action_name for action in plan.actions] == ["parse_date_columns", "convert_numeric_columns"]


def test_parse_natural_language_examples_to_whitelisted_plan():
    df = pd.DataFrame({"Due Date": ["2026-01-01"], "amount": ["1,200"], "name": ["A"]})
    profile = profile_dataframe(df, "sample.csv", "csv")

    duplicate_summary = parse_user_instruction("hapus duplicate dan buat summary", profile)
    flag_only = parse_user_instruction("jangan isi missing value, cukup flag saja", profile)
    dates_and_columns = parse_user_instruction("parse tanggal dan rapikan nama kolom", profile)

    assert duplicate_summary.plan is not None
    assert [action.action_name for action in duplicate_summary.plan.actions] == ["remove_duplicate_rows", "create_summary_sheet"]
    assert flag_only.plan is not None
    assert [action.action_name for action in flag_only.plan.actions] == ["flag_invalid_rows"]
    assert dates_and_columns.plan is not None
    assert [action.action_name for action in dates_and_columns.plan.actions] == ["standardize_column_names", "parse_date_columns"]


def test_parse_ambiguous_instruction_requests_clarification():
    df = pd.DataFrame({"a": [1]})
    profile = profile_dataframe(df, "sample.csv", "csv")
    parsed = parse_user_instruction("tolong bersihkan data ini", profile)
    assert parsed.needs_clarification is True
    assert parsed.plan is None
    assert "terlalu umum" in parsed.clarification_question


def test_priority_recommendations_group_actions():
    df = pd.DataFrame({"Due Date": ["bad"], "amount": ["1,200"], "name": [None]})
    profile = profile_dataframe(df, "sample.csv", "csv")
    priorities = priority_recommendations(profile)
    assert "standardize_column_names" in [action.action_name for action in priorities["Highly recommended"]]
    assert "create_summary_sheet" in [action.action_name for action in priorities["Optional"]]
    assert "fill_missing_values" in [action.action_name for action in priorities["Risky / requires confirmation"]]


def test_parse_sort_department_and_salary_prompts():
    df = pd.DataFrame({"departemen": ["Ops", "Finance"], "gaji": [900, 1200]})
    profile = profile_dataframe(df, "sample.csv", "csv")

    by_department = parse_user_instruction("urutkan departemen", profile)
    by_salary = parse_user_instruction("urutkan gaji dari terbesar", profile)

    assert by_department.plan is not None
    assert by_department.plan.actions[0].action_name == "sort_rows"
    assert by_department.plan.actions[0].columns == ["departemen"]
    assert by_department.plan.actions[0].parameters["ascending"] is True
    assert by_salary.plan is not None
    assert by_salary.plan.actions[0].action_name == "sort_rows"
    assert by_salary.plan.actions[0].columns == ["gaji"]
    assert by_salary.plan.actions[0].parameters["ascending"] is False


def test_parse_sort_ambiguous_prompt_requests_column_clarification():
    df = pd.DataFrame({"departemen": ["Ops"], "gaji": [900]})
    profile = profile_dataframe(df, "sample.csv", "csv")
    parsed = parse_user_instruction("urutkan data", profile)
    assert parsed.needs_clarification is True
    assert "kolom" in parsed.clarification_question


def test_sanitize_cleaning_plan_removes_unknown_actions():
    plan = CleaningPlan(
        actions=[
            CleaningAction(action_name="standardize_column_names"),
            CleaningAction(action_name="exec_python_code"),
        ]
    )
    sanitized = sanitize_cleaning_plan(plan)
    assert [action.action_name for action in sanitized.actions] == ["standardize_column_names"]
