from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def generate_dummy_data(output_dir: str | Path = "data/input", overwrite: bool = False) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = [out / "deal_pipeline.xlsx", out / "followups.xlsx", out / "ops_requests.xlsx"]
    if not overwrite and any(path.exists() for path in files):
        raise FileExistsError("Dummy data exists. Pass --overwrite to replace it.")

    deal_pipeline = pd.DataFrame([
        ["Alpha Tech", "Fintech", "Intro", "ID", "1,500,000", "USD", "Ana", "2026-04-10", "Founder replied"],
        ["alpha tech ", "FinTech", "intro", "Indonesia", "1500000", "usd", "Ana", "10/04/2026", "duplicate casing"],
        ["Beta Health", "Health", "Meeting", "SG", "2000000", "SGD", "Budi", "2026/03/25", "Need product demo"],
        ["Gamma Logistics", "Logistics", "DD", "MY", "850000", "MYR", "Citra", "2026-02-12", "DD docs incomplete"],
        ["Delta Energy", "Climate", "IC", "PH", None, "USD", "Dewa", "2026-04-18", "Missing valuation"],
        ["Epsilon AI", "Software", "passed", "VN", "1200000", "USD", None, "2026-01-08", "Owner missing"],
        ["Zeta Foods", "F&B", "Unknown", "TH", "450000", "THB", "Fajar", "not-a-date", "Invalid stage"],
        ["Omega Retail", "Retail", "Meeting", "BR", "2.3m", "USD", "Gita", "2026-04-20", "Text valuation"],
    ], columns=["company_name", "sector", "stage", "country", "valuation_amount", "valuation_currency", "owner", "last_contact_date", "notes"])
    followups = pd.DataFrame([
        ["Alpha Tech", "Send deck", "2026-04-15", "Ana", "pending"],
        ["Beta Health", "Schedule product demo", "2026-04-05", "Budi", "open"],
        ["Gamma Logistics", "Collect DD docs", "2026-02-20", "Citra", "in_progress"],
        ["Delta Energy", "Ask for valuation", "2026-04-28", "Dewa", "pending"],
        ["Epsilon AI", "Reassign owner", "2026-01-15", None, "todo"],
        ["omega retail", "Normalize valuation", "2026-04-22", "Gita", "DONE"],
        ["Zeta Foods", "Verify stage", "2026-04-12", "Fajar", "blocked"],
        ["Lambda Agro", "First outreach", "2026-05-01", "Hana", "pending"],
    ], columns=["company_name", "next_action", "due_date", "owner", "status"])
    ops_requests = pd.DataFrame([
        ["Alpha Tech", "crm_cleanup", "high", "Duplicate names", "2026-04-11", "Ira", "open"],
        ["Beta Health", "reporting", "medium", "Need owner summary", "2026-04-03", "Joko", "in_progress"],
        ["Gamma Logistics", "diligence", "critical", "Missing legal docs", "2026-02-18", "Kiki", "OPEN"],
        ["Delta Energy", "data_fix", "high", "Currency columns mixed", "2026-04-21", "Lala", "done"],
        ["Epsilon AI", "followup", "medium", "No owner assigned", "2026-01-10", "Miko", "pending"],
        ["Zeta Foods", "data_fix", "low", "Invalid stage value", "2026-04-12", "Nina", "closed"],
        ["Omega Retail", "reporting", "high", "Need summary by country", "2026-04-20", "Omar", "open"],
        ["Alpha Tech", "crm_cleanup", "medium", "Trailing spaces", "2026-04-12", "Ira", "open"],
    ], columns=["entity_name", "request_type", "priority", "description", "request_date", "assignee", "status"])

    for path, sheet, frame in [
        (files[0], "deal_pipeline", deal_pipeline),
        (files[1], "followups", followups),
        (files[2], "ops_requests", ops_requests),
    ]:
        frame.to_excel(path, sheet_name=sheet, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/input")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    generate_dummy_data(args.output_dir, overwrite=args.overwrite)
    print(f"wrote dummy data to {args.output_dir}")


if __name__ == "__main__":
    main()
