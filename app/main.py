from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.executor import ExecutionContext, execute_plan
from app.exporter import export_workbook
from app.io.readers import read_input_dir
from app.profiling import profile_datasets
from app.services.llm_client import get_planner
from app.validation import validate_datasets


def run_pipeline(input_dir: str, output: str, llm_mode: str = "mock") -> Path:
    datasets = read_input_dir(input_dir)
    profile = profile_datasets(datasets)
    cleaned, issues = validate_datasets(datasets)
    planner = get_planner(llm_mode)
    plan = planner.create_plan(profile)
    ctx = execute_plan(ExecutionContext(datasets=cleaned, issues=issues), plan)
    return export_workbook(output, profile, ctx)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=settings.input_dir)
    parser.add_argument("--output", default=settings.default_output_file)
    parser.add_argument("--llm-mode", default=settings.llm_mode, choices=["mock", "openai"])
    parser.add_argument("--generate-dummy-data", action="store_true")
    args = parser.parse_args()

    if args.generate_dummy_data:
        from scripts.generate_dummy_data import generate_dummy_data

        generate_dummy_data(args.input_dir, overwrite=True)
    output_path = run_pipeline(args.input_dir, args.output, args.llm_mode)
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
