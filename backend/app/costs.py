from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal
from typing import Any

from app.config import settings
from app.contracts import ModelCost

_calls: ContextVar[list[ModelCost] | None] = ContextVar("model_cost_calls", default=None)


def estimate_response(response: Any) -> ModelCost:
    usage = getattr(response, "usage", None)
    details = getattr(usage, "input_tokens_details", None)
    input_tokens = getattr(usage, "input_tokens", 0) or 0
    output_tokens = getattr(usage, "output_tokens", 0) or 0
    cached = getattr(details, "cached_tokens", 0) or 0
    written = getattr(details, "cache_write_tokens", 0) or 0
    cost = ModelCost(
        estimated_usd=None,
        model_calls=1,
        input_tokens=input_tokens,
        cached_input_tokens=cached,
        cache_write_tokens=written,
        output_tokens=output_tokens,
    )
    tier = getattr(response, "service_tier", None)
    if usage is None:
        cost.unavailable_reason = "The provider did not return token usage."
    elif (
        settings.openai_base_url.rstrip("/") != "https://api.openai.com/v1"
        or getattr(response, "model", None) != "gpt-6-luna"
        or tier not in ("default", "flex", "priority", "fast")
    ):
        cost.unavailable_reason = (
            "Pricing is not configured for this model, endpoint, or service tier."
        )
    elif min(input_tokens, output_tokens, cached, written) < 0 or cached + written > input_tokens:
        cost.unavailable_reason = "The provider returned inconsistent token usage."
    else:
        write_details = getattr(details, "cache_write_tokens_details", None)
        if hasattr(write_details, "model_dump"):
            write_details = write_details.model_dump()
        write_30m = write_details.get("ttl_30m_tokens", 0) if write_details else written
        write_12h = write_details.get("ttl_12h_tokens", 0) if write_details else 0
        if min(write_30m, write_12h) < 0 or write_30m + write_12h != written:
            cost.unavailable_reason = "The provider returned inconsistent cache-write usage."
            return cost
        input_rate = Decimal("0.10") * (2 if input_tokens > 272000 else 1)
        output_rate = Decimal("0.50") * (Decimal("1.5") if input_tokens > 272000 else 1)
        tier_factor = {"default": 1, "flex": Decimal("0.5"), "priority": 2, "fast": 2}[tier]
        weighted_input = (
            input_tokens
            - cached
            - written
            + cached * Decimal("0.1")
            + write_30m * Decimal("1.25")
            + write_12h * Decimal("2.5")
        )
        cost.estimated_usd = float(
            (weighted_input * input_rate + output_tokens * output_rate) * tier_factor / 1000000
        )
    return cost


def record_response(response: Any) -> None:
    calls = _calls.get()
    if calls is not None:
        calls.append(estimate_response(response))


@contextmanager
def capture_cost() -> Iterator[list[ModelCost]]:
    calls: list[ModelCost] = []
    token = _calls.set(calls)
    try:
        yield calls
    finally:
        _calls.reset(token)


def total_cost(calls: list[ModelCost]) -> ModelCost:
    reason = next((call.unavailable_reason for call in calls if call.estimated_usd is None), None)
    return ModelCost(
        estimated_usd=(
            None
            if any(call.estimated_usd is None for call in calls)
            else float(sum(Decimal(str(call.estimated_usd)) for call in calls))
        ),
        model_calls=len(calls),
        input_tokens=sum(call.input_tokens for call in calls),
        cached_input_tokens=sum(call.cached_input_tokens for call in calls),
        cache_write_tokens=sum(call.cache_write_tokens for call in calls),
        output_tokens=sum(call.output_tokens for call in calls),
        unavailable_reason=reason,
    )
