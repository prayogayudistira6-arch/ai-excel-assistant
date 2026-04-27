import pytest

from app.actions import add_normalized_key, merge_datasets, remove_duplicates
from app.executor import ALLOWED_ACTIONS, ExecutionContext


def test_add_normalized_key_and_remove_duplicates(sample_ctx):
    ctx = add_normalized_key(sample_ctx, "deal_pipeline")
    ctx = remove_duplicates(ctx, "deal_pipeline", ["normalized_key"])
    assert "normalized_key" in ctx.datasets["deal_pipeline"]
    assert len(ctx.datasets["deal_pipeline"]) == 2
    assert "duplicate_normalized_key" in set(ctx.issues["issue_type"])


def test_merge_datasets(sample_deal_pipeline, sample_followups):
    ctx = ExecutionContext(datasets={"left": sample_deal_pipeline, "right": sample_followups})
    ctx = merge_datasets(ctx, target="left", left="left", right="right", on="company_name", output_name="merged")
    assert "merged" in ctx.datasets


def test_reject_unknown_action_registry():
    assert "unknown_action" not in ALLOWED_ACTIONS
    with pytest.raises(KeyError):
        ALLOWED_ACTIONS["unknown_action"]
