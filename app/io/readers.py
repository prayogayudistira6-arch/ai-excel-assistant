from pathlib import Path
import re

import pandas as pd


def sanitize_dataset_name(name: str) -> str:
    clean = re.sub(r"[^0-9a-zA-Z]+", "_", Path(name).stem.strip().lower()).strip("_")
    return clean or "dataset"


def read_file(path: str | Path) -> dict[str, pd.DataFrame]:
    file_path = Path(path)
    if file_path.suffix.lower() in {".xlsx", ".xls"}:
        sheets = pd.read_excel(file_path, sheet_name=None)
        return {sanitize_dataset_name(name): df for name, df in sheets.items()}
    if file_path.suffix.lower() == ".csv":
        return {sanitize_dataset_name(file_path.stem): pd.read_csv(file_path, on_bad_lines="warn")}
    raise ValueError(f"Unsupported input file: {file_path}")


def read_input_dir(input_dir: str | Path) -> dict[str, pd.DataFrame]:
    datasets: dict[str, pd.DataFrame] = {}
    for path in sorted(Path(input_dir).glob("*")):
        if path.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
            continue
        for name, df in read_file(path).items():
            unique_name = name
            counter = 2
            while unique_name in datasets:
                unique_name = f"{name}_{counter}"
                counter += 1
            datasets[unique_name] = df
    if not datasets:
        raise FileNotFoundError(f"No Excel or CSV files found in {input_dir}")
    return datasets
