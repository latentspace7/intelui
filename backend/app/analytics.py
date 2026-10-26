from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.contracts import AskRequest, Snapshot
from app.costs import capture_cost, total_cost
from app.errors import AppError
from app.executor import execute_query
from app.models import Analysis, utcnow
from app.presentation import compile_ui
from app.provider import AnalyticsProvider


def create_snapshot(
    question: str,
    sql: str,
    provider: AnalyticsProvider,
    title: str = "Analysis",
    reference_date: str | None = None,
) -> Snapshot:
    result = execute_query(sql)
    plan = None
    ui = []
    summary = "No matching records were found. Try a broader time period or different filters."
    if result.rows:
        plan = provider.present(question, result)
        ui = compile_ui(plan, result)
        summary = plan.summary
        title = plan.title
    return Snapshot(
        title=title,
        question=question,
        summary=summary,
        result=result,
        presentation=plan,
        ui=ui,
        generated_at=utcnow(),
        reference_date=reference_date or str(settings.demo_reference_date),
        model=settings.openai_model,
    )


def analyze(request: AskRequest, session: Session, provider: AnalyticsProvider) -> Analysis:
    context = []
    parent_id = request.parent_id
    for _ in range(4):
        if not parent_id:
            break
        previous = session.scalar(select(Analysis).where(Analysis.id == parent_id))
        if previous is None:
            raise AppError(
                "analysis_not_found",
                "The previous analysis was not found. Start a new analysis.",
                404,
            )
        context.append(
            {
                "question": previous.question,
                "sql": previous.snapshot["result"]["sql"],
                "summary": previous.snapshot["summary"][:1800],
            }
        )
        parent_id = previous.parent_id
    context.reverse()
    with capture_cost() as calls:
        repair = None
        for attempt in range(2):
            plan = provider.plan(request.question, context, repair)
            if plan.status != "ready":
                raise AppError(
                    plan.status, plan.message or "Please ask a question about the airline dataset."
                )
            try:
                snapshot = create_snapshot(request.question, plan.sql, provider, plan.title)
                if plan.message:
                    snapshot.result.warnings.append(plan.message)
                break
            except AppError as exc:
                if attempt == 1 or exc.code not in ("unsafe_sql", "invalid_sql", "query_timeout"):
                    raise
                repair = f"Previous SQL: {plan.sql}\nValidation error: {exc.message}"
        snapshot.model_cost = total_cost(calls)
    analysis = Analysis(
        question=request.question,
        parent_id=request.parent_id,
        snapshot=snapshot.model_dump(mode="json"),
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis
