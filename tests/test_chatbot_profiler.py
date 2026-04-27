import pandas as pd

from app.processing.profiler import profile_dataframe, profile_file


def test_profiler_detects_core_spreadsheet_issues():
    df = pd.DataFrame(
        {
            "Deal Date": ["2026-01-01", "bad-date", "2026-01-01"],
            "Amount": ["$1,200", "2.5M", "one million"],
            "Status": ["Open", "open", None],
        }
    )
    profile = profile_dataframe(df, "sample.csv", "csv")
    assert profile.rows == 3
    assert "Deal Date" in profile.suspected_date_columns
    assert "Amount" in profile.suspected_numeric_columns
    assert profile.missing_values["Status"] == 1
    assert profile.invalid_date_counts["Deal Date"] == 1


def test_profile_file_reads_csv_and_xlsx(tmp_path):
    df = pd.DataFrame({"date": ["2026-01-01"], "amount": ["1,200"]})
    csv_path = tmp_path / "sample.csv"
    xlsx_path = tmp_path / "sample.xlsx"
    df.to_csv(csv_path, index=False)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="First", index=False)
        pd.DataFrame({"other": [1]}).to_excel(writer, sheet_name="Second", index=False)

    csv_df, csv_profile = profile_file(csv_path)
    xlsx_df, xlsx_profile = profile_file(xlsx_path)

    assert len(csv_df) == 1
    assert csv_profile.file_type == "csv"
    assert len(xlsx_df) == 1
    assert xlsx_profile.sheet_names == ["First", "Second"]
    assert xlsx_profile.selected_sheet == "First"
