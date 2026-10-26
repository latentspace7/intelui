import logging
from datetime import timedelta
from threading import Event

from sqlalchemy import select

from app.analytics import create_snapshot
from app.config import settings
from app.costs import capture_cost, total_cost
from app.db import SessionLocal
from app.errors import AppError
from app.models import Report, utcnow
from app.provider import AnalyticsProvider, get_provider

logger = logging.getLogger(__name__)


def refresh_report(report_id: str, provider: AnalyticsProvider, scheduled: bool = False) -> Report:
    with SessionLocal.begin() as session:
        query = select(Report).where(Report.id == report_id)
        if scheduled:
            query = query.where(
                Report.next_refresh_at <= utcnow(), Report.refresh_interval_hours > 0
            )
        report = session.scalar(query.with_for_update(skip_locked=True))
        if report is None:
            exists = session.get(Report, report_id)
            if exists is None:
                raise AppError("report_not_found", "The saved report was not found.", 404)
            raise AppError(
                "refresh_in_progress", "This report is already refreshing or is no longer due.", 409
            )
        report.last_attempt_at = utcnow()
        try:
            with capture_cost() as calls:
                snapshot = create_snapshot(
                    report.question,
                    report.snapshot["result"]["sql"],
                    provider,
                    report.title,
                    reference_date=report.snapshot["reference_date"],
                )
                snapshot.model_cost = total_cost(calls)
            report.snapshot = snapshot.model_dump(mode="json")
            report.last_refreshed_at = utcnow()
            report.refresh_status = "success"
            report.refresh_error = None
        except AppError as exc:
            report.refresh_status = "error"
            report.refresh_error = exc.message[:500]
        except Exception:
            logger.exception("Report refresh failed for %s", report.id)
            report.refresh_status = "error"
            report.refresh_error = (
                "The report could not be refreshed. The last successful snapshot is preserved."
            )
        if report.refresh_interval_hours:
            delay = (
                timedelta(minutes=5)
                if report.refresh_status == "error"
                else timedelta(hours=report.refresh_interval_hours)
            )
            report.next_refresh_at = utcnow() + delay
        else:
            report.next_refresh_at = None
        session.flush()
        session.expunge(report)
    return report


def refresh_due(provider: AnalyticsProvider | None = None) -> int:
    with SessionLocal() as session:
        ids = session.scalars(
            select(Report.id)
            .where(Report.next_refresh_at <= utcnow(), Report.refresh_interval_hours > 0)
            .order_by(Report.next_refresh_at)
            .limit(20)
        ).all()
    count = 0
    for report_id in ids:
        try:
            refresh_report(report_id, provider or get_provider(), scheduled=True)
            count += 1
        except AppError as exc:
            if exc.status not in (404, 409):
                raise
    return count


def scheduler_loop(stop: Event):
    while not stop.is_set():
        try:
            refresh_due()
        except Exception:
            logger.exception("Refresh scheduler could not inspect due reports")
        stop.wait(settings.scheduler_poll_seconds)
