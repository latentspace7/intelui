from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import AnalysisOut, Snapshot, StrictModel
from app.crm_catalog import CRM_COMPONENTS, EXAMPLES, example_snapshot
from app.crm_models import CRM_TABLES
from app.db import get_session
from app.errors import AppError
from app.models import Analysis, utcnow

router = APIRouter(prefix="/api")
DB = Annotated[Session, Depends(get_session)]


class StatusUpdate(StrictModel):
    expected_status: str = Field(min_length=1, max_length=30)
    status: str = Field(min_length=1, max_length=30)
    expected_label: str = Field(min_length=1, max_length=150)
    expected_field: str | None = Field(default=None, max_length=80)


@router.get("/catalog")
def list_catalog():
    return [
        {
            "id": kind,
            "title": spec.title,
            "description": spec.description,
            "prompt": EXAMPLES[kind][0],
        }
        for kind, spec in CRM_COMPONENTS.items()
    ]


@router.get("/catalog/{kind}", response_model=Snapshot)
def preview_catalog(kind: str):
    return example_snapshot(kind)


@router.post("/catalog/{kind}/analyses", response_model=AnalysisOut, status_code=201)
def open_catalog_analysis(kind: str, session: DB):
    snapshot = example_snapshot(kind)
    analysis = Analysis(question=snapshot.question, snapshot=snapshot.model_dump(mode="json"))
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return AnalysisOut(
        id=analysis.id,
        parent_id=None,
        question=analysis.question,
        snapshot=analysis.snapshot,
        created_at=analysis.created_at,
    )


@router.patch("/crm/{entity}/{record_id}")
def update_status(
    entity: Literal["tasks", "document_fields"], record_id: int, payload: StatusUpdate, session: DB
):
    column = "status" if entity == "tasks" else "review_status"
    allowed = (
        {"Outstanding", "In progress", "Complete"}
        if entity == "tasks"
        else {"Pending", "Accepted", "Needs correction"}
    )
    if payload.status not in allowed or payload.expected_status not in allowed:
        raise AppError("invalid_status", "Choose a supported status for this record.", 422)
    table = CRM_TABLES[entity]
    row = (
        session.execute(select(table).where(table.c.id == record_id).with_for_update())
        .mappings()
        .first()
    )
    if row is None:
        raise AppError("record_not_found", "The record was not found.", 404)
    if entity == "tasks":
        identity_matches = row["title"] == payload.expected_label
    else:
        documents = CRM_TABLES["documents"]
        title = session.scalar(
            select(documents.c.title).where(documents.c.id == row["document_id"])
        )
        identity_matches = (
            title == payload.expected_label and row["field_name"] == payload.expected_field
        )
    if not identity_matches:
        raise AppError(
            "record_mismatch",
            "The report does not match this record. Reload the source data before saving.",
            409,
        )
    if row[column] != payload.expected_status:
        raise AppError(
            "record_changed",
            "This record changed since it was loaded. Reload the data before saving.",
            409,
        )
    if payload.status == "Accepted" and row["declared_value"] != row["extracted_value"]:
        raise AppError(
            "field_mismatch",
            "The values differ. Mark the field as needing correction instead.",
            422,
        )
    if row[column] != payload.status:
        session.execute(
            table.update().where(table.c.id == record_id).values({column: payload.status})
        )
        session.execute(
            CRM_TABLES["audit_events"]
            .insert()
            .values(
                entity=entity,
                record_id=record_id,
                previous_status=row[column],
                new_status=payload.status,
                actor="Local demo user",
                occurred_at=utcnow(),
            )
        )
    session.commit()
    return {"id": record_id, "status": payload.status}
