from app.excel_agent.tools.registry import TOOLS, available_tools


def test_tool_registry_contains_required_tools():
    required = {
        "analyze_workbook",
        "answer_data_question",
        "standardize_column_names",
        "trim_whitespace",
        "remove_duplicate_rows",
        "flag_duplicate_rows",
        "parse_date_columns",
        "convert_numeric_columns",
        "fill_missing_values",
        "flag_missing_values",
        "normalize_text_casing",
        "highlight_column",
        "highlight_rows_by_condition",
        "split_sheet_by_column",
        "sort_rows",
        "create_group_summary",
        "create_pivot_table",
        "create_flagged_issues_sheet",
        "create_management_report",
        "enrich_with_external_api",
        "export_workbook",
        "undo_last_operation",
    }
    assert required.issubset(set(TOOLS))
    assert all("schema" in tool for tool in available_tools())
