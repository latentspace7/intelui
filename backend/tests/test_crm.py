import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DBAPIError

from app.config import settings
from app.contracts import ColumnBinding, QueryResult, Section
from app.crm_catalog import CRM_COMPONENTS, EXAMPLES, bind_component
from app.crm_models import CRM_TABLES
from app.crm_seed import build_crm_dataset, seed_crm
from app.db import SessionLocal, analytics_engine
from app.errors import AppError
from app.main import app
from app.models import Analysis, Report
from app.provider import get_provider
from app.sql_safety import validate_sql


def test_synthetic_batches_are_deterministic_connected_and_disjoint():
    first = build_crm_dataset(date(2026, 10, 26))
    assert first == build_crm_dataset(date(2026, 10, 26))
    second = build_crm_dataset(date(2026, 10, 26), 1)
    assert len(first["companies"]) == 24
    assert len(first["deals"]) == 96
    for name, table in CRM_TABLES.items():
        assert not {row["id"] for row in first[name]} & {row["id"] for row in second[name]}
        for column in table.columns:
            for foreign_key in column.foreign_keys:
                target = foreign_key.column.table.name
                ids = {row["id"] for row in first[target]}
                assert all(row[column.name] in ids for row in first[name])
    for batch in (-1, 100):
        with pytest.raises(ValueError):
            build_crm_dataset(date(2026, 10, 26), batch)


@pytest.mark.parametrize("kind", EXAMPLES)
def test_catalog_queries_pass_sql_validation(kind):
    assert '"crm"' in validate_sql(EXAMPLES[kind][1])


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM crm.deals",
        "SELECT * FROM crm.secrets",
        "SELECT * FROM crm.deals d JOIN app.reports r ON true",
        "SELECT pg_sleep(5) FROM crm.companies",
    ],
)
def test_crm_sql_cannot_escape_readonly_catalog(sql):
    with pytest.raises(AppError):
        validate_sql(sql)


def quote_section():
    fields = CRM_COMPONENTS["quote_simulator"].fields
    return Section(
        kind="quote_simulator",
        title="Quote",
        description="Synthetic quote",
        columns=[],
        x=None,
        y=[],
        value_column=None,
        row_index=None,
        format="currency",
        bindings=[ColumnBinding(field=field, column=field) for field in fields],
    )


def quote_result():
    row = dict(
        id=1, label="Example", unit_price=35, quantity=11, months=12, discount=0, setup_fee=250
    )
    return QueryResult(
        sql="",
        columns=list(row),
        rows=[row],
        row_count=1,
        duration_ms=1,
        truncated=False,
        warnings=[],
    )


def test_component_binding_rejects_missing_duplicate_and_fabricated_columns():
    section = quote_section()
    data = quote_result()
    assert bind_component(section, data)["rows"][0]["unit_price"] == 35
    assert (
        bind_component(section, data, reference_date="2026-09-01")["referenceDate"] == "2026-09-01"
    )
    section.bindings[0].column = "invented_id"
    with pytest.raises(AppError):
        bind_component(section, data)
    section = quote_section()
    section.bindings.append(section.bindings[0])
    with pytest.raises(AppError):
        bind_component(section, data)
    section.bindings = section.bindings[:2]
    with pytest.raises(AppError):
        bind_component(section, data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("unit_price", "free"),
        ("unit_price", -1),
        ("quantity", 0),
        ("quantity", 1.5),
        ("months", 121),
        ("discount", 101),
        ("id", True),
    ],
)
def test_quote_binding_rejects_invalid_calculation_inputs(field, value):
    data = quote_result()
    data.rows[0][field] = value
    with pytest.raises(AppError):
        bind_component(quote_section(), data)


integration = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="Requires migrated CRM PostgreSQL"
)


@pytest.fixture
def crm_client(monkeypatch):
    monkeypatch.setattr(settings, "scheduler_enabled", False)

    class NoModel:
        def present(self, *args):
            raise AssertionError("Catalog examples must not call a model")

    app.dependency_overrides[get_provider] = NoModel
    with SessionLocal() as session:
        before = set(session.scalars(select(Analysis.id)))
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    with SessionLocal.begin() as session:
        created = set(session.scalars(select(Analysis.id))) - before
        if created:
            session.execute(delete(Report).where(Report.analysis_id.in_(created)))
            session.execute(delete(Analysis).where(Analysis.id.in_(created)))


@integration
def test_all_catalog_examples_read_database_and_survive_save_and_refresh(crm_client):
    items = crm_client.get("/api/catalog").json()
    assert len(items) == 12
    for item in items:
        response = crm_client.get(f"/api/catalog/{item['id']}")
        assert response.status_code == 200, response.text
        snapshot = response.json()
        assert snapshot["result"]["rows"]
        component = snapshot["ui"][1]["updateComponents"]["components"][1]
        assert component["component"] == CRM_COMPONENTS[item["id"]].name
        assert len(component["rows"]) == snapshot["result"]["row_count"]
    assert crm_client.get("/api/catalog/unknown").status_code == 404
    analysis = crm_client.post("/api/catalog/pipeline/analyses").json()
    saved = crm_client.post(
        "/api/reports",
        json={
            "analysis_id": analysis["id"],
            "title": "CRM integration",
            "refresh_interval_hours": 0,
        },
    ).json()
    deals = CRM_TABLES["deals"]
    with SessionLocal.begin() as session:
        previous = session.scalar(select(deals.c.amount).where(deals.c.id == 1))
        session.execute(deals.update().where(deals.c.id == 1).values(amount=previous + 123))
    try:
        response = crm_client.post(f"/api/reports/{saved['id']}/refresh")
        assert response.status_code == 200
        refreshed = response.json()
        assert refreshed["refresh_status"] == "success", refreshed["refresh_error"]
        assert refreshed["snapshot"]["catalog_example"] == "pipeline"
        rows = refreshed["snapshot"]["result"]["rows"]
        assert next(row["amount"] for row in rows if row["id"] == 1) == float(previous + 123)
        assert refreshed["snapshot"]["model_cost"]["model_calls"] == 0
    finally:
        with SessionLocal.begin() as session:
            session.execute(deals.update().where(deals.c.id == 1).values(amount=previous))


@integration
def test_task_edits_are_persisted_audited_and_reject_stale_writes(crm_client):
    table = CRM_TABLES["tasks"]
    audit = CRM_TABLES["audit_events"]
    with SessionLocal.begin() as session:
        row = dict(session.execute(select(table).where(table.c.id == 1)).mappings().one())
        row.update(id=900001, title="Temporary test task", status="Outstanding")
        session.execute(table.insert().values(row))
    try:
        payload = {
            "expected_status": "Outstanding",
            "status": "Complete",
            "expected_label": "Temporary test task",
        }
        assert (
            crm_client.patch(
                "/api/crm/tasks/900001", json={**payload, "expected_label": "Wrong record"}
            ).status_code
            == 409
        )
        response = crm_client.patch("/api/crm/tasks/900001", json=payload)
        assert response.status_code == 200, response.text
        assert crm_client.patch("/api/crm/tasks/900001", json=payload).status_code == 409
        assert (
            crm_client.patch(
                "/api/crm/tasks/900001",
                json={
                    "expected_status": "Complete",
                    "status": "Approved",
                    "expected_label": "Temporary test task",
                },
            ).status_code
            == 422
        )
        with SessionLocal() as session:
            assert session.scalar(select(table.c.status).where(table.c.id == 900001)) == "Complete"
            event = (
                session.execute(
                    select(audit).where(audit.c.entity == "tasks", audit.c.record_id == 900001)
                )
                .mappings()
                .one()
            )
            assert event["previous_status"] == "Outstanding" and event["new_status"] == "Complete"
    finally:
        with SessionLocal.begin() as session:
            session.execute(
                audit.delete().where(audit.c.entity == "tasks", audit.c.record_id == 900001)
            )
            session.execute(table.delete().where(table.c.id == 900001))


@integration
def test_document_mismatch_cannot_be_accepted(crm_client):
    table = CRM_TABLES["document_fields"]
    with SessionLocal.begin() as session:
        row = dict(session.execute(select(table).where(table.c.id == 1)).mappings().one())
        row.update(id=900001, declared_value="100", extracted_value="200", review_status="Pending")
        session.execute(table.insert().values(row))
    try:
        response = crm_client.patch(
            "/api/crm/document_fields/900001",
            json={
                "expected_status": "Pending",
                "status": "Accepted",
                "expected_label": "Company profile · Northstar Labs",
                "expected_field": "Company",
            },
        )
        assert response.status_code == 422
        response = crm_client.patch(
            "/api/crm/document_fields/900001",
            json={
                "expected_status": "Pending",
                "status": "Needs correction",
                "expected_label": "Company profile · Northstar Labs",
                "expected_field": "Company",
            },
        )
        assert response.status_code == 200
    finally:
        with SessionLocal.begin() as session:
            session.execute(
                CRM_TABLES["audit_events"]
                .delete()
                .where(
                    CRM_TABLES["audit_events"].c.entity == "document_fields",
                    CRM_TABLES["audit_events"].c.record_id == 900001,
                )
            )
            session.execute(table.delete().where(table.c.id == 900001))


@integration
def test_crm_reseed_preserves_changes_and_reader_cannot_write():
    companies = CRM_TABLES["companies"]
    with SessionLocal.begin() as session:
        original = session.scalar(select(companies.c.description).where(companies.c.id == 1))
        session.execute(
            companies.update().where(companies.c.id == 1).values(description="Preserve this edit")
        )
    try:
        assert not any(seed_crm().values())
        with SessionLocal() as session:
            assert (
                session.scalar(select(companies.c.description).where(companies.c.id == 1))
                == "Preserve this edit"
            )
        with pytest.raises(DBAPIError), analytics_engine.begin() as connection:
            connection.execute(text("UPDATE crm.tasks SET status='Complete' WHERE id=1"))
    finally:
        with SessionLocal.begin() as session:
            session.execute(
                companies.update().where(companies.c.id == 1).values(description=original)
            )
