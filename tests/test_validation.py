from app.validation import validate_dataset


def test_validation_flags_deal_pipeline(sample_deal_pipeline):
    cleaned, issues = validate_dataset("deal_pipeline", sample_deal_pipeline)
    assert cleaned["stage"].tolist() == ["intro", "intro", "meeting"]
    assert "invalid_date" in set(issues["issue_type"])


def test_validation_flags_followups(sample_followups):
    _, issues = validate_dataset("followups", sample_followups)
    issue_types = set(issues["issue_type"])
    assert "invalid_enum" in issue_types
    assert "missing_required" in issue_types
    assert "invalid_date" in issue_types
