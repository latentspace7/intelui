import pytest

from app.errors import AppError
from app.sql_safety import validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM airline.bookings",
        "SELECT * FROM airline.bookings; DROP TABLE airline.customers",
        "WITH changed AS (DELETE FROM airline.bookings RETURNING *) SELECT * FROM changed",
        "SELECT * INTO copied FROM airline.bookings",
        "SELECT * FROM airline.bookings FOR UPDATE",
        "SELECT pg_sleep(10) FROM airline.bookings",
        "SELECT pg_read_file('/etc/passwd') FROM airline.bookings",
        "SELECT set_config('search_path', 'app', false) FROM airline.bookings",
        "SELECT * FROM pg_catalog.pg_authid",
        "SELECT * FROM app.reports",
        "SELECT * FROM other.airline.bookings",
        "SELECT * FROM airline.bookings b CROSS JOIN airline.customers c",
        "SELECT * FROM airline.bookings b, airline.customers c",
        "WITH RECURSIVE b AS (SELECT * FROM airline.bookings) SELECT * FROM b",
        "SELECT nonexistent FROM airline.bookings",
        "SELECT pg_catalog.sum(total_amount) FROM airline.bookings",
        "SELECT 'app.reports'::regclass FROM airline.bookings",
        "SELECT * FROM generate_series(1,1000000)",
        "SELECT * FROM airline.bookings b JOIN app.analyses a ON true",
        "SELECT 1",
    ],
)
def test_rejects_unsafe_or_invalid_queries(sql):
    with pytest.raises(AppError):
        validate_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) AS bookings FROM bookings",
        "SELECT COUNT(*) AS bookings FROM airline.bookings WHERE booked_at >= DATE '2026-04-26' AND booked_at < DATE '2026-10-27'",
        "SELECT id FROM airline.customers c WHERE EXISTS (SELECT 1 FROM airline.bookings b WHERE b.customer_id = c.id)",
        "SELECT travel_class, SUM(total_amount) AS gross FROM airline.bookings GROUP BY travel_class",
        "WITH classes AS (SELECT travel_class, SUM(total_amount) AS gross FROM airline.bookings GROUP BY travel_class) SELECT * FROM classes",
        "SELECT b.travel_class, SUM(p.amount) AS revenue FROM airline.bookings b JOIN airline.payments p ON p.booking_id=b.id WHERE p.status='Completed' GROUP BY b.travel_class",
        "SELECT DATE_TRUNC('month', scheduled_departure) AS month, COUNT(*) FILTER (WHERE status='Cancelled') AS cancellations FROM airline.flights GROUP BY 1 ORDER BY 1",
        "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status='Cancelled') / NULLIF(COUNT(*), 0), 2) AS pct FROM airline.flights",
        "SELECT origin FROM airline.flights UNION SELECT destination FROM airline.flights",
        "SELECT CAST(total_amount AS NUMERIC(12, 2)) AS amount FROM airline.bookings",
    ],
)
def test_accepts_analytical_queries(sql):
    validated = validate_sql(sql)
    assert '"airline"' in validated
