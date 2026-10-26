import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from threading import Event, Thread
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.analytics import analyze
from app.config import settings
from app.contracts import (
    AnalysisListItem,
    AnalysisOut,
    AskRequest,
    HealthOut,
    ReportOut,
    SaveReport,
    UpdateReport,
)
from app.db import analytics_engine, engine, get_session
from app.errors import AppError
from app.models import Analysis, Booking, Report, utcnow
from app.provider import AnalyticsProvider, get_provider
from app.reports import refresh_report, scheduler_loop

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = Event()
    worker = None
    if settings.scheduler_enabled:
        worker = Thread(target=scheduler_loop, args=(stop,), name="report-scheduler", daemon=True)
        worker.start()
    yield
    stop.set()
    if worker:
        worker.join(timeout=2)
    engine.dispose()
    analytics_engine.dispose()


app = FastAPI(title="AeroVista Intelligence", version="0.1.0", lifespan=lifespan)
DB = Annotated[Session, Depends(get_session)]
Provider = Annotated[AnalyticsProvider, Depends(get_provider)]


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        size = 0
        messages = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 16384:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "request_too_large",
                            "message": "Keep requests under 16 KB.",
                        }
                    },
                )
                return await response(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay():
            if messages:
                return messages.pop(0)
            return await receive()

        return await self.app(scope, replay, send)


app.add_middleware(BodyLimitMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}}
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "invalid_request",
                "message": "Check the question, report title, and refresh interval.",
            }
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    if getattr(getattr(exc, "orig", None), "sqlstate", None) == "55P03":
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "refresh_in_progress",
                    "message": "This report is refreshing. Please retry when it finishes.",
                }
            },
        )
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "database_unavailable",
                "message": "The database is unavailable. Start PostgreSQL and run migrations.",
            }
        },
    )


@app.get("/api/health", response_model=HealthOut)
def health():
    database = False
    analytics = False
    bookings = None
    try:
        with engine.connect() as connection:
            bookings = connection.scalar(select(func.count()).select_from(Booking))
            connection.execute(select(Report.id).limit(1))
            database = True
        with analytics_engine.connect() as connection:
            connection.execute(text("SELECT id FROM airline.bookings LIMIT 1"))
            analytics = True
    except SQLAlchemyError:
        pass
    return HealthOut(
        status="ok" if database and analytics else "degraded",
        database=database,
        analytics_database=analytics,
        model_configured=bool(settings.openai_api_key.get_secret_value()),
        model=settings.openai_model,
        reference_date=str(settings.demo_reference_date),
        scheduler_enabled=settings.scheduler_enabled,
        booking_count=bookings,
    )


def analysis_out(analysis: Analysis) -> AnalysisOut:
    return AnalysisOut(
        id=analysis.id,
        parent_id=analysis.parent_id,
        question=analysis.question,
        snapshot=analysis.snapshot,
        created_at=analysis.created_at,
    )


@app.post("/api/analyses", response_model=AnalysisOut, status_code=201)
def ask(payload: AskRequest, session: DB, provider: Provider):
    return analysis_out(analyze(payload, session, provider))


@app.get("/api/analyses", response_model=list[AnalysisListItem])
def list_analyses(session: DB):
    return [
        AnalysisListItem(
            id=item.id,
            parent_id=item.parent_id,
            question=item.question,
            title=item.snapshot["title"],
            created_at=item.created_at,
        )
        for item in session.scalars(
            select(Analysis).order_by(Analysis.created_at.desc()).limit(100)
        )
    ]


@app.get("/api/analyses/{analysis_id}", response_model=AnalysisOut)
def read_analysis(analysis_id: str, session: DB):
    analysis = session.get(Analysis, analysis_id)
    if analysis is None:
        raise AppError("analysis_not_found", "The analysis was not found.", 404)
    return analysis_out(analysis)


@app.get("/api/analyses/{analysis_id}/thread", response_model=list[AnalysisOut])
def read_thread(analysis_id: str, session: DB):
    chain = []
    current = analysis_id
    for _ in range(50):
        analysis = session.get(Analysis, current)
        if analysis is None:
            raise AppError("analysis_not_found", "The analysis was not found.", 404)
        chain.append(analysis_out(analysis))
        if not analysis.parent_id:
            break
        current = analysis.parent_id
    return list(reversed(chain))


@app.get("/api/reports", response_model=list[ReportOut])
def list_reports(session: DB):
    return session.scalars(select(Report).order_by(Report.position, Report.created_at)).all()


@app.get("/api/reports/{report_id}", response_model=ReportOut)
def read_report(report_id: str, session: DB):
    report = session.get(Report, report_id)
    if report is None:
        raise AppError("report_not_found", "The saved report was not found.", 404)
    return report


@app.post("/api/reports", response_model=ReportOut, status_code=201)
def save_report(payload: SaveReport, session: DB):
    analysis = session.get(Analysis, payload.analysis_id)
    if analysis is None:
        raise AppError("analysis_not_found", "Generate an analysis before saving it.", 404)
    max_position = session.scalar(select(func.max(Report.position)))
    report = Report(
        analysis_id=analysis.id,
        title=payload.title,
        question=analysis.question,
        snapshot=analysis.snapshot,
        position=(max_position or 0) + 1,
        refresh_interval_hours=payload.refresh_interval_hours,
        last_refreshed_at=analysis.created_at,
        next_refresh_at=utcnow() + timedelta(hours=payload.refresh_interval_hours)
        if payload.refresh_interval_hours
        else None,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


@app.patch("/api/reports/{report_id}", response_model=ReportOut)
def update_report(report_id: str, payload: UpdateReport, session: DB):
    report = session.scalar(
        select(Report).where(Report.id == report_id).with_for_update(nowait=True)
    )
    if report is None:
        raise AppError("report_not_found", "The saved report was not found.", 404)
    if payload.title is not None:
        report.title = payload.title
    if payload.position is not None:
        report.position = payload.position
    if payload.refresh_interval_hours is not None:
        report.refresh_interval_hours = payload.refresh_interval_hours
        report.next_refresh_at = (
            utcnow() + timedelta(hours=payload.refresh_interval_hours)
            if payload.refresh_interval_hours
            else None
        )
    session.commit()
    return report


@app.delete("/api/reports/{report_id}", status_code=204)
def delete_report(report_id: str, session: DB):
    report = session.scalar(
        select(Report).where(Report.id == report_id).with_for_update(nowait=True)
    )
    if report is None:
        raise AppError("report_not_found", "The saved report was not found.", 404)
    session.delete(report)
    session.commit()
    return Response(status_code=204)


@app.post("/api/reports/{report_id}/refresh", response_model=ReportOut)
def manual_refresh(report_id: str, provider: Provider):
    return refresh_report(report_id, provider)
