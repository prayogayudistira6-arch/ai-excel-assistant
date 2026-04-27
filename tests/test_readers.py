import pandas as pd

from app.io.readers import read_file


def test_read_excel_multi_sheet(tmp_path):
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="First Sheet", index=False)
        pd.DataFrame({"b": [2]}).to_excel(writer, sheet_name="Second", index=False)
    datasets = read_file(path)
    assert set(datasets) == {"first_sheet", "second"}


def test_read_csv_single_sheet(tmp_path):
    path = tmp_path / "messy file.csv"
    path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    datasets = read_file(path)
    assert list(datasets) == ["messy_file"]
    assert len(datasets["messy_file"]) == 2
