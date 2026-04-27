from typing import Any

import pandas as pd


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def profile_dataframe(name: str, df: pd.DataFrame) -> dict[str, Any]:
    lower_cols = {col: str(col).lower() for col in df.columns}
    sample_rows = [
        {str(col): _json_value(value) for col, value in row.items()}
        for row in df.head(5).to_dict(orient="records")
    ]
    candidate_date_columns = [col for col, low in lower_cols.items() if "date" in low or low.endswith("_at")]
    candidate_numeric_columns = [
        col for col, low in lower_cols.items() if any(token in low for token in ["amount", "count", "total"])
    ]
    candidate_key_columns = [
        col for col, low in lower_cols.items() if low in {"company_name", "entity_name", "id"} or low.endswith("_id")
    ]
    anomalies: list[str] = []
    for col in candidate_date_columns:
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.isna().sum() > df[col].isna().sum():
            anomalies.append(f"{col} contains unparseable date values")
    return {
        "dataset_name": name,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": [str(col) for col in df.columns],
        "sample_rows": sample_rows,
        "dtype_summary": {str(col): str(dtype) for col, dtype in df.dtypes.items()},
        "null_counts": {str(col): int(count) for col, count in df.isna().sum().items()},
        "duplicate_count": int(df.duplicated().sum()),
        "candidate_date_columns": [str(col) for col in candidate_date_columns],
        "candidate_numeric_columns": [str(col) for col in candidate_numeric_columns],
        "candidate_key_columns": [str(col) for col in candidate_key_columns],
        "basic_anomalies": anomalies,
    }


def profile_datasets(datasets: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    return [profile_dataframe(name, df) for name, df in datasets.items()]
