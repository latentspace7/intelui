import math
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.config import settings
from app.contracts import QueryResult
from app.db import analytics_engine
from app.errors import AppError
from app.sql_safety import validate_sql


def scalar_value(value):
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(value)[:2000]


def execute_query(sql: str) -> QueryResult:
    validated = validate_sql(sql)
    started = perf_counter()
    try:
        with analytics_engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL search_path TO crm, airline, pg_catalog"))
            connection.execute(
                text(f"SET LOCAL statement_timeout = '{settings.query_timeout_ms}ms'")
            )
            connection.execute(text("SET LOCAL lock_timeout = '1s'"))
            connection.execute(text("SET LOCAL work_mem = '4MB'"))
            role = connection.execute(
                text(
                    "SELECT rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user"
                )
            ).one()
            if any(role):
                raise AppError(
                    "unsafe_database_role",
                    "Configure a non-privileged analytics database role.",
                    503,
                )
            cursor = connection.execute(
                text(
                    f"SELECT * FROM ({validated}) AS bounded_result LIMIT {settings.max_result_rows + 1}"
                )
            )
            columns = list(cursor.keys())
            if len(columns) > 30 or len(set(columns)) != len(columns):
                raise AppError("invalid_sql", "Use at most 30 uniquely named result columns.")
            fetched = cursor.fetchall()
            truncated = len(fetched) > settings.max_result_rows
            rows = [
                {key: scalar_value(value) for key, value in zip(columns, row, strict=True)}
                for row in fetched[: settings.max_result_rows]
            ]
    except DBAPIError as exc:
        code = getattr(exc.orig, "sqlstate", None)
        if code in ("57014", "55P03"):
            raise AppError(
                "query_timeout",
                "The query took too long. Try a narrower time period or fewer joins.",
            ) from exc
        if code and code.startswith("42"):
            raise AppError(
                "invalid_sql",
                "PostgreSQL rejected the query. Check column names, types, and grouping.",
            ) from exc
        raise AppError(
            "database_unavailable",
            "The analytics database is unavailable. Check the database service.",
            503,
        ) from exc
    except SQLAlchemyError as exc:
        raise AppError(
            "database_unavailable", "The analytics database is unavailable.", 503
        ) from exc
    return QueryResult(
        sql=validated,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        duration_ms=round((perf_counter() - started) * 1000, 2),
        truncated=truncated,
        warnings=[
            f"Results limited to {settings.max_result_rows} rows; charts reflect only these rows."
        ]
        if truncated
        else [],
    )
