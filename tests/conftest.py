import pandas as pd
import pytest

from app.executor import ExecutionContext


@pytest.fixture
def sample_deal_pipeline():
    return pd.DataFrame({
        "company_name": ["Alpha Tech", "alpha tech ", "Beta Health"],
        "stage": ["Intro", "intro", "Meeting"],
        "country": ["ID", "Indonesia", "SG"],
        "valuation_amount": ["1,500,000", "1500000", "2.3m"],
        "owner": ["Ana", "Ana", "Budi"],
        "last_contact_date": ["2026-04-10", "10/04/2026", "bad-date"],
    })


@pytest.fixture
def sample_followups():
    return pd.DataFrame({
        "company_name": ["Alpha Tech", "Beta Health", "Epsilon AI"],
        "due_date": ["2026-04-15", "2026-04-05", "not-a-date"],
        "owner": ["Ana", "Budi", None],
        "status": ["pending", "open", "todo"],
    })


@pytest.fixture
def sample_ctx(sample_deal_pipeline):
    return ExecutionContext(datasets={"deal_pipeline": sample_deal_pipeline.copy()})
