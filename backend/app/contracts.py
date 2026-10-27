from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)]
Interval = Literal[0, 1, 4, 12, 24]
Scalar = str | int | float | bool | None


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AskRequest(StrictModel):
    question: Question
    parent_id: str | None = Field(default=None, max_length=36)


class SQLPlan(StrictModel):
    status: Literal["ready", "clarification", "out_of_scope"]
    message: str = Field(max_length=1000)
    sql: str = Field(max_length=12000)
    title: Title


class ColumnBinding(StrictModel):
    field: str = Field(min_length=1, max_length=50)
    column: str = Field(min_length=1, max_length=100)


class Section(StrictModel):
    kind: Literal[
        "metric",
        "table",
        "bar",
        "line",
        "donut",
        "insight",
        "record_overview",
        "checklist",
        "document_review",
        "quote_simulator",
        "budget_planner",
        "comparison",
        "cash_flow",
        "activity_timeline",
        "rule_assessment",
        "relationship_graph",
        "milestone_tracker",
        "pipeline",
    ]
    title: Title
    description: str = Field(max_length=700)
    columns: list[str] = Field(max_length=12)
    x: str | None
    y: list[str] = Field(max_length=4)
    value_column: str | None
    row_index: int | None = Field(ge=0, le=499)
    format: Literal["number", "currency", "percent", "text"]
    bindings: list[ColumnBinding] = Field(default_factory=list, max_length=16)


class Presentation(StrictModel):
    title: Title
    summary: str = Field(min_length=1, max_length=1800)
    sections: list[Section] = Field(min_length=1, max_length=8)


class QueryResult(StrictModel):
    sql: str
    columns: list[str]
    rows: list[dict[str, Scalar]]
    row_count: int
    duration_ms: float
    truncated: bool
    warnings: list[str]


class ModelCost(StrictModel):
    currency: Literal["USD"] = "USD"
    estimated_usd: float | None
    model_calls: int
    input_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    output_tokens: int
    pricing_date: str = "2026-10-26"
    unavailable_reason: str | None = None


class Snapshot(StrictModel):
    title: str
    question: str
    summary: str
    result: QueryResult
    presentation: Presentation | None
    ui: list[dict]
    generated_at: datetime
    reference_date: str
    model: str
    model_cost: ModelCost | None = None
    catalog_example: str | None = None


class AnalysisOut(StrictModel):
    id: str
    parent_id: str | None
    question: str
    snapshot: Snapshot
    created_at: datetime


class AnalysisListItem(StrictModel):
    id: str
    parent_id: str | None
    question: str
    title: str
    created_at: datetime


class SaveReport(StrictModel):
    analysis_id: str = Field(min_length=36, max_length=36)
    title: Title
    refresh_interval_hours: Interval = 0


class UpdateReport(StrictModel):
    title: Title | None = None
    refresh_interval_hours: Interval | None = None
    position: int | None = Field(default=None, ge=0, le=10000)


class ReportOut(StrictModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: str
    analysis_id: str
    title: str
    question: str
    snapshot: Snapshot
    position: int
    created_at: datetime
    last_refreshed_at: datetime
    last_attempt_at: datetime | None
    refresh_interval_hours: Interval
    next_refresh_at: datetime | None
    refresh_status: str
    refresh_error: str | None


class HealthOut(StrictModel):
    status: Literal["ok", "degraded"]
    database: bool
    analytics_database: bool
    model_configured: bool
    model: str
    reference_date: str
    scheduler_enabled: bool
    booking_count: int | None
    company_count: int | None = None
    contact_count: int | None = None
    deal_count: int | None = None
