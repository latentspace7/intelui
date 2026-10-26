import os
from datetime import timedelta
from threading import Event, Thread

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError

from app.config import settings
from app.costs import record_response
from app.db import SessionLocal, analytics_engine
from app.errors import AppError
from app.executor import execute_query
from app.main import app
from app.models import Analysis, Booking, Report, utcnow
from app.provider import get_provider
from app.reports import refresh_due, refresh_report
from tests.helpers import FakeProvider
from tests.test_costs import response as usage_response

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1", reason="Set RUN_DB_TESTS=1 for PostgreSQL tests"
    ),
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "scheduler_enabled", False)
    provider = FakeProvider()
    app.dependency_overrides[get_provider] = lambda: provider
    with SessionLocal() as session:
        before = set(session.scalars(select(Analysis.id)))
    with TestClient(app) as test_client:
        yield test_client, provider
    app.dependency_overrides.clear()
    with SessionLocal.begin() as session:
        new_ids = set(session.scalars(select(Analysis.id))) - before
        if new_ids:
            session.execute(delete(Report).where(Report.analysis_id.in_(new_ids)))
            session.execute(delete(Analysis).where(Analysis.id.in_(new_ids)))


def create_report(client):
    analysis = client.post("/api/analyses", json={"question": "How many bookings are there?"})
    assert analysis.status_code == 201, analysis.text
    saved = client.post(
        "/api/reports",
        json={
            "analysis_id": analysis.json()["id"],
            "title": "Integration test",
            "refresh_interval_hours": 4,
        },
    )
    assert saved.status_code == 201
    return saved.json()


def test_crud_persistence_and_manual_refresh_reads_new_data(client):
    api, provider = client
    report = create_report(api)
    report_id = report["id"]
    assert report["snapshot"]["result"]["rows"][0]["bookings"] == 100
    with SessionLocal() as session:
        assert session.get(Report, report_id).title == "Integration test"
    assert (
        api.patch(
            f"/api/reports/{report_id}", json={"title": "Renamed", "refresh_interval_hours": 12}
        ).json()["title"]
        == "Renamed"
    )
    with SessionLocal.begin() as session:
        booking = session.get(Booking, 1)
        added = Booking(
            id=900001,
            customer_id=booking.customer_id,
            flight_id=booking.flight_id,
            booking_reference="TEST900001",
            booked_at=booking.booked_at,
            travel_class=booking.travel_class,
            ticket_status=booking.ticket_status,
            total_amount=booking.total_amount,
        )
        session.add(added)
    try:
        refreshed = api.post(f"/api/reports/{report_id}/refresh")
        assert refreshed.status_code == 200
        assert refreshed.json()["snapshot"]["result"]["rows"][0]["bookings"] == 101
        assert refreshed.json()["last_refreshed_at"] != report["last_refreshed_at"]
    finally:
        with SessionLocal.begin() as session:
            session.execute(delete(Booking).where(Booking.id == 900001))
    provider.fail = True
    failed = api.post(f"/api/reports/{report_id}/refresh").json()
    assert failed["refresh_status"] == "error"
    assert failed["snapshot"]["result"]["rows"][0]["bookings"] == 101
    assert failed["refresh_error"]
    assert api.delete(f"/api/reports/{report_id}").status_code == 204
    assert api.get(f"/api/reports/{report_id}").status_code == 404


def test_readonly_role_and_row_limit(monkeypatch):
    for sql in [
        "DELETE FROM airline.bookings",
        "SELECT * FROM app.reports",
        "CREATE TEMP TABLE unsafe (id integer)",
    ]:
        with pytest.raises(DBAPIError), analytics_engine.begin() as conn:
            conn.execute(text(sql))
    monkeypatch.setattr(settings, "max_result_rows", 5)
    result = execute_query("SELECT id FROM airline.bookings ORDER BY id")
    assert result.row_count == 5 and result.truncated and result.warnings


def test_scheduled_refresh_and_no_duplicate_workers(client):
    api, provider = client
    saved = create_report(api)
    with SessionLocal.begin() as session:
        session.get(Report, saved["id"]).next_refresh_at = utcnow() - timedelta(hours=1)
    assert refresh_due(provider) == 1
    assert refresh_due(provider) == 0
    entered, release = Event(), Event()
    failures = []

    class BlockingProvider(FakeProvider):
        def present(self, question, result):
            entered.set()
            release.wait(timeout=10)
            return super().present(question, result)

    def run():
        try:
            refresh_report(saved["id"], BlockingProvider())
        except Exception as exc:
            failures.append(exc)

    worker = Thread(target=run)
    worker.start()
    assert entered.wait(timeout=5)
    try:
        with pytest.raises(AppError) as exc:
            refresh_report(saved["id"], provider)
        assert exc.value.code == "refresh_in_progress"
    finally:
        release.set()
        worker.join(timeout=10)
    assert not failures


def test_bounded_sql_repair_and_followup_context(client):
    api, provider = client
    original = provider.plan
    seen = []

    def repair_plan(question, context, repair=None):
        seen.append((context, repair))
        plan = original(question, context, repair)
        if repair is None and len(seen) == 1:
            plan.sql = "SELECT missing_column FROM airline.bookings"
        return plan

    provider.plan = repair_plan
    first = api.post("/api/analyses", json={"question": "Count bookings"})
    assert first.status_code == 201
    assert len(seen) == 2 and seen[1][1]
    second = api.post(
        "/api/analyses", json={"question": "And the total again?", "parent_id": first.json()["id"]}
    )
    assert second.status_code == 201
    assert seen[-1][0][0]["question"] == "Count bookings"
    assert len(api.get(f"/api/analyses/{second.json()['id']}/thread").json()) == 2


def test_seed_rerun_is_safe():
    from app.seed import seed

    assert seed() == {"already_seeded": 1}
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Booking)) == 100


def test_snapshot_cost_includes_repair_and_refresh_replaces_cost(client, monkeypatch):
    api, provider = client
    monkeypatch.setattr(settings, "openai_base_url", "https://api.openai.com/v1")
    original_plan, original_present = provider.plan, provider.present

    def plan(question, context, repair=None):
        record_response(usage_response())
        result = original_plan(question, context, repair)
        if repair is None:
            result.sql = "SELECT missing_column FROM airline.bookings"
        return result

    def present(question, result):
        record_response(usage_response())
        return original_present(question, result)

    monkeypatch.setattr(provider, "plan", plan)
    monkeypatch.setattr(provider, "present", present)
    report = create_report(api)
    cost = report["snapshot"]["model_cost"]
    assert cost["model_calls"] == 3
    assert cost["estimated_usd"] == pytest.approx(0.006045)
    for _ in range(2):
        refreshed = api.post(f"/api/reports/{report['id']}/refresh").json()
        assert refreshed["snapshot"]["model_cost"]["model_calls"] == 1
        assert refreshed["snapshot"]["model_cost"]["estimated_usd"] == pytest.approx(0.002015)
    assert provider.plans == 2
    original = api.get(f"/api/analyses/{report['analysis_id']}/thread").json()[0]
    assert original["snapshot"]["model_cost"] == cost
