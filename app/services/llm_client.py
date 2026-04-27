from __future__ import annotations

import requests

from app.config import get_settings
from app.models import ActionPlan


class MockLLMClient:
    def create_plan(self, profile: list[dict[str, object]]) -> ActionPlan:
        dataset_names = {str(item["dataset_name"]) for item in profile}
        steps: list[dict[str, object]] = []
        for name in sorted(dataset_names):
            steps.append({"id": f"{name}_standardize", "action": "standardize_column_names", "target": name, "params": {}, "reason": "Normalize columns."})
            steps.append({"id": f"{name}_trim", "action": "trim_whitespace", "target": name, "params": {}, "reason": "Trim text values."})
        if "deal_pipeline" in dataset_names:
            steps.extend([
                {"id": "deal_key", "action": "add_normalized_key", "target": "deal_pipeline", "params": {"source_col": "company_name", "output_col": "normalized_key"}, "reason": "Prepare dedup key."},
                {"id": "deal_amount", "action": "coerce_numeric_columns", "target": "deal_pipeline", "params": {"columns": ["valuation_amount"]}, "reason": "Normalize numeric valuation."},
                {"id": "deal_dates", "action": "parse_date_columns", "target": "deal_pipeline", "params": {"columns": ["last_contact_date"]}, "reason": "Normalize dates."},
                {"id": "deal_dedupe", "action": "remove_duplicates", "target": "deal_pipeline", "params": {"subset": ["normalized_key"], "keep": "first"}, "reason": "Keep primary row per company."},
                {"id": "deal_enrich", "action": "enrich_country_metadata", "target": "deal_pipeline", "params": {"country_col": "country"}, "reason": "Add country metadata."},
                {"id": "deal_summary", "action": "create_grouped_summary", "target": "deal_pipeline", "params": {"by": ["owner", "stage"], "output_name": "summary"}, "reason": "Create operating summary."},
            ])
        if "followups" in dataset_names:
            steps.extend([
                {"id": "followup_dates", "action": "parse_date_columns", "target": "followups", "params": {"columns": ["due_date"]}, "reason": "Parse due dates."},
                {"id": "followup_overdue", "action": "flag_overdue_rows", "target": "followups", "params": {"due_date_col": "due_date", "status_col": "status"}, "reason": "Flag overdue followups."},
            ])
        return ActionPlan(summary="Mock plan for safe spreadsheet cleanup.", findings=[], warnings=[], steps=steps)


class OpenAIPlannerClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.fallback = MockLLMClient()

    def create_plan(self, profile: list[dict[str, object]]) -> ActionPlan:
        if not self.settings.openai_api_key:
            return self.fallback.create_plan(profile)
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.settings.openai_model,
                    "input": [{"role": "user", "content": f"Return a safe action plan for this profile: {profile}"}],
                },
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException:
            return self.fallback.create_plan(profile)
        return self.fallback.create_plan(profile)


def get_planner(mode: str) -> MockLLMClient | OpenAIPlannerClient:
    return OpenAIPlannerClient() if mode == "openai" else MockLLMClient()
