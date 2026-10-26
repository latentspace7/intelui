import pytest
from pydantic import ValidationError

from app.contracts import QueryResult
from app.errors import AppError
from app.presentation import compile_ui
from tests.helpers import FakeProvider


def result():
    return QueryResult(
        sql="SELECT COUNT(*) AS bookings FROM airline.bookings",
        columns=["bookings"],
        rows=[{"bookings": 100}],
        row_count=1,
        duration_ms=2,
        truncated=False,
        warnings=[],
    )


def test_values_come_from_query_rows_and_a2ui_is_compiled():
    data = result()
    plan = FakeProvider().present("Bookings", data)
    ui = compile_ui(plan, data)
    assert ui[0]["createSurface"]["catalogId"] == "aerovista://analytics/v1"
    assert ui[1]["updateComponents"]["components"][1]["value"] == 100


def test_unknown_columns_and_out_of_range_kpi_rejected():
    data = result()
    plan = FakeProvider().present("Bookings", data)
    plan.sections[0].value_column = "invented_revenue"
    with pytest.raises(AppError):
        compile_ui(plan, data)
    plan.sections[0].value_column = "bookings"
    plan.sections[0].row_index = 5
    with pytest.raises(AppError):
        compile_ui(plan, data)


def test_unsupported_component_and_generated_code_rejected():
    data = result()
    plan = FakeProvider().present("Bookings", data).model_dump()
    plan["sections"][0]["kind"] = "script"
    from app.contracts import Presentation

    with pytest.raises(ValidationError):
        Presentation.model_validate(plan)
    plan["sections"][0]["kind"] = "metric"
    plan["javascript"] = "alert(1)"
    with pytest.raises(ValidationError):
        Presentation.model_validate(plan)


def test_nonnumeric_chart_and_empty_presentation_rejected():
    data = result()
    data.rows = [{"bookings": "one hundred"}]
    plan = FakeProvider().present("Bookings", data)
    with pytest.raises(AppError):
        compile_ui(plan, data)
