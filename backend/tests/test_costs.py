from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from app.config import settings
from app.contracts import SQLPlan
from app.costs import capture_cost, estimate_response, record_response, total_cost
from app.provider import OpenAIProvider


def response(input_tokens=12000, output_tokens=2000, cached=4000, written=7000, **kwargs):
    return SimpleNamespace(
        model="gpt-6-luna",
        service_tier="default",
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_tokens_details=SimpleNamespace(
                cached_tokens=cached, cache_write_tokens=written, **kwargs
            ),
            output_tokens_details=SimpleNamespace(reasoning_tokens=1000),
        ),
    )


@pytest.fixture(autouse=True)
def official_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "openai_base_url", "https://api.openai.com/v1")


def test_usage_pricing_counts_cache_writes_and_reasoning_only_once():
    result = estimate_response(
        response(
            cache_write_tokens_details={
                "ttl_30m_tokens": 3000,
                "ttl_12h_tokens": 4000,
            }
        )
    )
    assert result.estimated_usd == pytest.approx(0.002515)
    assert result.input_tokens == 12000
    assert result.output_tokens == 2000
    assert estimate_response(response()).estimated_usd == pytest.approx(0.002015)


@pytest.mark.parametrize("tier,multiplier", [("default", 1), ("flex", 0.5), ("priority", 2)])
def test_tier_and_long_context_prices(tier, multiplier):
    item = response(input_tokens=300000, cached=0, written=0)
    item.service_tier = tier
    assert estimate_response(item).estimated_usd == pytest.approx(0.0615 * multiplier)


@pytest.mark.parametrize("kind", ["model", "endpoint", "tier", "usage", "invalid_counts"])
def test_unavailable_cost_is_never_reported_as_zero(kind, monkeypatch):
    item = response()
    if kind == "model":
        item.model = "another-model"
    elif kind == "endpoint":
        monkeypatch.setattr(settings, "openai_base_url", "https://example.com/v1")
    elif kind == "tier":
        item.service_tier = "scale"
    elif kind == "usage":
        item.usage = None
    else:
        item.usage.input_tokens = 1
    cost = total_cost([estimate_response(item)])
    assert cost.estimated_usd is None
    assert cost.unavailable_reason


def test_parallel_runs_keep_costs_separate_and_reset_between_runs():
    barrier = Barrier(2)

    def run(count):
        with capture_cost() as calls:
            barrier.wait(timeout=5)
            for _ in range(count):
                record_response(response())
            return total_cost(calls)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, [1, 3]))
    assert [result.model_calls for result in results] == [1, 3]
    assert results[1].estimated_usd == pytest.approx(3 * results[0].estimated_usd)
    with capture_cost() as calls:
        assert total_cost(calls).estimated_usd == 0


def test_provider_records_actual_response_usage(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test-only"))
    monkeypatch.setattr(settings, "ai_provider", "openai")
    item = response()
    item.output_parsed = SQLPlan(status="ready", message="", sql="SELECT 1", title="Test")
    client = MagicMock()
    client.__enter__.return_value.responses.parse.return_value = item
    monkeypatch.setattr("app.provider.OpenAI", lambda **kwargs: client)
    with capture_cost() as calls:
        assert OpenAIProvider()._parse("test", {}, SQLPlan) == item.output_parsed
    assert total_cost(calls).model_calls == 1
    assert total_cost(calls).estimated_usd == pytest.approx(0.002015)
